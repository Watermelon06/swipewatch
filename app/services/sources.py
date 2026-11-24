"""Источники каталога: Кинопоиск (kinopoiskapiunofficial.tech) и Apple iTunes Search API.
Парсеры вынесены в чистые функции — они покрыты тестами на фикстурах."""
import asyncio
import re
from dataclasses import dataclass, field

import httpx

from .genres import dedupe_key, normalize_genres


@dataclass
class Draft:
    source: str
    source_id: str
    title: str
    original_title: str | None = None
    type: str = "Фильм"
    year: int | None = None
    duration_min: int | None = None
    age: str | None = None
    kp_rating: float | None = None
    imdb_rating: float | None = None
    votes: int = 0
    genres: list[str] = field(default_factory=list)
    synopsis: str | None = None
    short_hook: str | None = None
    poster_url: str | None = None
    external_url: str | None = None

    @property
    def key(self) -> str:
        return dedupe_key(self.title, self.year)


def make_hook(text: str | None, limit: int = 170) -> str | None:
    if not text:
        return None
    text = re.sub(r"\s+", " ", text).strip()
    m = re.match(r"(.+?[.!?])(\s|$)", text)
    sentence = m.group(1) if m else text
    if len(sentence) > limit:
        sentence = sentence[:limit].rsplit(" ", 1)[0].rstrip(",;:—- ") + "…"
    return sentence or None


# ---------------------------------------------------------------- Кинопоиск

KP_TYPES = {"FILM": "Фильм", "TV_SERIES": "Сериал", "MINI_SERIES": "Сериал", "TV_SHOW": "Сериал"}


class KinopoiskError(Exception):
    pass


class QuotaExceeded(KinopoiskError):
    pass


def parse_kp_list_item(it: dict) -> Draft | None:
    kp_id = it.get("kinopoiskId") or it.get("filmId")
    title = it.get("nameRu") or it.get("nameEn") or it.get("nameOriginal")
    kind = KP_TYPES.get(it.get("type") or "FILM")
    genres = normalize_genres([g.get("genre", "") for g in it.get("genres") or []])
    poster = it.get("posterUrl") or it.get("posterUrlPreview")
    if not (kp_id and title and kind and genres and poster):
        return None
    orig = it.get("nameOriginal") or it.get("nameEn")
    year = it.get("year")
    return Draft(
        source="kp", source_id=str(kp_id), title=title,
        original_title=orig if orig and orig != title else None,
        type=kind, year=int(year) if str(year or "").isdigit() else None,
        kp_rating=it.get("ratingKinopoisk") or None, imdb_rating=it.get("ratingImdb") or None,
        genres=genres, poster_url=poster, external_url=f"https://www.kinopoisk.ru/film/{kp_id}/",
    )


def parse_kp_detail(d: dict) -> dict:
    """Поля, которые добавляет детальный запрос /films/{id}."""
    age = None
    limits = d.get("ratingAgeLimits")            # 'age16'
    if limits and re.search(r"\d+", limits):
        age = re.search(r"\d+", limits).group(0) + "+"
    desc = (d.get("description") or "").strip() or None
    return {
        "synopsis": desc,
        "short_hook": make_hook(d.get("shortDescription") or d.get("slogan") or desc),
        "duration_min": d.get("filmLength") or None,
        "age": age,
        "votes": d.get("ratingKinopoiskVoteCount") or 0,
        "kp_rating": d.get("ratingKinopoisk") or None,
        "imdb_rating": d.get("ratingImdb") or None,
        "external_url": d.get("webUrl") or None,
    }


class KinopoiskClient:
    BASE = "https://kinopoiskapiunofficial.tech/api"

    def __init__(self, api_key: str, pause: float = 0.12):
        self.http = httpx.AsyncClient(
            base_url=self.BASE, timeout=25,
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        )
        self.requests = 0
        self.pause = pause

    async def close(self):
        await self.http.aclose()

    async def get(self, path: str, params: dict | None = None) -> dict:
        for attempt in range(3):
            self.requests += 1
            resp = await self.http.get(path, params=params)
            if resp.status_code == 429:               # лимит запросов в секунду
                await asyncio.sleep(1.5 * (attempt + 1))
                continue
            if resp.status_code == 402:
                raise QuotaExceeded("Дневной лимит Кинопоиск API исчерпан")
            if resp.status_code == 401:
                raise KinopoiskError("Неверный KP_API_KEY")
            if resp.status_code == 404:
                return {}
            resp.raise_for_status()
            await asyncio.sleep(self.pause)
            return resp.json()
        raise KinopoiskError(f"429 Too Many Requests: {path}")

    async def collection(self, kind: str, page: int) -> dict:
        return await self.get("/v2.2/films/collections", {"type": kind, "page": page})

    async def search(self, **params) -> dict:
        return await self.get("/v2.2/films", params)

    async def film(self, kp_id: str) -> dict:
        return await self.get(f"/v2.2/films/{kp_id}")

    async def genre_ids(self) -> dict[str, int]:
        data = await self.get("/v2.2/films/filters")
        return {g["genre"].lower(): g["id"] for g in data.get("genres", []) if g.get("genre")}


# ---------------------------------------------------------------- iTunes / Apple TV

ITUNES_TERMS = [
    "триллер", "детектив", "драма", "фантастика", "приключения", "криминал", "боевик",
    "комедия", "мистика", "ужасы", "оскар", "культовое кино", "лучшие фильмы",
    "thriller", "sci-fi", "crime", "mystery", "horror",
]


def parse_itunes_item(it: dict) -> Draft | None:
    if it.get("kind") != "feature-movie":
        return None
    title = it.get("trackName")
    desc = (it.get("longDescription") or it.get("shortDescription") or "").strip()
    art = it.get("artworkUrl100")
    release = (it.get("releaseDate") or "")[:4]
    genres = normalize_genres([it.get("primaryGenreName", "")])
    if not (title and art and genres and len(desc) >= 60):
        return None
    millis = it.get("trackTimeMillis")
    return Draft(
        source="itunes", source_id=str(it["trackId"]), title=title, type="Фильм",
        year=int(release) if release.isdigit() else None,
        duration_min=round(millis / 60000) if millis else None,
        age=it.get("contentAdvisoryRating"), genres=genres, synopsis=desc,
        short_hook=make_hook(it.get("shortDescription") or desc),
        poster_url=re.sub(r"\d+x\d+bb", "600x900bb", art),
        external_url=it.get("trackViewUrl"),
    )


async def fetch_itunes(http: httpx.AsyncClient, term: str, limit: int = 50) -> list[Draft]:
    resp = await http.get("https://itunes.apple.com/search", params={
        "term": term, "media": "movie", "entity": "movie", "country": "RU", "lang": "ru_ru", "limit": limit})
    resp.raise_for_status()
    # Apple отдаёт text/javascript -> парсим вручную
    import json
    results = json.loads(resp.text).get("results", [])
    return [d for d in (parse_itunes_item(r) for r in results) if d]
