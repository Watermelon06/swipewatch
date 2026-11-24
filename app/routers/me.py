from typing import Literal

from fastapi import APIRouter, Query
from sqlalchemy import delete, select

from ..deps import CurrentUser, Db
from ..models import Movie, UserMovieState
from ..schemas import movie_out

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/history")
async def history(db: Db, user: CurrentUser, state: Literal["watched", "liked", "skipped"] = "watched",
                  limit: int = Query(50, ge=1, le=200)):
    rows = (await db.execute(
        select(UserMovieState, Movie).join(Movie, Movie.id == UserMovieState.movie_id)
        .where(UserMovieState.user_id == user.id, UserMovieState.state == state)
        .order_by(UserMovieState.updated_at.desc()).limit(limit)
    )).all()
    return [{"movie": movie_out(m), "rating": s.rating, "updated_at": s.updated_at} for s, m in rows]


@router.delete("/history")
async def reset_history(db: Db, user: CurrentUser):
    """Кнопка «сбросить историю»: фильмы снова могут выпадать."""
    res = await db.execute(delete(UserMovieState).where(UserMovieState.user_id == user.id))
    await db.commit()
    return {"deleted": res.rowcount}
