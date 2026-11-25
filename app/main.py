import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .db import engine, SessionLocal
from .models import Base
from .migrations import backfill_collection, run_migrations
from .routers import admin, auth, me, meta, sessions

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if get_settings().auto_create_tables:      # для MVP; потом заменить на Alembic
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        await backfill_collection(SessionLocal)
    await run_migrations(engine)
    yield
    await engine.dispose()


app = FastAPI(title="Swipe&Watch API", lifespan=lifespan)

api = APIRouter(prefix="/api")
for r in (auth.router, meta.router, sessions.router, me.router, admin.router):
    api.include_router(r)
app.include_router(api)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
