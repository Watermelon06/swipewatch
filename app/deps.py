from datetime import timedelta
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from .config import get_settings
from .db import get_db
from .models import User, utcnow
from .security import parse_token

Db = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(db: Db, authorization: str | None = Header(default=None)) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "missing token")
    user_id = parse_token(authorization[7:].strip())
    if not user_id:
        raise HTTPException(401, "invalid token")
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(401, "unknown user")
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
