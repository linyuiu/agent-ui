import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    base_dir = Path(__file__).resolve().parents[2]
    env_path = base_dir / ".env"
    load_dotenv(env_path)


def _as_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _as_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_csv(name: str, default: str) -> list[str]:
    value = os.getenv(name, default)
    return [item.strip() for item in value.split(",") if item.strip()]


_load_env()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5432/agent_ui",
)
DB_POOL_SIZE = _as_int("DB_POOL_SIZE", 50)
DB_MAX_OVERFLOW = _as_int("DB_MAX_OVERFLOW", 100)
DB_POOL_TIMEOUT = _as_int("DB_POOL_TIMEOUT", 30)
DB_POOL_RECYCLE = _as_int("DB_POOL_RECYCLE", 1800)
DB_POOL_PRE_PING = _as_bool("DB_POOL_PRE_PING", True)
DB_ECHO = _as_bool("DB_ECHO", False)
DB_SEED_ON_STARTUP = _as_bool("DB_SEED_ON_STARTUP", True)

APP_HOST = os.getenv("APP_HOST", "localhost")
APP_PORT = _as_int("APP_PORT", 8000)
APP_RELOAD = _as_bool("APP_RELOAD", True)
CORS_ORIGINS = _as_csv("CORS_ORIGINS", "http://localhost:5173")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"http://{APP_HOST}:{APP_PORT}")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

JWT_SECRET = os.getenv("JWT_SECRET") or ""
ACCESS_TOKEN_EXPIRE_MINUTES = _as_int("ACCESS_TOKEN_EXPIRE_MINUTES", 480)
AUTH_SESSION_IDLE_TIMEOUT_MINUTES = _as_int("AUTH_SESSION_IDLE_TIMEOUT_MINUTES", 480)
AUTH_SESSION_TOUCH_INTERVAL_SECONDS = _as_int("AUTH_SESSION_TOUCH_INTERVAL_SECONDS", 60)
AUTH_SESSION_TOKEN_TTL_MINUTES = _as_int("AUTH_SESSION_TOKEN_TTL_MINUTES", 43200)
AUTH_SESSION_REDIS_ENABLED = _as_bool("AUTH_SESSION_REDIS_ENABLED", True)
AUTH_SESSION_REDIS_PREFIX = os.getenv("AUTH_SESSION_REDIS_PREFIX", "agent_ui:auth_session")
AUTH_COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "agent_ui_session")
AUTH_COOKIE_DOMAIN = os.getenv("AUTH_COOKIE_DOMAIN") or None
AUTH_COOKIE_SAMESITE = os.getenv("AUTH_COOKIE_SAMESITE", "lax")
AUTH_COOKIE_SECURE = _as_bool("AUTH_COOKIE_SECURE", False)

HTTP_CLIENT_TIMEOUT = _as_int("HTTP_CLIENT_TIMEOUT", 60)
HTTP_CLIENT_MAX_CONNECTIONS = _as_int("HTTP_CLIENT_MAX_CONNECTIONS", 500)
HTTP_CLIENT_MAX_KEEPALIVE_CONNECTIONS = _as_int("HTTP_CLIENT_MAX_KEEPALIVE_CONNECTIONS", 100)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
