from __future__ import annotations

import httpx

_shared_async_client: httpx.AsyncClient | None = None


def get_shared_async_client() -> httpx.AsyncClient:
    global _shared_async_client
    if _shared_async_client is None:
        _shared_async_client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
    return _shared_async_client


async def close_shared_async_client() -> None:
    global _shared_async_client
    if _shared_async_client is not None:
        await _shared_async_client.aclose()
        _shared_async_client = None


__all__ = ["close_shared_async_client", "get_shared_async_client"]
