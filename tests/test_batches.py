"""Пачки 1–5: дозагрузка колоды, жанровый фильтр, итог подбора, валидация, токены."""
import time
import uuid

import httpx
from sqlalchemy import update

from app.db import SessionLocal
from app.main import app
from app.models import Movie
from app.security import make_token, parse_token_full
from app.services import deck
from app.services.catalog import CatalogItem, invalidate_catalog
from tests.test_api import drain, start


async def _only_first(n):
    async with SessionLocal() as db:
        await db.execute(update(Movie).where(Movie.id > n).values(is_active=False))
        await db.commit()
    invalidate_catalog()


async def test_next_drains_pool_and_flags_exhausted_exactly(client):
    """F1/F2: ровно 8 подходящих фильмов (= размер первой порции) — сессия сразу exhausted, план честный."""
    await _only_first(8)
    data = await start(client, limit=15)
    assert len(data["cards"]) == 8 and data["exhausted"] and data["planned_total"] == 8
    nxt = (await client.get(f"/api/sessions/{data['session_id']}/next", params={"n": 5})).json()
    assert nxt["cards"] == [] and nxt["exhausted"]


async def test_next_batches_reach_limit(client):
    data = await start(client, limit=20)
    ids, last = await drain(client, data)
    assert len(ids) == len(set(ids)) == 20 and last["exhausted"]
    assert data["planned_total"] == 20      # каталог большой -> план = лимит


async def test_planned_total_shrinks_when_pool_smaller_than_limit(client):
    await _only_first(12)
    data = await start(client, limit=20)
    assert data["planned_total"] == 12 and not data["exhausted"]
    ids, last = await drain(client, data)
    assert len(ids) == 12 and last["planned_total"] == 12


async def test_genre_session_never_repeats_skipped_or_liked(client):
    """F3/F4: по жанру — ни повторов из прошлой сессии, ни скипнутых, ни «чужих» жанров."""
    first = await start(client, limit=10, initial_genres=["Комедия"])
    sid = first["session_id"]
    ids1, _ = await drain(client, first)
    for i, mid in enumerate(ids1[:3]):
        await client.post(f"/api/sessions/{sid}/events", json={"events": [
            {"event_id": f"ev-left-{i:04d}", "type": "left", "movie_id": int(mid)}]})
    await client.post(f"/api/sessions/{sid}/finish")
    second = await start(client, limit=20, initial_genres=["Комедия"])
    ids2, _ = await drain(client, second)
    assert not set(ids1) & set(ids2)
    cards = (await client.get("/api/sessions/active")).json()["session"]["cards"]
    assert all("Комедия" in c["genres"] for c in cards)


def test_null_fields_are_not_filtered_out():
    """F10: пустая длительность/рейтинг/возраст не отсеивают фильм."""
    c = [CatalogItem(1, ("Драма",), None, "kp", 2010, "Фильм", None, None),
         CatalogItem(2, ("Драма",), 5.0, "kp", 2010, "Фильм", 200, "18+")]
    got = deck.build_batch(c, n=5, weights={}, excluded=set(), tiers={}, rng=__import__("random").Random(1),
                           filters={"max_duration": 120, "min_rating": 7, "max_age": 12})
    assert [x.id for x in got] == [1]


def test_details_and_dwell_give_weak_plus_only_to_positive_actions():
    base = deck.session_weights([], [("right", None, ["Драма"], 0.0)])
    plus = deck.session_weights([], [("right", None, ["Драма"], deck.signal_bonus(True, 6000))])
    left = deck.session_weights([], [("left", None, ["Драма"], deck.signal_bonus(True, 6000))])
    assert plus["Драма"] == base["Драма"] + 0.75 and left["Драма"] == -1


async def test_year_range_validation_gives_422_with_readable_message(client):
    r = await client.post("/api/sessions", json={"limit": 10, "filters": {"year_from": 2020, "year_to": 2010}})
    assert r.status_code == 422
    assert "Год" in str(r.json()["detail"])


async def _react(client, sid, mid, kind, n, **extra):
    r = await client.post(f"/api/sessions/{sid}/events", json={"events": [
        {"event_id": f"res-{kind}-{n:05d}", "type": kind, "movie_id": int(mid), **extra}]})
    assert r.status_code == 200


async def test_result_best_match_alternatives_and_saved(client):
    """F5/F7: итог считает сервер. Просмотренные и пропущенные не рекомендуются."""
    data = await start(client, limit=10, initial_genres=["Драма"])
    sid, cards = data["session_id"], data["cards"]
    await _react(client, sid, cards[0]["id"], "right", 1, opened_details=True, dwell_ms=7000)
    await _react(client, sid, cards[1]["id"], "left", 2)
    await _react(client, sid, cards[2]["id"], "up", 3, rating=5)
    r = (await client.get(f"/api/sessions/{sid}/result")).json()
    assert r["counts"] == {"saved": 1, "watched": 1, "skipped": 1}
    assert r["best"]["movie"]["id"] == cards[0]["id"] and r["best"]["saved"]
    assert 35 <= r["best"]["match"] <= 99 and 1 <= len(r["best"]["reasons"]) <= 2
    shown = {a["movie"]["id"] for a in r["alternatives"]} | {r["best"]["movie"]["id"]}
    assert len(r["alternatives"]) == 3
    assert cards[1]["id"] not in shown and cards[2]["id"] not in shown
    assert [m["movie"]["id"] for m in r["saved"]] == [cards[0]["id"]]
    assert r["saved"][0]["collection"]["in_watchlist"] is True


async def test_result_without_saved_still_recommends(client):
    data = await start(client, limit=10, initial_genres=["Комедия"])
    sid = data["session_id"]
    await _react(client, sid, data["cards"][0]["id"], "left", 1)
    r = (await client.get(f"/api/sessions/{sid}/result")).json()
    assert r["saved"] == [] and r["best"] and not r["best"]["saved"]
    assert "Комедия" in r["best"]["movie"]["genres"]


async def test_result_is_owner_only(client):
    data = await start(client)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as other:
        other.headers["Authorization"] = "Bearer " + (await other.post("/api/auth/anon")).json()["token"]
        assert (await other.get(f"/api/sessions/{data['session_id']}/result")).status_code == 404


async def test_session_detail_has_collection_state(client):
    data = await start(client)
    sid, mid = data["session_id"], data["cards"][0]["id"]
    await _react(client, sid, mid, "right", 1)
    d = (await client.get(f"/api/me/sessions/{sid}")).json()
    assert d["cards"][0]["collection"]["in_watchlist"] is True


async def test_token_expiry_legacy_and_sliding_refresh(client):
    uid = uuid.uuid4()
    assert parse_token_full(make_token(uid))[0] == uid
    assert parse_token_full(make_token(uid, now=time.time() - 400 * 86400)) is None      # истёк
    tampered = make_token(uid).replace(str(uid), str(uuid.uuid4()), 1)
    assert parse_token_full(tampered) is None
    # новый токен ещё «свежий» -> заголовка продления нет
    r = await client.get("/api/meta")
    assert r.status_code == 200 and "x-refreshed-token" not in r.headers
    # токен старше половины срока -> сервер присылает новый
    me = (await client.get("/api/auth/providers")).status_code
    tok = (await client.post("/api/auth/anon")).json()["token"]
    old_uid = tok.split(".")[0]
    aged = make_token(uuid.UUID(old_uid), now=time.time() - 120 * 86400)
    r = await client.get("/api/meta", headers={"Authorization": f"Bearer {aged}"})
    assert r.status_code == 200 and parse_token_full(r.headers["x-refreshed-token"])


def test_client_ip_uses_configured_proxy_depth(monkeypatch):
    from app.config import get_settings
    from app.routers.auth import _client_ip

    class Req:
        def __init__(self, xff): self.headers = {"x-forwarded-for": xff}; self.client = None

    s = get_settings()
    monkeypatch.setattr(s, "trusted_proxy_count", 2)
    assert _client_ip(Req("9.9.9.9, 1.1.1.1, 10.0.0.1")) == "1.1.1.1"
    monkeypatch.setattr(s, "trusted_proxy_count", 1)
    assert _client_ip(Req("9.9.9.9, 1.1.1.1")) == "1.1.1.1"
    monkeypatch.setattr(s, "trusted_proxy_count", 0)
    assert _client_ip(Req("9.9.9.9")) == "unknown"


def test_match_percent_is_spread_not_saturated():
    w = {"Драма": 6}
    hi = deck.match_percent(["Драма"], 8.0, w)
    lo = deck.match_percent(["Комедия"], 6.0, w)
    assert 35 <= lo < hi <= 98 and hi < 98


async def test_active_session_reports_real_plan(client):
    await _only_first(12)
    data = await start(client, limit=20)
    active = (await client.get("/api/sessions/active")).json()["session"]
    assert active["planned_total"] == 12 and active["exhausted"] is False
