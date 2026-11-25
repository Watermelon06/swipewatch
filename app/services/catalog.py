"""Лёгкий in-memory индекс каталога. Полные карточки загружаются только для выбранных id."""
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
    year: int | None = None
    type: str = "Фильм"
    duration_min: int | None = None
    age: str | None = None


_cache: dict = {"items": [], "ts": 0.0}
TTL = 300.0


def invalidate_catalog() -> None:
    _cache["ts"] = 0.0
    _cache["items"] = []


async def get_catalog(db: AsyncSession) -> list[CatalogItem]:
    if _cache["items"] and time.monotonic() - _cache["ts"] < TTL:
        return _cache["items"]
    rows = await db.execute(
        select(Movie.id, Movie.genres, Movie.kp_rating, Movie.imdb_rating, Movie.source,
               Movie.year, Movie.type, Movie.duration_min, Movie.age).where(
            Movie.is_active.is_(True), Movie.synopsis.is_not(None), Movie.poster_url.is_not(None)
        )
    )
    items = [
        CatalogItem(r.id, tuple(r.genres or ()), r.kp_rating or r.imdb_rating, r.source,
                    r.year, r.type or "Фильм", r.duration_min, r.age)
        for r in rows if r.genres
    ]
    _cache["items"], _cache["ts"] = items, time.monotonic()
    return items
