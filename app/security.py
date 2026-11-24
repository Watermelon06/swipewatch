"""Анонимная авторизация: сервер выдаёт подписанный токен 'user_id.подпись'.
Подделать чужой user_id без SECRET_KEY нельзя."""
import hashlib
import hmac
import uuid

from .config import get_settings


def _sig(msg: str) -> str:
    key = get_settings().secret_key.encode()
    return hmac.new(key, msg.encode(), hashlib.sha256).hexdigest()[:40]


def make_token(user_id: uuid.UUID) -> str:
    msg = str(user_id)
    return f"{msg}.{_sig(msg)}"


def parse_token(token: str) -> uuid.UUID | None:
    try:
        msg, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(sig, _sig(msg)):
            return None
        return uuid.UUID(msg)
    except (ValueError, AttributeError):
        return None
