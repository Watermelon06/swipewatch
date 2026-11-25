import uuid
from datetime import datetime, timezone

from sqlalchemy import (JSON, Boolean, DateTime, Float, ForeignKey, Index, Integer,
                        String, Text, UniqueConstraint, Uuid, false)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Movie(Base):
    __tablename__ = "movies"
    __table_args__ = (UniqueConstraint("source", "source_id", name="uq_movie_source"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source: Mapped[str] = mapped_column(String(16))
    source_id: Mapped[str] = mapped_column(String(40))
    dedupe_key: Mapped[str] = mapped_column(String(300), unique=True)
    title: Mapped[str] = mapped_column(String(300))
    original_title: Mapped[str | None] = mapped_column(String(300))
    type: Mapped[str] = mapped_column(String(16), default="Фильм")
    year: Mapped[int | None] = mapped_column(Integer)
    duration_min: Mapped[int | None] = mapped_column(Integer)
    age: Mapped[str | None] = mapped_column(String(16))
    kp_rating: Mapped[float | None] = mapped_column(Float)
    imdb_rating: Mapped[float | None] = mapped_column(Float)
    votes: Mapped[int] = mapped_column(Integer, default=0)
    genres: Mapped[list] = mapped_column(JSON, default=list)
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
    status: Mapped[str] = mapped_column(String(16), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SessionCard(Base):
    __tablename__ = "session_cards"
    __table_args__ = (UniqueConstraint("session_id", "movie_id", name="uq_session_movie"),)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))


class Swipe(Base):
    __tablename__ = "swipes"
    __table_args__ = (Index("ix_swipes_session_movie", "session_id", "movie_id"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"))
    action: Mapped[str] = mapped_column(String(8))
    rating: Mapped[int | None] = mapped_column(Integer)
    dwell_ms: Mapped[int] = mapped_column(Integer, default=0)
    opened_details: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class UserMovieState(Base):
    """Обратная совместимость с существующим алгоритмом рекомендаций."""
    __tablename__ = "user_movie_state"
    __table_args__ = (Index("ix_ums_user", "user_id"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    state: Mapped[str] = mapped_column(String(8))
    rating: Mapped[int | None] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


# New v2 tables are additive: the existing MVP tables and their data remain intact.
class UserProfile(Base):
    __tablename__ = "user_profiles"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(80), default="Киноман")
    avatar_url: Mapped[str | None] = mapped_column(Text)
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserIdentity(Base):
    __tablename__ = "user_identities"
    __table_args__ = (UniqueConstraint("provider", "subject", name="uq_identity_provider_subject"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    provider: Mapped[str] = mapped_column(String(24))
    subject: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class UserMovieCollection(Base):
    __tablename__ = "user_movie_collection"
    __table_args__ = (Index("ix_collection_user_updated", "user_id", "updated_at"),)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    in_watchlist: Mapped[bool] = mapped_column(Boolean, default=False)
    watched: Mapped[bool] = mapped_column(Boolean, default=False)
    skipped: Mapped[bool] = mapped_column(Boolean, default=False)
    rating: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(Text)
    watched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SwipeStateSnapshot(Base):
    __tablename__ = "swipe_state_snapshots"
    swipe_id: Mapped[int] = mapped_column(ForeignKey("swipes.id", ondelete="CASCADE"), primary_key=True)
    previous_state: Mapped[str | None] = mapped_column(String(8))
    previous_rating: Mapped[int | None] = mapped_column(Integer)
    previous_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    previous_collection: Mapped[dict | None] = mapped_column(JSON)


class SessionOptions(Base):
    __tablename__ = "session_options"
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    filters: Mapped[dict] = mapped_column(JSON, default=dict)


class VkOAuthAttempt(Base):
    __tablename__ = "vk_oauth_attempts"
    state: Mapped[str] = mapped_column(String(128), primary_key=True)
    code_verifier: Mapped[str] = mapped_column(String(128))
    anon_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthExchangeCode(Base):
    __tablename__ = "auth_exchange_codes"
    code: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
