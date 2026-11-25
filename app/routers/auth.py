"""Guest auth and optional VK ID OAuth 2.1 (Authorization Code + PKCE)."""
import base64
import hashlib
import secrets
import time
from collections import defaultdict, deque
from datetime import timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select, update

from ..config import get_settings
from ..deps import CurrentUser, Db
from ..models import (AuthExchangeCode, GameSession, Swipe, User, UserIdentity,
                      UserMovieCollection, UserMovieState, UserProfile, VkOAuthAttempt, utcnow)
from ..security import make_token

router = APIRouter(prefix="/auth", tags=["auth"])
VK_AUTHORIZE_URL = "https://id.vk.ru/authorize"
VK_TOKEN_URL = "https://id.vk.ru/oauth2/auth"
VK_USER_INFO_URL = "https://id.vk.ru/oauth2/user_info"


_anon_hits: dict[str, deque] = defaultdict(deque)   # in-memory, на процесс


def _client_ip(request: Request) -> str:
    """IP клиента. За N доверенными прокси реальный адрес — N-й с конца в X-Forwarded-For
    (всё левее может подделать клиент). N = TRUSTED_PROXY_COUNT; 0 = заголовок игнорируем."""
    n = get_settings().trusted_proxy_count
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and n > 0:
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        if parts:
            return parts[-n] if len(parts) >= n else parts[0]
    return request.client.host if request.client else "unknown"


def check_anon_rate(ip: str, limit: int, window: int = 3600) -> None:
    if limit <= 0:
        return
    now = time.monotonic()
    hits = _anon_hits[ip]
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= limit:
        raise HTTPException(429, "Слишком много новых гостевых аккаунтов. Попробуйте позже.")
    hits.append(now)
    if len(_anon_hits) > 10_000:        # не даём словарю расти бесконечно
        for key in [k for k, v in _anon_hits.items() if not v or now - v[-1] > window]:
            _anon_hits.pop(key, None)


@router.post("/anon")
async def anon(request: Request, db: Db):
    check_anon_rate(_client_ip(request), get_settings().anon_rate_limit_per_hour)
    user = User()
    db.add(user)
    await db.commit()
    return {"token": make_token(user.id), "user_id": str(user.id), "is_guest": True}


@router.get("/providers")
async def providers():
    settings = get_settings()
    return {"vk": bool(settings.vk_client_id and settings.vk_redirect_uri)}


def _as_utc(value):
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def _merge_user_data(db, source_id, target_id):
    """Merge an anonymous profile into the account already linked to a VK identity."""
    if source_id == target_id:
        return
    source_states = (await db.execute(select(UserMovieState).where(
        UserMovieState.user_id == source_id
    ))).scalars().all()
    for source in source_states:
        target = await db.get(UserMovieState, (target_id, source.movie_id))
        if not target:
            source.user_id = target_id
        elif (source.updated_at or utcnow()) > (target.updated_at or utcnow()):
            target.state, target.rating, target.updated_at = source.state, source.rating, source.updated_at
            await db.delete(source)
        else:
            await db.delete(source)

    source_items = (await db.execute(select(UserMovieCollection).where(
        UserMovieCollection.user_id == source_id
    ))).scalars().all()
    for source in source_items:
        target = await db.get(UserMovieCollection, (target_id, source.movie_id))
        if not target:
            source.user_id = target_id
            continue
        target.is_favorite = target.is_favorite or source.is_favorite
        target.in_watchlist = target.in_watchlist or source.in_watchlist
        target.watched = target.watched or source.watched
        target.skipped = target.skipped or source.skipped
        if (source.updated_at or utcnow()) > (target.updated_at or utcnow()):
            target.rating, target.note = source.rating, source.note
            target.watched_at, target.updated_at = source.watched_at, source.updated_at
        await db.delete(source)

    await db.execute(update(GameSession).where(GameSession.user_id == source_id).values(user_id=target_id))
    await db.execute(update(Swipe).where(Swipe.user_id == source_id).values(user_id=target_id))
    source_profile = await db.get(UserProfile, source_id)
    target_profile = await db.get(UserProfile, target_id)
    if source_profile and not target_profile:
        source_profile.user_id = target_id
    elif source_profile:
        if target_profile.display_name == "Киноман" and source_profile.display_name != "Киноман":
            target_profile.display_name = source_profile.display_name
        await db.delete(source_profile)
    await db.execute(update(UserIdentity).where(UserIdentity.user_id == source_id).values(user_id=target_id))
    source_user = await db.get(User, source_id)
    if source_user:
        await db.delete(source_user)


@router.get("/vk/start")
async def vk_start(db: Db, user: CurrentUser):
    settings = get_settings()
    if not settings.vk_client_id or not settings.vk_redirect_uri:
        raise HTTPException(503, "VK ID is not configured. Set VK_CLIENT_ID and VK_REDIRECT_URI.")
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    db.add(VkOAuthAttempt(state=state, code_verifier=verifier, anon_user_id=user.id,
                          expires_at=utcnow() + timedelta(minutes=10)))
    await db.commit()
    params = {
        "response_type": "code", "client_id": settings.vk_client_id,
        "redirect_uri": settings.vk_redirect_uri, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "scope": "vkid.personal_info", "lang_id": "ru",
    }
    return {"authorization_url": VK_AUTHORIZE_URL + "?" + urlencode(params)}


@router.get("/vk/callback")
async def vk_callback(db: Db, code: str | None = None, state: str | None = None,
                      device_id: str | None = None, error: str | None = None):
    if error:
        return RedirectResponse(url="/?vk_error=denied", status_code=302)
    if not code or not state or not device_id:
        return RedirectResponse(url="/?vk_error=invalid_callback", status_code=302)
    attempt = await db.get(VkOAuthAttempt, state)
    if not attempt or _as_utc(attempt.expires_at) < utcnow():
        if attempt:
            await db.delete(attempt)
            await db.commit()
        return RedirectResponse(url="/?vk_error=expired", status_code=302)

    settings = get_settings()
    token_params = {
        "grant_type": "authorization_code", "redirect_uri": settings.vk_redirect_uri,
        "client_id": settings.vk_client_id, "code_verifier": attempt.code_verifier,
        "device_id": device_id, "state": state,
    }
    if settings.vk_service_token:
        token_params["service_token"] = settings.vk_service_token
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(VK_TOKEN_URL, params=token_params, data={"code": code})
            token_response.raise_for_status()
            token_data = token_response.json()
            if token_data.get("state") and token_data["state"] != state:
                raise ValueError("VK state mismatch")
            access_token = token_data.get("access_token")
            if not access_token:
                raise ValueError("VK did not return an access token")
            info_response = await client.post(VK_USER_INFO_URL,
                                              params={"client_id": settings.vk_client_id},
                                              data={"access_token": access_token})
            info_response.raise_for_status()
            info_data = info_response.json()
    except (httpx.HTTPError, ValueError, KeyError):
        await db.delete(attempt)
        await db.commit()
        return RedirectResponse(url="/?vk_error=provider_error", status_code=302)

    profile = info_data.get("user") or info_data
    subject = str(profile.get("user_id") or profile.get("id") or token_data.get("user_id") or "")
    if not subject:
        await db.delete(attempt)
        await db.commit()
        return RedirectResponse(url="/?vk_error=profile_error", status_code=302)
    anon_user_id = attempt.anon_user_id
    await db.delete(attempt)
    await db.flush()
    identity = (await db.execute(select(UserIdentity).where(
        UserIdentity.provider == "vk", UserIdentity.subject == subject
    ))).scalar_one_or_none()
    if identity:
        target_user_id = identity.user_id
        await _merge_user_data(db, anon_user_id, target_user_id)
    else:
        target_user_id = anon_user_id
        db.add(UserIdentity(user_id=target_user_id, provider="vk", subject=subject))

    first_name = str(profile.get("first_name") or "").strip()
    last_name = str(profile.get("last_name") or "").strip()
    display_name = (first_name + " " + last_name).strip() or "Пользователь VK"
    user_profile = await db.get(UserProfile, target_user_id)
    if not user_profile:
        user_profile = UserProfile(user_id=target_user_id, display_name=display_name,
                                   avatar_url=profile.get("avatar"), preferences={})
        db.add(user_profile)
    else:
        user_profile.display_name = display_name
        user_profile.avatar_url = profile.get("avatar") or user_profile.avatar_url
        user_profile.updated_at = utcnow()

    exchange_code = secrets.token_urlsafe(36)
    db.add(AuthExchangeCode(code=exchange_code, user_id=target_user_id,
                            expires_at=utcnow() + timedelta(seconds=90)))
    await db.commit()
    return RedirectResponse(url=f"/?vk_code={exchange_code}", status_code=302)


@router.post("/exchange")
async def exchange_code(db: Db, code: str = Query(..., min_length=20, max_length=128)):
    row = await db.get(AuthExchangeCode, code)
    if not row or _as_utc(row.expires_at) < utcnow():
        if row:
            await db.delete(row)
            await db.commit()
        raise HTTPException(400, "login code expired or already used")
    user = await db.get(User, row.user_id)
    if not user:
        await db.delete(row)
        await db.commit()
        raise HTTPException(400, "account not found")
    token = make_token(user.id)
    await db.delete(row)
    await db.commit()
    return {"token": token, "user_id": str(user.id), "is_guest": False}
