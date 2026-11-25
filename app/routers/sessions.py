import random
import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from ..config import get_settings
from ..deps import CurrentUser, Db
from ..models import (GameSession, Movie, SessionCard, SessionOptions, Swipe,
                      SwipeStateSnapshot, UserMovieCollection, UserMovieState, utcnow)
from ..schemas import DeckOut, EventsIn, SessionCreate, collection_flags, movie_out
from ..services import deck
from ..services.catalog import get_catalog
from ..services.genres import canonical_genres

router = APIRouter(prefix="/sessions", tags=["sessions"])
FIRST_BATCH = 8
MAX_BATCH = 10


async def _owned(db: Db, user, session_id: uuid.UUID) -> GameSession:
    session = await db.get(GameSession, session_id)
    if not session or session.user_id != user.id:
        raise HTTPException(404, "session not found")
    return session


def _ensure_active(session: GameSession) -> None:
    if session.status != "active":
        raise HTTPException(409, "session is not active")


async def _deck_context(db: Db, user, session: GameSession, served_ids: list[int]):
    """Всё, что нужно колоде: веса вкуса, антиповторы, каталог, фильтры. Общее для /next, /active и /result."""
    cfg = get_settings()
    swipes = (await db.execute(
        select(Swipe.action, Swipe.rating, Movie.genres, Swipe.opened_details, Swipe.dwell_ms)
        .join(Movie, Movie.id == Swipe.movie_id)
        .where(Swipe.session_id == session.id, Swipe.undone_at.is_(None))
    )).all()
    weights = deck.session_weights(session.initial_genres, [
        (a, r, g or [], deck.signal_bonus(bool(od), dw or 0)) for a, r, g, od, dw in swipes])
    states = {
        row.movie_id: (row.state, row.updated_at)
        for row in (await db.execute(select(UserMovieState).where(UserMovieState.user_id == user.id))).scalars()
    }
    prev_session = (await db.execute(
        select(GameSession.id).where(GameSession.user_id == user.id, GameSession.id != session.id)
        .order_by(GameSession.started_at.desc()).limit(1)
    )).scalar_one_or_none()
    last_ids: set[int] = set()
    if prev_session:
        last_ids = set((await db.execute(
            select(SessionCard.movie_id).where(SessionCard.session_id == prev_session)
        )).scalars())
    tiers, watched = deck.compute_tiers(states, last_ids, utcnow(), cfg.skip_cooldown_days)
    catalog = await get_catalog(db)
    options = await db.get(SessionOptions, session.id)
    return {"weights": weights, "tiers": tiers, "watched": watched, "catalog": catalog,
            "filters": (options.filters if options else {}) or {},
            "strict": list(session.initial_genres or [])}


def _remaining(ctx: dict, session: GameSession, taken: set[int], n: int) -> int:
    return deck.count_available(ctx["catalog"], n=n, excluded=taken | ctx["watched"], tiers=ctx["tiers"],
                                surprise=session.surprise, filters=ctx["filters"], strict_genres=ctx["strict"])


async def _serve_batch(db: Db, user, session: GameSession, n: int) -> DeckOut:
    _ensure_active(session)
    cfg = get_settings()
    served_rows = (await db.execute(
        select(SessionCard.movie_id, SessionCard.position)
        .where(SessionCard.session_id == session.id).order_by(SessionCard.position)
    )).all()
    served_ids = [r.movie_id for r in served_rows]
    quota = session.limit - len(served_ids)
    n = min(n, quota)
    if n <= 0:
        return DeckOut(session_id=session.id, cards=[], served_total=len(served_ids),
                       planned_total=len(served_ids), exhausted=True)

    ctx = await _deck_context(db, user, session, served_ids)
    by_id = {item.id: item for item in ctx["catalog"]}
    history_primary = [by_id[mid].genres[0] for mid in served_ids[-3:] if mid in by_id and by_id[mid].genres]
    rng = random.Random(f"{session.seed}:{len(served_ids)}")
    picked = deck.build_batch(
        ctx["catalog"], n=n, weights=ctx["weights"], excluded=set(served_ids) | ctx["watched"],
        tiers=ctx["tiers"], rng=rng, surprise=session.surprise, explore_ratio=cfg.explore_ratio,
        temperature=cfg.temperature, history_primary=history_primary, filters=ctx["filters"],
        strict_genres=ctx["strict"],
    )
    movies = {m.id: m for m in (await db.execute(
        select(Movie).where(Movie.id.in_([item.id for item in picked]))
    )).scalars()} if picked else {}
    ordered = [movies[item.id] for item in picked if item.id in movies]
    base = len(served_ids)
    for i, movie in enumerate(ordered):
        db.add(SessionCard(session_id=session.id, position=base + i, movie_id=movie.id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "concurrent next request")

    served_total = base + len(ordered)
    # Сколько подходящих карточек осталось ПОСЛЕ этой порции: по нему честно считаем exhausted и план.
    remaining = _remaining(ctx, session, set(served_ids) | {m.id for m in ordered}, n)
    planned_total = min(session.limit, served_total + remaining)
    exhausted = served_total >= planned_total
    return DeckOut(session_id=session.id, cards=[movie_out(movie) for movie in ordered],
                   served_total=served_total, planned_total=planned_total, exhausted=exhausted)


@router.post("", response_model=DeckOut)
async def create_session(body: SessionCreate, db: Db, user: CurrentUser):
    active = (await db.execute(
        select(GameSession).where(GameSession.user_id == user.id, GameSession.status == "active")
    )).scalars().all()
    for previous in active:
        previous.status = "abandoned"
        previous.finished_at = utcnow()
    initial = canonical_genres(body.initial_genres)
    session = GameSession(user_id=user.id, limit=body.limit, seed=random.randrange(2**31),
                          surprise=body.surprise, initial_genres=initial)
    db.add(session)
    await db.flush()
    db.add(SessionOptions(session_id=session.id,
                          filters=body.filters.model_dump(exclude_none=True) if body.filters else {}))
    await db.commit()
    return await _serve_batch(db, user, session, min(FIRST_BATCH, body.limit))


@router.get("/active")
async def active_session(db: Db, user: CurrentUser):
    session = (await db.execute(
        select(GameSession).where(GameSession.user_id == user.id, GameSession.status == "active")
        .order_by(GameSession.started_at.desc()).limit(1)
    )).scalar_one_or_none()
    if not session:
        return {"session": None}
    card_rows = (await db.execute(
        select(SessionCard, Movie).join(Movie, Movie.id == SessionCard.movie_id)
        .where(SessionCard.session_id == session.id).order_by(SessionCard.position)
    )).all()
    event_rows = (await db.execute(
        select(Swipe).where(Swipe.session_id == session.id, Swipe.undone_at.is_(None))
        .order_by(Swipe.id)
    )).scalars().all()
    options = await db.get(SessionOptions, session.id)
    served_ids = [movie.id for _, movie in card_rows]
    ctx = await _deck_context(db, user, session, served_ids)
    planned_total = min(session.limit, len(served_ids) + _remaining(ctx, session, set(served_ids), FIRST_BATCH))
    cards = [movie_out(movie).model_dump() for _, movie in card_rows]
    events = [{"movie_id": str(event.movie_id), "type": event.action, "rating": event.rating,
               "created_at": event.created_at.isoformat()} for event in event_rows]
    return {"session": {
        "session_id": str(session.id), "limit": session.limit, "surprise": session.surprise,
        "initial_genres": session.initial_genres or [], "filters": options.filters if options else {},
        "started_at": session.started_at.isoformat(), "cards": cards, "events": events,
        "served_total": len(cards), "swipe_count": len(events),
        "planned_total": planned_total, "exhausted": len(cards) >= planned_total,
    }}


@router.get("/{session_id}/next", response_model=DeckOut)
async def next_cards(session_id: uuid.UUID, db: Db, user: CurrentUser,
                     n: int = Query(5, ge=1, le=MAX_BATCH)):
    session = await _owned(db, user, session_id)
    return await _serve_batch(db, user, session, n)


@router.get("/{session_id}/result")
async def session_result(session_id: uuid.UUID, db: Db, user: CurrentUser):
    """Итог подбора: лучшее совпадение, 2–3 хороших варианта и то, что отобрал сам пользователь.
    Работает для любой сессии (активной, завершённой, прерванной) — после перезагрузки данные берутся отсюда."""
    session = await _owned(db, user, session_id)
    cfg = get_settings()
    served_ids = list((await db.execute(
        select(SessionCard.movie_id).where(SessionCard.session_id == session.id)
        .order_by(SessionCard.position))).scalars())
    swipes = (await db.execute(
        select(Swipe.movie_id, Swipe.action, Swipe.rating, Swipe.opened_details, Swipe.dwell_ms, Movie.genres)
        .join(Movie, Movie.id == Swipe.movie_id)
        .where(Swipe.session_id == session.id, Swipe.undone_at.is_(None)).order_by(Swipe.id)
    )).all()
    initial = list(session.initial_genres or [])
    weights = deck.session_weights(initial, [
        (a, r, g or [], deck.signal_bonus(bool(od), dw or 0)) for _, a, r, od, dw, g in swipes])
    reacted = {mid for mid, *_ in swipes}
    saved_ids = [mid for mid, a, *_ in swipes if a == "right"]
    counts = {"saved": len(saved_ids),
              "watched": sum(1 for _, a, *_ in swipes if a == "up"),
              "skipped": sum(1 for _, a, *_ in swipes if a == "left")}

    states = {row.movie_id: (row.state, row.updated_at) for row in (await db.execute(
        select(UserMovieState).where(UserMovieState.user_id == user.id))).scalars()}
    tiers, watched_before = deck.compute_tiers(states, set(), utcnow(), cfg.skip_cooldown_days)
    options = await db.get(SessionOptions, session.id)
    filters = (options.filters if options else {}) or {}
    catalog = await get_catalog(db)
    pool = deck.recommend_pool(catalog, n=session.limit, excluded=reacted | watched_before, tiers=tiers,
                               weights=weights, surprise=session.surprise, filters=filters,
                               strict_genres=initial)

    saved_movies = {m.id: m for m in (await db.execute(
        select(Movie).where(Movie.id.in_(saved_ids)))).scalars()} if saved_ids else {}
    saved_ranked = sorted(
        (saved_movies[i] for i in saved_ids if i in saved_movies),
        key=lambda m: (-deck.rank_score(m.genres or [], m.kp_rating or m.imdb_rating, weights), m.id))
    ranked_ids = [m.id for m in saved_ranked] + [c.id for c in pool]
    top_ids = ranked_ids[:4]                                   # лучшее + до 3 вариантов
    extra_ids = [i for i in top_ids if i not in saved_movies]
    movies = dict(saved_movies)
    if extra_ids:
        movies.update({m.id: m for m in (await db.execute(select(Movie).where(Movie.id.in_(extra_ids)))).scalars()})
    flags = {r.movie_id: collection_flags(r) for r in (await db.execute(
        select(UserMovieCollection).where(UserMovieCollection.user_id == user.id,
                                          UserMovieCollection.movie_id.in_(set(saved_ids) | set(top_ids))))).scalars()}
    liked = [(m.title, list(m.genres or [])) for m in saved_ranked]
    liked_ids = [m.id for m in saved_ranked]

    def pack(movie: Movie) -> dict:
        rating = movie.kp_rating or movie.imdb_rating
        genres = list(movie.genres or [])
        return {"movie": movie_out(movie).model_dump(),
                "match": deck.match_percent(genres, rating, weights),
                "reasons": deck.match_reasons(genres, rating, weights, initial, liked, movie.id, liked_ids),
                "saved": movie.id in saved_movies, "collection": flags.get(movie.id)}

    top = [pack(movies[i]) for i in top_ids if i in movies]
    return {
        "session_id": str(session.id), "status": session.status, "limit": session.limit,
        "served_total": len(served_ids), "answered": len(swipes), "counts": counts,
        "ended_early": len(served_ids) < session.limit,
        "best": top[0] if top else None, "alternatives": top[1:],
        "saved": [pack(m) for m in saved_ranked],
    }


@router.post("/{session_id}/events")
async def post_events(session_id: uuid.UUID, body: EventsIn, db: Db, user: CurrentUser):
    session = await _owned(db, user, session_id)
    _ensure_active(session)
    ids = [event.event_id for event in body.events]
    known = set((await db.execute(select(Swipe.event_id).where(Swipe.event_id.in_(ids)))).scalars())
    requested_movie_ids = [event.movie_id for event in body.events]
    in_session = set((await db.execute(
        select(SessionCard.movie_id).where(SessionCard.session_id == session.id,
                                           SessionCard.movie_id.in_(requested_movie_ids))
    )).scalars())
    # Фильмы, на которые в этой сессии уже есть (не отменённая) реакция.
    reacted = set((await db.execute(
        select(Swipe.movie_id).where(Swipe.session_id == session.id, Swipe.undone_at.is_(None))
    )).scalars())
    accepted = duplicates = 0
    for event in body.events:
        if event.event_id in known:
            continue
        if event.movie_id not in in_session:
            raise HTTPException(400, f"movie {event.movie_id} was not served in this session")
        if event.movie_id in reacted:      # повторный свайп того же фильма (двойной клик / гонка)
            duplicates += 1
            continue
        current_state = await db.get(UserMovieState, (user.id, event.movie_id))
        current_collection = await db.get(UserMovieCollection, (user.id, event.movie_id))
        swipe = Swipe(event_id=event.event_id, session_id=session.id, user_id=user.id,
                      movie_id=event.movie_id, action=event.type, rating=event.rating,
                      dwell_ms=event.dwell_ms, opened_details=event.opened_details)
        db.add(swipe)
        await db.flush()
        collection_snapshot = None
        if current_collection:
            collection_snapshot = {
                "is_favorite": current_collection.is_favorite,
                "in_watchlist": current_collection.in_watchlist,
                "watched": current_collection.watched,
                "skipped": current_collection.skipped,
                "rating": current_collection.rating,
                "note": current_collection.note,
                "watched_at": current_collection.watched_at.isoformat() if current_collection.watched_at else None,
                "updated_at": current_collection.updated_at.isoformat() if current_collection.updated_at else None,
            }
        db.add(SwipeStateSnapshot(
            swipe_id=swipe.id,
            previous_state=current_state.state if current_state else None,
            previous_rating=current_state.rating if current_state else None,
            previous_updated_at=current_state.updated_at if current_state else None,
            previous_collection=collection_snapshot,
        ))
        new_state = {"right": "liked", "left": "skipped", "up": "watched"}[event.type]
        if not current_collection:
            current_collection = UserMovieCollection(user_id=user.id, movie_id=event.movie_id)
            db.add(current_collection)
        if event.type == "right":
            current_collection.in_watchlist = True
            current_collection.skipped = False
        elif event.type == "left":
            current_collection.skipped = True
            current_collection.in_watchlist = False
        else:
            current_collection.watched = True
            current_collection.skipped = False
            current_collection.in_watchlist = False
            current_collection.rating = event.rating * 2 if event.rating else current_collection.rating
            current_collection.watched_at = utcnow()
        current_collection.updated_at = utcnow()
        # Preserve a previously watched flag when the same movie is added to a list.
        effective_state = "watched" if current_collection.watched else new_state
        effective_rating = event.rating if event.rating is not None else (current_state.rating if current_state else None)
        if current_state:
            current_state.state, current_state.rating, current_state.updated_at = effective_state, effective_rating, utcnow()
        else:
            db.add(UserMovieState(user_id=user.id, movie_id=event.movie_id,
                                  state=effective_state, rating=effective_rating))
        accepted += 1
        reacted.add(event.movie_id)
        await db.flush()
        known.add(event.event_id)
    await db.commit()
    return {"accepted": accepted, "duplicates": duplicates}


@router.post("/{session_id}/undo")
async def undo(session_id: uuid.UUID, db: Db, user: CurrentUser):
    session = await _owned(db, user, session_id)
    _ensure_active(session)
    last = (await db.execute(
        select(Swipe).where(Swipe.session_id == session.id, Swipe.undone_at.is_(None))
        .order_by(Swipe.id.desc()).limit(1)
    )).scalar_one_or_none()
    if not last:
        return {"movie_id": None}
    snapshot = await db.get(SwipeStateSnapshot, last.id)
    last.undone_at = utcnow()
    state_row = await db.get(UserMovieState, (user.id, last.movie_id))
    if state_row:
        if snapshot and snapshot.previous_state:
            state_row.state = snapshot.previous_state
            state_row.rating = snapshot.previous_rating
            state_row.updated_at = snapshot.previous_updated_at or utcnow()
        else:
            await db.delete(state_row)
    elif snapshot and snapshot.previous_state:
        db.add(UserMovieState(user_id=user.id, movie_id=last.movie_id,
                              state=snapshot.previous_state, rating=snapshot.previous_rating,
                              updated_at=snapshot.previous_updated_at or utcnow()))
    collection = await db.get(UserMovieCollection, (user.id, last.movie_id))
    previous = snapshot.previous_collection if snapshot else None
    if previous is None:
        if collection:
            await db.delete(collection)
    else:
        from datetime import datetime
        if not collection:
            collection = UserMovieCollection(user_id=user.id, movie_id=last.movie_id)
            db.add(collection)
        for key in ("is_favorite", "in_watchlist", "watched", "skipped", "rating", "note"):
            setattr(collection, key, previous.get(key))
        collection.watched_at = datetime.fromisoformat(previous["watched_at"]) if previous.get("watched_at") else None
        collection.updated_at = datetime.fromisoformat(previous["updated_at"]) if previous.get("updated_at") else utcnow()
    await db.commit()
    return {"movie_id": str(last.movie_id)}


@router.post("/{session_id}/finish")
async def finish(session_id: uuid.UUID, db: Db, user: CurrentUser):
    session = await _owned(db, user, session_id)
    if session.status == "active":
        session.status, session.finished_at = "finished", utcnow()
        await db.commit()
    count = (await db.execute(
        select(func.count()).select_from(Swipe).where(Swipe.session_id == session.id,
                                                       Swipe.undone_at.is_(None))
    )).scalar_one()
    return {"status": session.status, "swipes": count}
