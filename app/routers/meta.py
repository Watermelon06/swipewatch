from fastapi import APIRouter

from ..deps import CurrentUser, Db
from ..services.genres import ALL_GENRES

router = APIRouter(tags=["meta"])


@router.get("/meta")
async def meta(db: Db, user: CurrentUser):
    return {"genres": ALL_GENRES}


@router.get("/health")
async def health():
    return {"ok": True}
