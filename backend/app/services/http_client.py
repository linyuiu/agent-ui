from __future__ import annotations

import httpx

from ..config import settings

_shared_async_client: httpx.AsyncClient | None = None


def get_shared_async_client() -> httpx.AsyncClient:
    global _shared_async_client
    if _shared_async_client is None:
        _shared_async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(float(max(1, settings.HTTP_CLIENT_TIMEOUT))),
            limits=httpx.Limits(
                max_connections=max(1, settings.HTTP_CLIENT_MAX_CONNECTIONS),
                max_keepalive_connections=max(1, settings.HTTP_CLIENT_MAX_KEEPALIVE_CONNECTIONS),
            ),
        )
    return _shared_async_client


async def close_shared_async_client() -> None:
    global _shared_async_client
    if _shared_async_client is not None:
        await _shared_async_client.aclose()
        _shared_async_client = None


__all__ = ["close_shared_async_client", "get_shared_async_client"]
