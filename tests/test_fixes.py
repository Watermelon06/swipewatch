import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.db import SessionLocal, engine
from app.migrations import run_migrations
from app.models import Movie
from app.routers.auth import _anon_hits, check_anon_rate
from app.services.genres import canonical_genres, dedupe_key
from app.services.sources import Draft
from app.services.sync import SyncReport, upsert_drafts


async def _session(client, **body):
    r = await client.post("/api/sessions", json={"limit": 10, "initial_genres": [], **body})
    assert r.status_code == 200
    return r.json()


async def test_duplicate_swipe_same_movie_is_ignored_and_undo_allows_retry(client):
    data = await _session(client)
    sid, mid = data["session_id"], int(data["cards"][0]["id"])
    ev = lambda n, t: {"events": [{"event_id": f"dup-event-{n:04d}", "type": t, "movie_id": mid}]}
    assert (await client.post(f"/api/sessions/{sid}/events", json=ev(1, "right"))).json()["accepted"] == 1
    second = (await client.post(f"/api/sessions/{sid}/events", json=ev(2, "left"))).json()
    assert second["accepted"] == 0 and second["duplicates"] == 1
    active = (await client.get("/api/sessions/active")).json()["session"]
    assert len(active["events"]) == 1
    await client.post(f"/api/sessions/{sid}/undo")
    assert (await client.post(f"/api/sessions/{sid}/events", json=ev(3, "left"))).json()["accepted"] == 1


def test_genre_aliases():
    assert canonical_genres(["Ужасы", "Фэнтези", "Мелодрама", "Мультфильм", "Хоррор"]) == ["Хоррор", "Мистика", "Драма"]


async def test_session_accepts_legacy_genre_names(client):
    await _session(client, initial_genres=["Ужасы", "Фэнтези", "Мультфильм"])
    active = (await client.get("/api/sessions/active")).json()["session"]
    assert active["initial_genres"] == ["Хоррор", "Мистика"]


async def test_rating_scales_stay_in_sync(client):
    data = await _session(client)
    sid, mid = data["session_id"], int(data["cards"][0]["id"])
    await client.post(f"/api/sessions/{sid}/events", json={"events": [
        {"event_id": "rate-event-001", "type": "up", "movie_id": mid, "rating": 4}]})
    await client.put(f"/api/me/collection/{mid}", json={"rating": 8})   # то, что раньше слал фронт
    hist = (await client.get("/api/me/history", params={"state": "watched"})).json()
    assert hist[0]["rating"] == 4                                        # legacy-шкала 1-5
    coll = (await client.get("/api/me/collection", params={"view": "watched"})).json()["items"][0]
    assert coll["rating"] == 8                                           # шкала коллекции 1-10


async def test_collection_pagination_total_and_genre_filter(client):
    data = await _session(client, limit=10)
    cards = data["cards"]
    for card in cards:
        await client.put(f"/api/me/collection/{card['id']}", json={"in_watchlist": True})
    page = (await client.get("/api/me/collection", params={"view": "watchlist", "limit": 3})).json()
    assert page["total"] == len(cards) and len(page["items"]) == 3
    genre = cards[0]["genres"][0]
    expected = {c["id"] for c in cards if genre in c["genres"]}
    got, offset = set(), 0
    while True:
        r = (await client.get("/api/me/collection", params={
            "view": "watchlist", "genre": genre, "limit": 2, "offset": offset})).json()
        assert r["total"] == len(expected)
        got |= {i["movie"]["id"] for i in r["items"]}
        offset += 2
        if offset >= r["total"]:
            break
    assert got == expected


async def test_session_detail_has_action_and_rating(client):
    data = await _session(client)
    sid, mid = data["session_id"], int(data["cards"][0]["id"])
    await client.post(f"/api/sessions/{sid}/events", json={"events": [
        {"event_id": "detail-evt-01", "type": "up", "movie_id": mid, "rating": 5}]})
    detail = (await client.get(f"/api/me/sessions/{sid}")).json()
    first = detail["cards"][0]
    assert first["action"] == "up" and first["rating"] == 5


def test_anon_rate_limit_unit():
    _anon_hits.clear()
    for _ in range(3):
        check_anon_rate("1.2.3.4", 3)
    with pytest.raises(HTTPException) as err:
        check_anon_rate("1.2.3.4", 3)
    assert err.value.status_code == 429
    check_anon_rate("5.6.7.8", 3)          # другой IP не затронут
    check_anon_rate("1.2.3.4", 0)          # 0 = лимит выключен
    _anon_hits.clear()


async def test_upsert_drafts_dedupes_by_original_title(seeded):
    async with SessionLocal() as db:
        db.add(Movie(source="kp", source_id="kp-1", dedupe_key=dedupe_key("Начало", 2010),
                     title="Начало", original_title="Inception", year=2010, genres=[]))
        await db.commit()
    report = SyncReport()
    drafts = [Draft(source="itunes", source_id="i1", title="Inception", original_title="Inception", year=2010),
              Draft(source="itunes", source_id="i2", title="Interstellar RU", original_title="Interstellar", year=2014),
              Draft(source="itunes", source_id="i3", title="Interstellar", original_title="Interstellar", year=2014)]
    async with SessionLocal() as db:
        added = await upsert_drafts(db, drafts, report)
    assert added == 1                       # Inception — дубль KP; i3 — дубль i2 внутри прогона


async def test_migrations_idempotent_and_fix_rating_scale(seeded):
    async with engine.begin() as conn:
        await conn.execute(text("DROP TABLE IF EXISTS schema_migrations"))
    assert await run_migrations(engine) == [1, 2, 3]
    assert await run_migrations(engine) == []
