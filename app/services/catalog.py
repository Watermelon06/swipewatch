"""Лёгкий in-memory индекс каталога (id, жанры, рейтинг). Полные карточки грузим из БД только для выбранных id."""
import time
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Movie


@dataclass(frozen=True, slots=True)
class CatalogItem:
    id: int
    genres: tuple[str, ...]
    rating: float | None
    source: str


_cache: dict = {"items": [], "ts": 0.0}
TTL = 300.0


def invalidate_catalog() -> None:
    _cache["ts"] = 0.0
    _cache["items"] = []


async def get_catalog(db: AsyncSession) -> list[CatalogItem]:
    if _cache["items"] and time.monotonic() - _cache["ts"] < TTL:
        return _cache["items"]
    rows = await db.execute(
        select(Movie.id, Movie.genres, Movie.kp_rating, Movie.imdb_rating, Movie.source).where(
            Movie.is_active.is_(True),
            Movie.synopsis.is_not(None),
            Movie.poster_url.is_not(None),
        )
    )
    items = [
        CatalogItem(r.id, tuple(r.genres or ()), r.kp_rating or r.imdb_rating, r.source)
        for r in rows
        if r.genres
    ]
    _cache["items"], _cache["ts"] = items, time.monotonic()
    return items
