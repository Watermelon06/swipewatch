"""Анонимная авторизация: сервер выдаёт подписанный токен 'user_id.exp.подпись' со сроком жизни.
Подделать чужой user_id без SECRET_KEY нельзя. Старые токены 'user_id.подпись' (без срока) принимаются
и при первом же запросе заменяются новыми (см. deps.get_current_user)."""
import hashlib
import hmac
import time
import uuid

from .config import get_settings


def _sig(msg: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, msg.encode(), hashlib.sha256).hexdigest()[:40]


def make_token(user_id: uuid.UUID, now: float | None = None) -> str:
    exp = int((now if now is not None else time.time()) + get_settings().token_ttl_days * 86400)
    msg = f"{user_id}.{exp}"
    return f"{msg}.{_sig(msg)}"


def parse_token_full(token: str, now: float | None = None) -> tuple[uuid.UUID, int | None] | None:
    """-> (user_id, exp) или None. exp=None для старого формата."""
    try:
        parts = token.split(".")
        if len(parts) == 2:                       # legacy: uuid.sig
            msg, sig = parts
            if not hmac.compare_digest(sig, _sig(msg)):
                return None
            return uuid.UUID(msg), None
        if len(parts) == 3:
            uid, exp, sig = parts
            if not hmac.compare_digest(sig, _sig(f"{uid}.{exp}")):
                return None
            if int(exp) < (now if now is not None else time.time()):
                return None
            return uuid.UUID(uid), int(exp)
    except (ValueError, AttributeError):
        return None
    return None


def parse_token(token: str) -> uuid.UUID | None:
    parsed = parse_token_full(token)
    return parsed[0] if parsed else None


def needs_refresh(exp: int | None, now: float | None = None) -> bool:
    """Скользящее продление: обновляем токен, когда прошла половина срока (или формат старый)."""
    if exp is None:
        return True
    return exp - (now if now is not None else time.time()) < get_settings().token_ttl_days * 86400 / 2
