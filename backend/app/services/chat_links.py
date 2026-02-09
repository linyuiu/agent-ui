from __future__ import annotations

import os
from urllib.parse import unquote, urlparse
from uuid import uuid4

SERVICE_PUBLIC_BASE_URL_ENV = "SERVICE_PUBLIC_BASE_URL"
DEFAULT_SERVICE_PUBLIC_BASE_URL = "http://localhost:5173"


def service_public_base_url() -> str:
    raw = (
        os.getenv("FRONTEND_PUBLIC_BASE_URL")
        or os.getenv("CHAT_PUBLIC_BASE_URL")
        or os.getenv(SERVICE_PUBLIC_BASE_URL_ENV)
        or os.getenv("PUBLIC_BASE_URL")
        or os.getenv("BACKEND_BASE_URL")
        or DEFAULT_SERVICE_PUBLIC_BASE_URL
    )
    return raw.rstrip("/")


def generate_proxy_id() -> str:
    return uuid4().hex


def build_proxy_chat_url(proxy_id: str) -> str:
    return f"{service_public_base_url()}/chat/{proxy_id}"


def build_upstream_chat_url(base_url: str, token: str, rest_path: str = "") -> str:
    base = base_url.rstrip("/")
    path = rest_path.lstrip("/")
    root = f"{base}/chat/{token}"
    if not path:
        return root
    return f"{root}/{path}"


def parse_upstream_chat_url(raw_url: str) -> tuple[str, str]:
    candidate = (raw_url or "").strip()
    if not candidate:
        raise ValueError("Agent URL is required")

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Agent URL must be an absolute http(s) URL")

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "chat":
        raise ValueError("Agent URL must use /chat/{token}")

    token = unquote(parts[1]).strip()
    if not token:
        raise ValueError("Agent URL token is empty")

    base_url = f"{parsed.scheme}://{parsed.netloc}"
    return base_url, token
