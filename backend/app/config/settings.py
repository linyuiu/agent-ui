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
DB_POOL_SIZE = _as_int("DB_POOL_SIZE", 20)
DB_MAX_OVERFLOW = _as_int("DB_MAX_OVERFLOW", 30)
DB_POOL_TIMEOUT = _as_int("DB_POOL_TIMEOUT", 30)
DB_POOL_RECYCLE = _as_int("DB_POOL_RECYCLE", 1800)
DB_POOL_PRE_PING = _as_bool("DB_POOL_PRE_PING", True)
DB_ECHO = _as_bool("DB_ECHO", False)

APP_HOST = os.getenv("APP_HOST", "127.0.0.1")
APP_PORT = _as_int("APP_PORT", 8000)
APP_RELOAD = _as_bool("APP_RELOAD", True)
CORS_ORIGINS = _as_csv("CORS_ORIGINS", "http://localhost:5173")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", f"http://{APP_HOST}:{APP_PORT}")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")

JWT_SECRET = os.getenv("JWT_SECRET") or ""
ACCESS_TOKEN_EXPIRE_MINUTES = _as_int("ACCESS_TOKEN_EXPIRE_MINUTES", 480)
