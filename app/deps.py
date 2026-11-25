from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import get_db
from .models import User, utcnow
from .security import make_token, needs_refresh, parse_token_full

Db = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(db: Db, response: Response,
                           authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing token")
    parsed = parse_token_full(authorization[7:].strip())
    if not parsed:
        raise HTTPException(401, "invalid token")
    user_id, exp = parsed
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(401, "unknown user")
    if needs_refresh(exp):                      # скользящий срок жизни: клиент подхватит заголовок
        response.headers["X-Refreshed-Token"] = make_token(user.id)
    last = user.last_seen if user.last_seen.tzinfo else user.last_seen.replace(tzinfo=utcnow().tzinfo)
    if utcnow() - last > timedelta(hours=1):  # не пишем в БД на каждый запрос
        user.last_seen = utcnow()
        await db.commit()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    token = get_settings().admin_token
    if not token:
        raise HTTPException(503, "ADMIN_TOKEN is not configured")
    if x_admin_token != token:
        raise HTTPException(403, "forbidden")
