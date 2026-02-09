import os
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    base_dir = Path(__file__).resolve().parents[2]
    env_path = base_dir / ".env"
    load_dotenv(env_path)


_load_env()


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
