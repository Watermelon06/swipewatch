from sqlalchemy import func, select

from app.config import normalize_db_url
from app.db import SessionLocal
from app.models import Movie
from app.services.sources import Draft
from app.services.sync import SyncReport, upsert_drafts


def test_neon_url_is_normalized_for_asyncpg():
    url, args = normalize_db_url("postgresql://u:p@ep-x-pooler.eu.aws.neon.tech/neondb?sslmode=require&channel_binding=require")
    assert url == "postgresql+asyncpg://u:p@ep-x-pooler.eu.aws.neon.tech/neondb"
    assert args["ssl"] == "require" and args["statement_cache_size"] == 0
    assert normalize_db_url("sqlite+aiosqlite:///x.db") == ("sqlite+aiosqlite:///x.db", {})


async def test_upsert_dedupes_across_sources(seeded):
    kp = Draft(source="kp", source_id="900", title="Остров проклятых", year=2010, genres=["Триллер"], poster_url="u")
    apple = Draft(source="itunes", source_id="55", title="Остров проклятых!", year=2010, genres=["Триллер"],
                  synopsis="x" * 80, poster_url="u")
    other = Draft(source="itunes", source_id="56", title="Совсем другое", year=2011, genres=["Драма"],
                  synopsis="x" * 80, poster_url="u")
    rep = SyncReport()
    async with SessionLocal() as db:
        before = (await db.execute(select(func.count()).select_from(Movie))).scalar_one()
        assert await upsert_drafts(db, [kp], rep) == 1
        assert await upsert_drafts(db, [apple, other], rep) == 1     # дубль из iTunes отброшен
        assert await upsert_drafts(db, [kp], rep) == 0               # повторный запуск = update, не insert
        after = (await db.execute(select(func.count()).select_from(Movie))).scalar_one()
    assert after - before == 2 and rep.updated == 1
