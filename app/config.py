from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    secret_key: str
    kp_api_key: str = ""
    admin_token: str = ""
    auto_create_tables: bool = True
    anon_rate_limit_per_hour: int = 60   # гостевых аккаунтов с одного IP в час; 0 = без лимита (за NAT/оператором IP общий)
    trusted_proxy_count: int = 1         # сколько доверенных прокси перед приложением (для X-Forwarded-For); 0 = не доверять заголовку
    token_ttl_days: int = 180            # срок жизни токена; продлевается автоматически при активности
    vk_client_id: str = ""
    vk_redirect_uri: str = ""
    vk_service_token: str = ""  # требуется только для некоторых типов приложений VK ID

    # Логика колоды
    skip_cooldown_days: int = 30      # скипнутый фильм не показываем N дней
    explore_ratio: float = 0.2        # доля "неожиданных" карточек в порции
    temperature: float = 3.0          # ниже = жёстче следуем вкусу, выше = случайнее


@lru_cache
def get_settings() -> Settings:
    return Settings()


def normalize_db_url(url: str) -> tuple[str, dict]:
    """Neon отдаёт postgresql://...?sslmode=require&channel_binding=require.
    asyncpg таких параметров в URL не понимает, поэтому убираем query и передаём ssl отдельно."""
    parts = urlsplit(url)
    if parts.scheme in ("postgres", "postgresql", "postgresql+asyncpg"):
        clean = urlunsplit(("postgresql+asyncpg", parts.netloc, parts.path, "", ""))
        args = {
            "ssl": "require",            # Neon работает только по TLS
            "statement_cache_size": 0,   # нужно для pooled (pgbouncer) эндпоинта Neon
            "timeout": 20,               # холодный старт Neon может занять пару секунд
        }
        return clean, args
    return url, {}
