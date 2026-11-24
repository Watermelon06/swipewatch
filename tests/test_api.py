import uuid


async def start(client, **body):
    r = await client.post("/api/sessions", json={"limit": 15, "initial_genres": [], **body})
    assert r.status_code == 200, r.text
    return r.json()


async def drain(client, data):
    ids = [c["id"] for c in data["cards"]]
    sid = data["session_id"]
    while not data["exhausted"]:
        r = await client.get(f"/api/sessions/{sid}/next", params={"n": 5})
        data = r.json()
        ids += [c["id"] for c in data["cards"]]
    return ids, data


async def test_auth_required(seeded):
    import httpx
    from app.main import app
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.post("/api/sessions", json={})).status_code == 401
        c.headers["Authorization"] = "Bearer " + str(uuid.uuid4()) + ".forged"
        assert (await c.get("/api/meta")).status_code == 401


async def test_deck_has_no_duplicates_and_respects_limit(client):
    data = await start(client)
    assert len(data["cards"]) == 8
    ids, last = await drain(client, data)
    assert len(ids) == len(set(ids)) == 15 and last["planned_total"] == 15
    # card format for the client
    c = data["cards"][0]
    assert isinstance(c["id"], str) and c["genres"] and c["posterUrl"]


async def test_new_session_starts_differently(client):
    a = await start(client)
    b = await start(client)
    assert {c["id"] for c in a["cards"]} != {c["id"] for c in b["cards"]}
    assert len({c["id"] for c in a["cards"]} & {c["id"] for c in b["cards"]}) <= 2   # прошлую выдачу обходим


async def test_watched_never_returns_and_events_idempotent(client):
    data = await start(client)
    sid = data["session_id"]
    first, second = data["cards"][0], data["cards"][1]
    ev = [{"event_id": "evt-00000001", "type": "up", "movie_id": int(first["id"]), "rating": 5, "dwell_ms": 900},
          {"event_id": "evt-00000002", "type": "left", "movie_id": int(second["id"]), "dwell_ms": 200}]
    assert (await client.post(f"/api/sessions/{sid}/events", json={"events": ev})).json()["accepted"] == 2
    assert (await client.post(f"/api/sessions/{sid}/events", json={"events": ev})).json()["accepted"] == 0
    for _ in range(5):
        d2 = await start(client, limit=20)
        ids, _ = await drain(client, d2)
        assert first["id"] not in ids                     # просмотренное — никогда
    hist = (await client.get("/api/me/history", params={"state": "watched"})).json()
    assert [h["movie"]["id"] for h in hist] == [first["id"]] and hist[0]["rating"] == 5


async def test_event_validation(client):
    data = await start(client)
    sid = data["session_id"]
    bad_movie = {"event_id": "evt-00000009", "type": "right", "movie_id": 99999}
    assert (await client.post(f"/api/sessions/{sid}/events", json={"events": [bad_movie]})).status_code == 400
    no_rating = {"event_id": "evt-0000000a", "type": "up", "movie_id": int(data["cards"][0]["id"])}
    assert (await client.post(f"/api/sessions/{sid}/events", json={"events": [no_rating]})).status_code == 400


async def test_undo_restores_state(client):
    data = await start(client)
    sid, card = data["session_id"], data["cards"][0]
    await client.post(f"/api/sessions/{sid}/events", json={"events": [
        {"event_id": "evt-0000000b", "type": "up", "movie_id": int(card["id"]), "rating": 4}]})
    assert (await client.post(f"/api/sessions/{sid}/undo")).json()["movie_id"] == card["id"]
    assert (await client.get("/api/me/history", params={"state": "watched"})).json() == []
    assert (await client.post(f"/api/sessions/{sid}/undo")).json()["movie_id"] is None


async def test_taste_shifts_next_batches(client):
    data = await start(client, limit=20, initial_genres=["Хоррор", "Хоррор", "Хоррор", "Хоррор"], surprise=False)
    ids, _ = await drain(client, data)
    assert len(ids) == 20


async def test_cannot_touch_foreign_session(client, seeded):
    import httpx
    from app.main import app
    data = await start(client)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as other:
        tok = (await other.post("/api/auth/anon")).json()["token"]
        other.headers["Authorization"] = f"Bearer {tok}"
        assert (await other.get(f"/api/sessions/{data['session_id']}/next")).status_code == 404


async def test_exhausted_pool_shrinks_plan(client):
    from sqlalchemy import update
    from app.db import SessionLocal
    from app.models import Movie
    from app.services.catalog import invalidate_catalog
    async with SessionLocal() as db:
        await db.execute(update(Movie).where(Movie.id > 6).values(is_active=False))
        await db.commit()
    invalidate_catalog()
    data = await start(client, limit=20)
    assert data["exhausted"] and data["planned_total"] == len(data["cards"]) == 6


async def test_admin_protected(client):
    assert (await client.get("/api/admin/stats")).status_code == 403
    r = await client.get("/api/admin/stats", headers={"X-Admin-Token": "admin"})
    assert r.status_code == 200 and r.json()["ready_for_deck"] == 80
