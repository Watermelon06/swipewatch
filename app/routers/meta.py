from fastapi import APIRouter

from ..deps import CurrentUser, Db
from ..services.catalog import get_catalog
from ..services.genres import ALL_GENRES

router = APIRouter(tags=["meta"])


@router.get("/meta")
async def meta(db: Db, user: CurrentUser):
    catalog = await get_catalog(db)
    return {"genres": ALL_GENRES, "catalog_size": len(catalog)}


@router.get("/health")
async def health():
    return {"ok": True}
