import random
import uuid

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError

from ..config import get_settings
from ..deps import CurrentUser, Db
from ..models import GameSession, Movie, SessionCard, Swipe, UserMovieState, utcnow
from ..schemas import DeckOut, EventsIn, SessionCreate, movie_out
from ..services import deck
from ..services.catalog import get_catalog
from ..services.genres import ALL_GENRES

router = APIRouter(prefix="/sessions", tags=["sessions"])
FIRST_BATCH = 8
MAX_BATCH = 10


async def _owned(db: Db, user, session_id: uuid.UUID) -> GameSession:
    s = await db.get(GameSession, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(404, "session not found")
    return s


async def _serve_batch(db: Db, user, session: GameSession, n: int) -> DeckOut:
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

    swipes = (await db.execute(
        select(Swipe.action, Swipe.rating, Movie.genres)
        .join(Movie, Movie.id == Swipe.movie_id)
        .where(Swipe.session_id == session.id, Swipe.undone_at.is_(None))
    )).all()
    weights = deck.session_weights(session.initial_genres, [(a, r, g or []) for a, r, g in swipes])

    states = {
        r.movie_id: (r.state, r.updated_at)
        for r in (await db.execute(select(UserMovieState).where(UserMovieState.user_id == user.id))).scalars()
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
    by_id = {c.id: c for c in catalog}
    history_primary = [by_id[i].genres[0] for i in served_ids[-3:] if i in by_id and by_id[i].genres]

    rng = random.Random(f"{session.seed}:{len(served_ids)}")
    picked = deck.build_batch(
        catalog, n=n, weights=weights, excluded=set(served_ids) | watched, tiers=tiers, rng=rng,
        surprise=session.surprise, explore_ratio=cfg.explore_ratio, temperature=cfg.temperature,
        history_primary=history_primary,
    )

    movies = {m.id: m for m in (await db.execute(
        select(Movie).where(Movie.id.in_([p.id for p in picked]))
    )).scalars()} if picked else {}
    ordered = [movies[p.id] for p in picked if p.id in movies]

    base = len(served_ids)
    for i, m in enumerate(ordered):
        db.add(SessionCard(session_id=session.id, position=base + i, movie_id=m.id))
    try:
        await db.commit()
    except IntegrityError:  # параллельный /next — клиент должен слать запросы по очереди
        await db.rollback()
        raise HTTPException(409, "concurrent next request")

    served_total = base + len(ordered)
    exhausted = len(ordered) < n or served_total >= session.limit
    return DeckOut(
        session_id=session.id, cards=[movie_out(m) for m in ordered], served_total=served_total,
        planned_total=served_total if exhausted else session.limit, exhausted=exhausted,
    )


@router.post("", response_model=DeckOut)
async def create_session(body: SessionCreate, db: Db, user: CurrentUser):
    # незавершённые прошлые сессии помечаем брошенными
    prev = (await db.execute(
        select(GameSession).where(GameSession.user_id == user.id, GameSession.status == "active")
    )).scalars().all()
    for p in prev:
        p.status = "abandoned"

    initial = [g for g in body.initial_genres if g in ALL_GENRES]
    session = GameSession(user_id=user.id, limit=body.limit, seed=random.randrange(2**31),
                          surprise=body.surprise, initial_genres=initial)
    db.add(session)
    await db.commit()
    return await _serve_batch(db, user, session, min(FIRST_BATCH, body.limit))


@router.get("/{session_id}/next", response_model=DeckOut)
async def next_cards(session_id: uuid.UUID, db: Db, user: CurrentUser, n: int = Query(5, ge=1, le=MAX_BATCH)):
    session = await _owned(db, user, session_id)
    return await _serve_batch(db, user, session, n)


@router.post("/{session_id}/events")
async def post_events(session_id: uuid.UUID, body: EventsIn, db: Db, user: CurrentUser):
    session = await _owned(db, user, session_id)
    ids = [e.event_id for e in body.events]
    known = set((await db.execute(select(Swipe.event_id).where(Swipe.event_id.in_(ids)))).scalars())
    in_session = set((await db.execute(
        select(SessionCard.movie_id).where(SessionCard.session_id == session.id,
                                           SessionCard.movie_id.in_([e.movie_id for e in body.events]))
    )).scalars())

    accepted = 0
    for e in body.events:
        if e.event_id in known:
            continue                       # повторная отправка — игнорируем
        if e.movie_id not in in_session:
            raise HTTPException(400, f"movie {e.movie_id} was not served in this session")
        if e.type == "up" and e.rating is None:
            raise HTTPException(400, "rating is required for 'up'")
        db.add(Swipe(event_id=e.event_id, session_id=session.id, user_id=user.id, movie_id=e.movie_id,
                     action=e.type, rating=e.rating, dwell_ms=e.dwell_ms))
        state = {"right": "liked", "left": "skipped", "up": "watched"}[e.type]
        row = await db.get(UserMovieState, (user.id, e.movie_id))
        if row:
            row.state, row.rating, row.updated_at = state, e.rating, utcnow()
        else:
            db.add(UserMovieState(user_id=user.id, movie_id=e.movie_id, state=state, rating=e.rating))
        accepted += 1
        await db.flush()
    await db.commit()
    return {"accepted": accepted}


@router.post("/{session_id}/undo")
async def undo(session_id: uuid.UUID, db: Db, user: CurrentUser):
    session = await _owned(db, user, session_id)
    last = (await db.execute(
        select(Swipe).where(Swipe.session_id == session.id, Swipe.undone_at.is_(None))
        .order_by(Swipe.id.desc()).limit(1)
    )).scalar_one_or_none()
    if not last:
        return {"movie_id": None}
    last.undone_at = utcnow()
    await db.execute(delete(UserMovieState).where(
        UserMovieState.user_id == user.id, UserMovieState.movie_id == last.movie_id))
    await db.commit()
    return {"movie_id": str(last.movie_id)}


@router.post("/{session_id}/finish")
async def finish(session_id: uuid.UUID, db: Db, user: CurrentUser):
    session = await _owned(db, user, session_id)
    if session.status == "active":
        session.status, session.finished_at = "finished", utcnow()
        await db.commit()
    count = (await db.execute(
        select(func.count()).select_from(Swipe).where(Swipe.session_id == session.id, Swipe.undone_at.is_(None))
    )).scalar_one()
    return {"status": session.status, "swipes": count}
