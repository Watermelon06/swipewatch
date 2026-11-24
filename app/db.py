from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import get_settings, normalize_db_url

_settings = get_settings()
_url, _connect_args = normalize_db_url(_settings.database_url)

_kwargs: dict = {"pool_pre_ping": True, "connect_args": _connect_args}
if _url.startswith("postgresql"):
    # Neon усыпляет соединения -> pre_ping + короткий recycle
    _kwargs.update(pool_recycle=240, pool_size=5, max_overflow=5)

engine = create_async_engine(_url, **_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
