from __future__ import annotations

import hashlib


def normalize_identity(value: str | None) -> str:
    return str(value or "").strip().lower()


def normalize_source(value: str | None) -> str:
    return str(value or "").strip().lower()


def build_identity_key(username: str | None, source: str | None) -> str:
    normalized_username = normalize_identity(username)
    normalized_source = normalize_source(source)
    if not normalized_username or not normalized_source:
        return ""
    raw = f"{normalized_username}|{normalized_source}".encode("utf-8")
    return hashlib.md5(raw).hexdigest()
