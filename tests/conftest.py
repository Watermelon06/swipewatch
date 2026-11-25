import os
import tempfile

_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_db}"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["ADMIN_TOKEN"] = "admin"
os.environ["ANON_RATE_LIMIT_PER_HOUR"] = "0"

import random  # noqa: E402

import httpx  # noqa: E402
import pytest_asyncio  # noqa: E402

from app.db import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base, Movie  # noqa: E402
from app.services.catalog import invalidate_catalog  # noqa: E402
from app.services.genres import ALL_GENRES, dedupe_key  # noqa: E402


@pytest_asyncio.fixture
async def seeded():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    rnd = random.Random(1)
    async with SessionLocal() as db:
        for i in range(80):
            genres = rnd.sample(ALL_GENRES, rnd.randint(1, 3))
            db.add(Movie(source="kp", source_id=str(i), dedupe_key=dedupe_key(f"Фильм {i}", 2000 + i % 20),
                         title=f"Фильм {i}", year=2000 + i % 20, kp_rating=round(rnd.uniform(6, 9), 1),
                         genres=genres, synopsis="Описание " * 10, poster_url=f"http://x/{i}.jpg"))
        await db.commit()
    invalidate_catalog()


@pytest_asyncio.fixture
async def client(seeded):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        r = await c.post("/api/auth/anon")
        c.headers["Authorization"] = f"Bearer {r.json()['token']}"
        yield c
