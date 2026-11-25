"""Small idempotent data migration for existing MVP databases."""
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from .models import UserMovieCollection, UserMovieState, utcnow


async def backfill_collection(session_factory: async_sessionmaker) -> int:
    """Copy legacy liked/watched/skipped rows into the richer v2 collection table.

    Existing rows are never deleted or rewritten. The operation is idempotent.
    """
    created = 0
    async with session_factory() as db:
        legacy = (await db.execute(select(UserMovieState))).scalars().all()
        for row in legacy:
            current = await db.get(UserMovieCollection, (row.user_id, row.movie_id))
            if current:
                continue
            current = UserMovieCollection(user_id=row.user_id, movie_id=row.movie_id,
                                          updated_at=row.updated_at or utcnow())
            if row.state == "liked":
                current.in_watchlist = True
            elif row.state == "watched":
                current.watched = True
                current.rating = row.rating * 2 if row.rating else None
                current.watched_at = row.updated_at
            elif row.state == "skipped":
                current.skipped = True
            db.add(current)
            created += 1
        await db.commit()
    return created


# Версионированные миграции схемы/данных. Новая миграция = новая запись в конец списка.
# Каждая применяется один раз (учёт в таблице schema_migrations), все запросы идемпотентны.
MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (1, "ix_swipes_session_movie",
     ["CREATE INDEX IF NOT EXISTS ix_swipes_session_movie ON swipes (session_id, movie_id)"]),
    (2, "fix_state_rating_scale",   # legacy-оценка 1-5; раньше сюда попадали значения 1-10
     ["UPDATE user_movie_state SET rating = (rating + 1) / 2 WHERE rating > 5"]),
    (3, "swipes_opened_details",    # сигнал «открыл Подробнее»
     ["ALTER TABLE swipes ADD COLUMN IF NOT EXISTS opened_details BOOLEAN NOT NULL DEFAULT FALSE"]),
]


async def run_migrations(engine: AsyncEngine) -> list[int]:
    applied_now: list[int] = []
    async with engine.begin() as conn:
        await conn.execute(text(
            "CREATE TABLE IF NOT EXISTS schema_migrations ("
            "version INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, "
            "applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)"))
        done = {row[0] for row in await conn.execute(text("SELECT version FROM schema_migrations"))}
        for version, name, statements in MIGRATIONS:
            if version in done:
                continue
            for statement in statements:
                if conn.dialect.name == "sqlite":      # SQLite не знает ADD COLUMN IF NOT EXISTS
                    statement = statement.replace("ADD COLUMN IF NOT EXISTS", "ADD COLUMN").replace(
                        "DEFAULT FALSE", "DEFAULT 0")
                    try:
                        async with conn.begin_nested():
                            await conn.execute(text(statement))
                    except Exception as exc:           # колонка уже есть (create_all) — это нормально
                        if "duplicate column" not in str(exc).lower():
                            raise
                else:
                    await conn.execute(text(statement))
            await conn.execute(text(
                "INSERT INTO schema_migrations (version, name) VALUES (:v, :n) ON CONFLICT DO NOTHING"),
                {"v": version, "n": name})
            applied_now.append(version)
    return applied_now
