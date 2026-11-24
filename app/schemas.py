import uuid
from typing import Literal

from pydantic import BaseModel, Field

from .models import Movie


class MovieOut(BaseModel):
    """Формат под клиент (camelCase, id строкой)."""
    id: str
    title: str
    originalTitle: str
    type: str
    year: int | None
    duration: str | None
    age: str | None
    kp: float | None
    imdb: float | None
    genres: list[str]
    shortHook: str | None
    synopsis: str | None
    posterUrl: str | None
    kinopoiskUrl: str | None
    source: str


def _fmt_duration(minutes: int | None) -> str | None:
    if not minutes:
        return None
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h} ч {m} мин"
    return f"{h} ч" if h else f"{m} мин"


def movie_out(m: Movie) -> MovieOut:
    return MovieOut(
        id=str(m.id), title=m.title, originalTitle=m.original_title or m.title, type=m.type,
        year=m.year, duration=_fmt_duration(m.duration_min), age=m.age,
        kp=m.kp_rating, imdb=m.imdb_rating, genres=list(m.genres or []),
        shortHook=m.short_hook, synopsis=m.synopsis, posterUrl=m.poster_url,
        kinopoiskUrl=m.external_url, source=m.source,
    )


class SessionCreate(BaseModel):
    limit: Literal[10, 15, 20] = 15
    initial_genres: list[str] = Field(default_factory=list, max_length=30)
    surprise: bool = False


class DeckOut(BaseModel):
    session_id: uuid.UUID | None = None
    cards: list[MovieOut]
    served_total: int
    planned_total: int      # сколько карточек реально будет в сессии (меньше limit, если каталог кончился)
    exhausted: bool


class EventIn(BaseModel):
    event_id: str = Field(min_length=8, max_length=64)
    type: Literal["right", "left", "up"]
    movie_id: int
    rating: int | None = Field(default=None, ge=1, le=5)
    dwell_ms: int = Field(default=0, ge=0, le=3_600_000)


class EventsIn(BaseModel):
    events: list[EventIn] = Field(min_length=1, max_length=50)
