from __future__ import annotations

import logging
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)

try:  # pragma: no cover - import availability depends on deployment extras
    import redis.asyncio as redis
    from redis.exceptions import RedisError
except Exception:  # pragma: no cover
    redis = None

    class RedisError(Exception):
        pass


_redis_client: Any | None = None


def get_redis_client() -> Any | None:
    global _redis_client
    if not settings.AUTH_SESSION_REDIS_ENABLED or not settings.REDIS_URL or redis is None:
        return None
    if _redis_client is None:
        _redis_client = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=1.0,
            socket_timeout=1.0,
            health_check_interval=30,
        )
    return _redis_client


async def close_redis_client() -> None:
    global _redis_client
    if _redis_client is None:
        return
    try:
        await _redis_client.aclose()
    except Exception:
        logger.exception("failed to close redis client")
    finally:
        _redis_client = None


__all__ = ["RedisError", "close_redis_client", "get_redis_client"]
