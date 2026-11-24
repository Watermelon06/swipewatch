import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import func, select

from ..config import get_settings
from ..db import SessionLocal
from ..deps import Db, require_admin
from ..models import Movie
from ..services.sync import SyncReport, run_sync

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])
_lock = asyncio.Lock()
_last: dict = {"running": False, "report": None}


async def _job(budget: int, itunes: bool):
    async with _lock:
        _last["running"] = True
        try:
            _last["report"] = await run_sync(SessionLocal, get_settings().kp_api_key, budget, itunes)
        finally:
            _last["running"] = False


@router.post("/sync")
async def sync(bg: BackgroundTasks, budget: int = Query(450, ge=10, le=2000), itunes: bool = True):
    if _lock.locked():
        raise HTTPException(409, "sync already running")
    bg.add_task(_job, budget, itunes)
    return {"started": True}


@router.get("/stats")
async def stats(db: Db):
    total = (await db.execute(select(func.count()).select_from(Movie))).scalar_one()
    ready = (await db.execute(select(func.count()).select_from(Movie).where(
        Movie.is_active.is_(True), Movie.synopsis.is_not(None), Movie.poster_url.is_not(None)))).scalar_one()
    by_source = dict((await db.execute(select(Movie.source, func.count()).group_by(Movie.source))).all())
    report = _last["report"]
    return {"total": total, "ready_for_deck": ready, "by_source": by_source, "sync_running": _last["running"],
            "last_sync": vars(report) if isinstance(report, SyncReport) else None}
