from typing import Literal
import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, select

from ..deps import CurrentUser, Db
from ..models import (GameSession, Movie, SessionCard, SessionOptions, Swipe,
                      UserIdentity, UserMovieCollection, UserMovieState, UserProfile, utcnow)
from ..schemas import CollectionUpdate, ProfileUpdate, collection_flags, movie_out

router = APIRouter(prefix="/me", tags=["me"])


def _state_rating(collection_rating: int | None) -> int | None:
    """Коллекция хранит оценку 1-10, а legacy user_movie_state — 1-5."""
    if collection_rating is None:
        return None
    return max(1, min(5, (collection_rating + 1) // 2))


def _iso(value):
    return value.isoformat() if value else None


@router.get("/history")
async def history(db: Db, user: CurrentUser,
                  state: Literal["watched", "liked", "skipped"] = "watched",
                  limit: int = Query(50, ge=1, le=200)):
    rows = (await db.execute(
        select(UserMovieState, Movie).join(Movie, Movie.id == UserMovieState.movie_id)
        .where(UserMovieState.user_id == user.id, UserMovieState.state == state)
        .order_by(UserMovieState.updated_at.desc()).limit(limit)
    )).all()
    return [{"movie": movie_out(movie).model_dump(), "rating": row.rating,
             "updated_at": _iso(row.updated_at)} for row, movie in rows]


@router.delete("/history")
async def reset_history(db: Db, user: CurrentUser):
    state_result = await db.execute(delete(UserMovieState).where(UserMovieState.user_id == user.id))
    collection_result = await db.execute(delete(UserMovieCollection).where(
        UserMovieCollection.user_id == user.id))
    await db.commit()
    return {"deleted": state_result.rowcount, "collection_deleted": collection_result.rowcount}


@router.get("/collection")
async def collection(
    db: Db, user: CurrentUser,
    view: Literal["all", "favorites", "watchlist", "watched", "skipped"] = "all",
    q: str | None = Query(default=None, max_length=120),
    genre: str | None = Query(default=None, max_length=50),
    limit: int = Query(60, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    conds = [UserMovieCollection.user_id == user.id]
    if view == "favorites":
        conds.append(UserMovieCollection.is_favorite.is_(True))
    elif view == "watchlist":
        conds.append(UserMovieCollection.in_watchlist.is_(True))
    elif view == "watched":
        conds.append(UserMovieCollection.watched.is_(True))
    elif view == "skipped":
        conds.append(UserMovieCollection.skipped.is_(True))
    if q:
        conds.append(func.lower(Movie.title).contains(q.lower(), autoescape=True))
    query = (select(UserMovieCollection, Movie)
             .join(Movie, Movie.id == UserMovieCollection.movie_id).where(*conds)
             .order_by(UserMovieCollection.updated_at.desc(), Movie.id))
    if genre:
        # genres — JSON-список, переносимого SQL-фильтра нет: фильтруем до пагинации в Python
        # (коллекция одного пользователя небольшая), чтобы offset/limit/total были честными.
        all_rows = [r for r in (await db.execute(query)).all() if genre in (r[1].genres or [])]
        total = len(all_rows)
        rows = all_rows[offset:offset + limit]
    else:
        rows = (await db.execute(query.limit(limit).offset(offset))).all()
        total = (await db.execute(
            select(func.count()).select_from(UserMovieCollection)
            .join(Movie, Movie.id == UserMovieCollection.movie_id).where(*conds)
        )).scalar_one()
    data = []
    for state, movie in rows:
        data.append({
            "movie": movie_out(movie).model_dump(),
            "is_favorite": state.is_favorite, "in_watchlist": state.in_watchlist,
            "watched": state.watched, "skipped": state.skipped,
            "rating": state.rating, "note": state.note,
            "watched_at": _iso(state.watched_at), "updated_at": _iso(state.updated_at),
        })
    return {"items": data, "total": total, "limit": limit, "offset": offset}


@router.put("/collection/{movie_id}")
async def update_collection(movie_id: int, body: CollectionUpdate, db: Db, user: CurrentUser):
    movie = await db.get(Movie, movie_id)
    if not movie:
        raise HTTPException(404, "movie not found")
    item = await db.get(UserMovieCollection, (user.id, movie_id))
    if not item:
        item = UserMovieCollection(user_id=user.id, movie_id=movie_id)
        db.add(item)
    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(item, key, value)
    if item.watched and not item.watched_at:
        item.watched_at = utcnow()
    if not item.watched:
        item.watched_at = None
    item.updated_at = utcnow()

    # Keep the recommendation engine's original state table in sync.
    state = await db.get(UserMovieState, (user.id, movie_id))
    state_name = "watched" if item.watched else "liked" if item.in_watchlist or item.is_favorite else "skipped" if item.skipped else None
    if state_name:
        if state:
            state.state = state_name
            state.rating = _state_rating(item.rating)
            state.updated_at = utcnow()
        else:
            db.add(UserMovieState(user_id=user.id, movie_id=movie_id, state=state_name,
                                  rating=_state_rating(item.rating)))
    elif state:
        await db.delete(state)
    await db.commit()
    return {"ok": True, "item": {
        "is_favorite": item.is_favorite, "in_watchlist": item.in_watchlist,
        "watched": item.watched, "skipped": item.skipped, "rating": item.rating,
        "note": item.note,
    }}


@router.delete("/collection/{movie_id}")
async def delete_collection_item(movie_id: int, db: Db, user: CurrentUser):
    item = await db.get(UserMovieCollection, (user.id, movie_id))
    if not item:
        return {"deleted": False}
    await db.delete(item)
    state = await db.get(UserMovieState, (user.id, movie_id))
    if state:
        await db.delete(state)
    await db.commit()
    return {"deleted": True}


@router.get("/dashboard")
async def dashboard(db: Db, user: CurrentUser):
    profile = await db.get(UserProfile, user.id)
    if not profile:
        profile = UserProfile(user_id=user.id, display_name="Киноман", preferences={})
        db.add(profile)
        await db.commit()
    counts = {}
    for key, column in (("favorites", UserMovieCollection.is_favorite),
                        ("watchlist", UserMovieCollection.in_watchlist),
                        ("watched", UserMovieCollection.watched),
                        ("skipped", UserMovieCollection.skipped)):
        counts[key] = (await db.execute(select(func.count()).select_from(UserMovieCollection).where(
            UserMovieCollection.user_id == user.id, column.is_(True)
        ))).scalar_one()
    recent_rows = (await db.execute(
        select(UserMovieCollection, Movie).join(Movie, Movie.id == UserMovieCollection.movie_id)
        .where(UserMovieCollection.user_id == user.id)
        .order_by(UserMovieCollection.updated_at.desc()).limit(8)
    )).all()
    recent = [{"movie": movie_out(movie).model_dump(), "is_favorite": state.is_favorite,
               "in_watchlist": state.in_watchlist, "watched": state.watched,
               "rating": state.rating, "note": state.note} for state, movie in recent_rows]
    active = (await db.execute(select(GameSession).where(
        GameSession.user_id == user.id, GameSession.status == "active"
    ).order_by(GameSession.started_at.desc()).limit(1))).scalar_one_or_none()
    sessions_count = (await db.execute(select(func.count()).select_from(GameSession).where(
        GameSession.user_id == user.id
    ))).scalar_one()
    identities_count = (await db.execute(select(func.count()).select_from(UserIdentity).where(
        UserIdentity.user_id == user.id
    ))).scalar_one()
    return {
        "profile": {"display_name": profile.display_name, "avatar_url": profile.avatar_url,
                    "preferences": profile.preferences or {}},
        "counts": counts, "recent": recent,
        "active_session": ({"session_id": str(active.id), "started_at": _iso(active.started_at),
                            "limit": active.limit} if active else None),
        "sessions_count": sessions_count, "has_vk": identities_count > 0,
    }


@router.get("/profile")
async def get_profile(db: Db, user: CurrentUser):
    profile = await db.get(UserProfile, user.id)
    if not profile:
        profile = UserProfile(user_id=user.id, display_name="Киноман", preferences={})
        db.add(profile)
        await db.commit()
    return {"display_name": profile.display_name, "avatar_url": profile.avatar_url,
            "preferences": profile.preferences or {}, "created_at": _iso(profile.created_at)}


@router.patch("/profile")
async def update_profile(body: ProfileUpdate, db: Db, user: CurrentUser):
    profile = await db.get(UserProfile, user.id)
    if not profile:
        profile = UserProfile(user_id=user.id, display_name="Киноман", preferences={})
        db.add(profile)
    changes = body.model_dump(exclude_unset=True)
    for key, value in changes.items():
        if value is not None:
            setattr(profile, key, value)
    profile.updated_at = utcnow()
    await db.commit()
    return {"display_name": profile.display_name, "avatar_url": profile.avatar_url,
            "preferences": profile.preferences or {}}


@router.get("/sessions")
async def session_history(db: Db, user: CurrentUser, limit: int = Query(30, ge=1, le=100),
                          offset: int = Query(0, ge=0)):
    sessions = (await db.execute(select(GameSession).where(
        GameSession.user_id == user.id
    ).order_by(GameSession.started_at.desc(), GameSession.id).limit(limit).offset(offset))).scalars().all()
    result = []
    for session in sessions:
        served = (await db.execute(select(func.count()).select_from(SessionCard).where(
            SessionCard.session_id == session.id
        ))).scalar_one()
        swiped = (await db.execute(select(func.count()).select_from(Swipe).where(
            Swipe.session_id == session.id, Swipe.undone_at.is_(None)
        ))).scalar_one()
        liked = (await db.execute(select(func.count()).select_from(Swipe).where(
            Swipe.session_id == session.id, Swipe.action == "right", Swipe.undone_at.is_(None)
        ))).scalar_one()
        options = await db.get(SessionOptions, session.id)
        result.append({
            "id": str(session.id), "status": session.status, "started_at": _iso(session.started_at),
            "finished_at": _iso(session.finished_at), "limit": session.limit,
            "served": served, "swiped": swiped, "liked": liked,
            "initial_genres": session.initial_genres or [], "surprise": session.surprise,
            "filters": options.filters if options else {},
        })
    return result


@router.get("/sessions/{session_id}")
async def session_detail(session_id: uuid.UUID, db: Db, user: CurrentUser):
    session = await db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "session not found")
    rows = (await db.execute(
        select(SessionCard, Movie).join(Movie, Movie.id == SessionCard.movie_id)
        .where(SessionCard.session_id == session.id).order_by(SessionCard.position)
    )).all()
    events = (await db.execute(select(Swipe).where(
        Swipe.session_id == session.id, Swipe.undone_at.is_(None)
    ).order_by(Swipe.id))).scalars().all()
    event_by_movie = {event.movie_id: event for event in events}
    ids = [movie.id for _, movie in rows]
    flags = {r.movie_id: collection_flags(r) for r in (await db.execute(
        select(UserMovieCollection).where(UserMovieCollection.user_id == user.id,
                                          UserMovieCollection.movie_id.in_(ids)))).scalars()} if ids else {}
    cards = []
    for _, movie in rows:
        event = event_by_movie.get(movie.id)
        cards.append({"movie": movie_out(movie).model_dump(), "action": event.action if event else None,
                      "rating": event.rating if event else None, "collection": flags.get(movie.id)})
    options = await db.get(SessionOptions, session.id)
    return {"id": str(session.id), "status": session.status, "started_at": _iso(session.started_at),
            "finished_at": _iso(session.finished_at), "limit": session.limit,
            "initial_genres": session.initial_genres or [], "surprise": session.surprise,
            "filters": options.filters if options else {}, "cards": cards}
