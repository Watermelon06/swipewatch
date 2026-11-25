async def test_collection_and_dashboard(client):
    data = await client.post("/api/sessions", json={"limit": 10, "initial_genres": []})
    assert data.status_code == 200
    movie_id = int(data.json()["cards"][0]["id"])

    saved = await client.put(f"/api/me/collection/{movie_id}", json={
        "is_favorite": True, "in_watchlist": True, "note": "Посмотреть на выходных"
    })
    assert saved.status_code == 200
    favorites = await client.get("/api/me/collection", params={"view": "favorites"})
    assert favorites.status_code == 200
    assert favorites.json()["items"][0]["movie"]["id"] == str(movie_id)
    dashboard = await client.get("/api/me/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["counts"]["favorites"] == 1
    assert dashboard.json()["counts"]["watchlist"] == 1


async def test_active_session_can_be_restored_and_closed(client):
    started = await client.post("/api/sessions", json={"limit": 10, "initial_genres": []})
    sid = started.json()["session_id"]
    active = await client.get("/api/sessions/active")
    assert active.status_code == 200
    assert active.json()["session"]["session_id"] == sid
    assert len(active.json()["session"]["cards"]) == 8

    card = started.json()["cards"][0]
    event = {"event_id": "v2-event-00001", "type": "right", "movie_id": int(card["id"])}
    saved = await client.post(f"/api/sessions/{sid}/events", json={"events": [event]})
    assert saved.status_code == 200
    active = await client.get("/api/sessions/active")
    assert len(active.json()["session"]["events"]) == 1

    assert (await client.post(f"/api/sessions/{sid}/finish")).status_code == 200
    assert (await client.get(f"/api/sessions/{sid}/next")).status_code == 409
    assert (await client.post(f"/api/sessions/{sid}/events", json={"events": [event]})).status_code == 409
    assert (await client.post(f"/api/sessions/{sid}/undo")).status_code == 409


async def test_vk_provider_is_optional(client):
    response = await client.get("/api/auth/providers")
    assert response.status_code == 200
    assert "vk" in response.json()
