"""Синхронизация каталога. Два шага:
1) discovery: списки (топы + выборки по жанрам) -> upsert «черновиков» (быстро, 20 фильмов на запрос)
2) enrich: детальный запрос по фильму (описание, длительность, возраст) в рамках дневного лимита.
В колоду попадают только фильмы с описанием и постером."""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..models import Movie, utcnow
from .catalog import invalidate_catalog
from .genres import dedupe_key
from .sources import (ITUNES_TERMS, Draft, KinopoiskClient, KinopoiskError, QuotaExceeded,
                      fetch_itunes, parse_kp_detail, parse_kp_list_item)

log = logging.getLogger("sync")

TARGET_GENRES = ["триллер", "детектив", "драма", "фантастика", "приключения",
                 "криминал", "боевик", "комедия", "ужасы", "фэнтези"]


@dataclass
class SyncReport:
    started: datetime = field(default_factory=utcnow)
    kp_requests: int = 0
    added: int = 0
    updated: int = 0
    enriched: int = 0
    itunes_added: int = 0
    errors: list[str] = field(default_factory=list)


async def upsert_drafts(db: AsyncSession, drafts: list[Draft], report: SyncReport) -> int:
    rows = (await db.execute(select(Movie.id, Movie.source, Movie.source_id, Movie.dedupe_key))).all()
    by_src = {(r.source, r.source_id): r.id for r in rows}
    keys = {r.dedupe_key for r in rows}
    added = 0
    for d in drafts:
        existing_id = by_src.get((d.source, d.source_id))
        if existing_id:
            m = await db.get(Movie, existing_id)
            m.kp_rating, m.imdb_rating = d.kp_rating or m.kp_rating, d.imdb_rating or m.imdb_rating
            m.poster_url = d.poster_url or m.poster_url
            m.genres = d.genres or m.genres
            report.updated += 1
            continue
        keys_to_check = {d.key}
        if d.original_title:
            keys_to_check.add(dedupe_key(d.original_title, d.year))
        if keys_to_check & keys:
            continue                      # такой фильм уже есть из другого источника
        db.add(Movie(
            source=d.source, source_id=d.source_id, dedupe_key=d.key, title=d.title,
            original_title=d.original_title, type=d.type, year=d.year, duration_min=d.duration_min,
            age=d.age, kp_rating=d.kp_rating, imdb_rating=d.imdb_rating, votes=d.votes, genres=d.genres,
            synopsis=d.synopsis, short_hook=d.short_hook, poster_url=d.poster_url, external_url=d.external_url,
            enriched_at=utcnow() if d.source == "itunes" else None,
        ))
        keys.add(d.key)
        added += 1
    await db.commit()
    return added


async def discover_kp(kp: KinopoiskClient, max_requests: int) -> list[Draft]:
    found: dict[str, Draft] = {}

    def add(items: list[dict]):
        for it in items:
            d = parse_kp_list_item(it)
            if d:
                found.setdefault(d.source_id, d)

    start = kp.requests
    spent = lambda: kp.requests - start  # noqa: E731

    # 1) топы: самые надёжные по качеству
    for kind in ("TOP_250_MOVIES", "TOP_250_TV_SHOWS"):
        for page in range(1, 14):
            if spent() >= max_requests * 0.5:
                break
            data = await kp.collection(kind, page)
            add(data.get("items") or data.get("films") or [])
            if page >= (data.get("totalPages") or 1):
                break

    # 2) выборки по жанрам, отсортированные по числу голосов
    ids = await kp.genre_ids()
    for page in (1, 2, 3):
        for genre in TARGET_GENRES:
            gid = ids.get(genre)
            if not gid:
                continue
            for kind in ("FILM", "TV_SERIES"):
                if spent() >= max_requests:
                    return list(found.values())
                data = await kp.search(order="NUM_VOTE", type=kind, ratingFrom=6.5, ratingTo=10,
                                       yearFrom=1980, yearTo=3000, genres=gid, page=page)
                add(data.get("items") or [])
    return list(found.values())


async def enrich_kp(sf: async_sessionmaker, kp: KinopoiskClient, max_requests: int, report: SyncReport) -> None:
    async with sf() as db:
        todo = (await db.execute(
            select(Movie.id, Movie.source_id).where(
                Movie.source == "kp", Movie.enriched_at.is_(None), Movie.is_active.is_(True))
            .order_by(Movie.kp_rating.desc().nullslast()).limit(max_requests)
        )).all()
    for movie_id, kp_id in todo:
        try:
            detail = await kp.film(kp_id)
        except QuotaExceeded:
            report.errors.append("kp quota exceeded during enrich")
            return
        except Exception as e:  # noqa: BLE001
            report.errors.append(f"film {kp_id}: {e}")
            continue
        async with sf() as db:
            m = await db.get(Movie, movie_id)
            if detail:
                for k, v in parse_kp_detail(detail).items():
                    if v:
                        setattr(m, k, v)
            m.enriched_at = utcnow()          # даже если описания нет — повторно не запрашиваем
            await db.commit()
        report.enriched += 1


async def run_sync(sf: async_sessionmaker, kp_api_key: str, budget: int = 450, use_itunes: bool = True) -> SyncReport:
    report = SyncReport()
    if kp_api_key:
        kp = KinopoiskClient(kp_api_key)
        try:
            drafts = await discover_kp(kp, max_requests=int(budget * 0.35))
            async with sf() as db:
                report.added += await upsert_drafts(db, drafts, report)
            await enrich_kp(sf, kp, max_requests=max(0, budget - kp.requests), report=report)
        except QuotaExceeded as e:
            report.errors.append(str(e))
        except KinopoiskError as e:
            report.errors.append(str(e))
        finally:
            report.kp_requests = kp.requests
            await kp.close()
    else:
        report.errors.append("KP_API_KEY не задан — пропускаю Кинопоиск")

    if use_itunes:
        async with httpx.AsyncClient(timeout=20) as http:
            for term in ITUNES_TERMS:
                try:
                    drafts = await fetch_itunes(http, term)
                except Exception as e:  # noqa: BLE001
                    report.errors.append(f"itunes '{term}': {e}")
                    continue
                async with sf() as db:
                    report.itunes_added += await upsert_drafts(db, drafts, report)
                await asyncio.sleep(0.4)      # Apple лимитирует ~20 запросов/мин

    invalidate_catalog()
    log.info("sync done: %s", report)
    return report
