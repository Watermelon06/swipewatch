import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint, Uuid)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_movie_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16))              # 'kp' | 'itunes'
    source_id: Mapped[str] = mapped_column(String(40))
    dedupe_key: Mapped[str] = mapped_column(String(300), unique=True)  # норм.название|год

    title: Mapped[str] = mapped_column(String(300))
    original_title: Mapped[str | None] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(16), default="Фильм")  # Фильм | Сериал
    year: Mapped[int | None] = mapped_column(Integer)
    duration_min: Mapped[int | None] = mapped_column(Integer)
    age: Mapped[str | None] = mapped_column(String(16))
    kp_rating: Mapped[float | None] = mapped_column(Float)
    imdb_rating: Mapped[float | None] = mapped_column(Float)
    votes: Mapped[int] = mapped_column(Integer, default=0)
    genres: Mapped[list] = mapped_column(JSON, default=list)      # только из ALL_GENRES
    synopsis: Mapped[str | None] = mapped_column(Text)
    short_hook: Mapped[str | None] = mapped_column(Text)
    poster_url: Mapped[str | None] = mapped_column(Text)
    external_url: Mapped[str | None] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class GameSession(Base):
    __tablename__ = "sessions"
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    limit: Mapped[int] = mapped_column(Integer)
    seed: Mapped[int] = mapped_column(Integer)
    surprise: Mapped[bool] = mapped_column(Boolean, default=False)
    initial_genres: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|finished|abandoned
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionCard(Base):
    """Какие карточки сервер уже выдал в сессии (и в каком порядке)."""
    __tablename__ = "session_cards"
    __table_args__ = (UniqueConstraint("session_id", "movie_id", name="uq_session_movie"),)

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))


class Swipe(Base):
    __tablename__ = "swipes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True)  # идемпотентность
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(8))                  # right | left | up
    rating: Mapped[int | None] = mapped_column(Integer)
    dwell_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserMovieState(Base):
    """Долгая память: что пользователь уже просмотрел / лайкнул / скипнул."""
    __tablename__ = "user_movie_state"
    __table_args__ = (Index("ix_ums_user", "user_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[str] = mapped_column(String(8))                   # watched | liked | skipped
    rating: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
