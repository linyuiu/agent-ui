from __future__ import annotations

import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session
from urllib.parse import parse_qsl, urlencode
from urllib.parse import urlparse

from .. import models
from ..db import get_db
from ..services.chat_links import build_proxy_chat_url, build_upstream_chat_url

router = APIRouter(tags=["chat_proxy"])
logger = logging.getLogger(__name__)

_PROXY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
_REQUEST_HEADER_BLOCKLIST = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
    "accept-encoding",
    "origin",
    "referer",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-forwarded-proto",
}
_RESPONSE_HEADER_BLOCKLIST = {
    "content-length",
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailer",
    "transfer-encoding",
    "upgrade",
}
_PROXY_ID_COOKIE = "chat_proxy_id"
_TOKEN_QUERY_KEYS = {"accesstoken", "acesstoken", "token"}
_TOKEN_JSON_KEYS = {"accesstoken", "acesstoken", "token"}


def _normalize_token_key(raw_key: str) -> str:
    return str(raw_key).replace("_", "").replace("-", "").lower()


def _proxy_request_headers(request: Request) -> dict[str, str]:
    headers: dict[str, str] = {}
    for key, value in request.headers.items():
        if key.lower() in _REQUEST_HEADER_BLOCKLIST:
            continue
        headers[key] = value
    # Keep payload deterministic and avoid compression/header mismatch on proxy responses.
    headers["accept-encoding"] = "identity"
    return headers


def _rewrite_location(location: str, agent: models.Agent) -> str:
    token = agent.upstream_token or ""
    proxy_id = agent.proxy_id or ""
    if not token or not proxy_id:
        return location

    upstream_root = build_upstream_chat_url(agent.upstream_base_url, token)
    proxy_root = build_proxy_chat_url(proxy_id)
    if location.startswith(upstream_root):
        return f"{proxy_root}{location[len(upstream_root):]}"

    upstream_rel_root = f"/chat/{token}"
    if location.startswith(upstream_rel_root):
        return f"/chat/{proxy_id}{location[len(upstream_rel_root):]}"

    return location


def _proxy_response_headers(headers: httpx.Headers, agent: models.Agent) -> dict[str, str]:
    forwarded: dict[str, str] = {}
    for key, value in headers.items():
        lower = key.lower()
        if lower in _RESPONSE_HEADER_BLOCKLIST:
            continue
        if lower == "location":
            forwarded[key] = _rewrite_location(value, agent)
            continue
        forwarded[key] = value
    return forwarded


def _agent_from_referer(db: Session, referer: str) -> models.Agent | None:
    if not referer:
        return None
    try:
        parsed = urlparse(referer)
    except Exception:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] != "chat":
        return None
    referer_proxy_id = parts[1]
    if not referer_proxy_id:
        return None
    return db.query(models.Agent).filter(models.Agent.proxy_id == referer_proxy_id).first()


def _agent_from_cookie(db: Session, request: Request) -> models.Agent | None:
    proxy_id = (request.cookies.get(_PROXY_ID_COOKIE) or "").strip()
    if not proxy_id:
        return None
    return db.query(models.Agent).filter(models.Agent.proxy_id == proxy_id).first()


def _agent_from_query(db: Session, query: str) -> models.Agent | None:
    if not query:
        return None
    params = parse_qsl(query, keep_blank_values=True)
    if not params:
        return None

    candidates: list[str] = []
    seen: set[str] = set()
    for _, value in params:
        candidate = (value or "").strip()
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)
    if not candidates:
        return None

    agents = db.query(models.Agent).filter(models.Agent.proxy_id.in_(candidates)).all()
    if not agents:
        return None

    by_proxy_id = {agent.proxy_id: agent for agent in agents}
    for candidate in candidates:
        if candidate in by_proxy_id:
            return by_proxy_id[candidate]
    return None


def _build_upstream_paths(agent: models.Agent, rest: str) -> list[str]:
    rest = rest.lstrip("/")
    if not rest:
        return [f"/chat/{agent.upstream_token}"]
    return [f"/chat/{rest}", f"/chat/{agent.upstream_token}/{rest}"]


def _is_chat_available(agent: models.Agent) -> bool:
    if not bool(getattr(agent, "is_synced", False)):
        return True
    return (agent.status or "").strip().lower() == "active"


def _resolve_proxy_target(
    db: Session, request: Request, request_path: str
) -> tuple[models.Agent, list[str]]:
    parts = [part for part in request_path.split("/") if part]
    if not parts:
        raise HTTPException(status_code=404, detail="Chat endpoint not found")

    first = parts[0]
    agent = db.query(models.Agent).filter(models.Agent.proxy_id == first).first()
    if agent:
        rest = "/".join(parts[1:])
        return agent, _build_upstream_paths(agent, rest)

    query_agent = _agent_from_query(db, request.url.query)
    if query_agent:
        rest = request_path.lstrip("/")
        return query_agent, _build_upstream_paths(query_agent, rest)

    referer_agent = _agent_from_referer(db, request.headers.get("referer", ""))
    if referer_agent:
        rest = request_path.lstrip("/")
        return referer_agent, _build_upstream_paths(referer_agent, rest)

    cookie_agent = _agent_from_cookie(db, request)
    if cookie_agent:
        rest = request_path.lstrip("/")
        return cookie_agent, _build_upstream_paths(cookie_agent, rest)

    raise HTTPException(status_code=404, detail="Chat endpoint not found")


def _rewrite_query_for_upstream(agent: models.Agent, query: str) -> str:
    if not query:
        return ""
    params = parse_qsl(query, keep_blank_values=True)
    if not params:
        return query

    rewritten = False
    next_params: list[tuple[str, str]] = []
    for key, value in params:
        normalized = _normalize_token_key(key)
        if normalized in _TOKEN_QUERY_KEYS:
            next_params.append((key, agent.upstream_token))
            rewritten = True
            continue
        if value == agent.proxy_id:
            next_params.append((key, agent.upstream_token))
            rewritten = True
            continue
        next_params.append((key, value))

    if not rewritten:
        return query
    return urlencode(next_params, doseq=True)


def _rewrite_json_tokens(value: object, *, proxy_id: str, upstream_token: str) -> object:
    if isinstance(value, dict):
        rewritten: dict[object, object] = {}
        for key, item in value.items():
            normalized = _normalize_token_key(str(key))
            if normalized in _TOKEN_JSON_KEYS and isinstance(item, str):
                rewritten[key] = upstream_token
                continue
            rewritten[key] = _rewrite_json_tokens(
                item,
                proxy_id=proxy_id,
                upstream_token=upstream_token,
            )
        return rewritten

    if isinstance(value, list):
        return [
            _rewrite_json_tokens(item, proxy_id=proxy_id, upstream_token=upstream_token)
            for item in value
        ]

    if isinstance(value, str) and value == proxy_id:
        return upstream_token

    return value


def _rewrite_payload_for_upstream(agent: models.Agent, request: Request, payload: bytes) -> bytes:
    if not payload:
        return payload

    content_type = (request.headers.get("content-type") or "").lower()

    if "application/json" in content_type:
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except Exception:
            return payload
        rewritten = _rewrite_json_tokens(
            parsed,
            proxy_id=agent.proxy_id,
            upstream_token=agent.upstream_token,
        )
        try:
            return json.dumps(rewritten, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        except Exception:
            return payload

    if "application/x-www-form-urlencoded" in content_type:
        try:
            text = payload.decode("utf-8")
            params = parse_qsl(text, keep_blank_values=True)
        except Exception:
            return payload
        next_params: list[tuple[str, str]] = []
        for key, value in params:
            normalized = _normalize_token_key(key)
            if normalized in _TOKEN_QUERY_KEYS or value == agent.proxy_id:
                next_params.append((key, agent.upstream_token))
            else:
                next_params.append((key, value))
        return urlencode(next_params, doseq=True).encode("utf-8")

    proxy_bytes = agent.proxy_id.encode("utf-8")
    if proxy_bytes in payload:
        return payload.replace(proxy_bytes, agent.upstream_token.encode("utf-8"))

    return payload


def _should_try_fallback_path(response: httpx.Response) -> bool:
    if response.status_code in {400, 401, 403, 404, 405}:
        return True

    content_type = (response.headers.get("content-type") or "").lower()
    if "application/json" not in content_type:
        return False

    try:
        body = response.json()
    except Exception:
        return False

    if not isinstance(body, dict):
        return False

    code = body.get("code")
    if code is None:
        return False

    code_text = str(code).strip()
    return code_text not in {"", "0", "200"}


@router.api_route("/chat/{request_path:path}", methods=_PROXY_METHODS)
async def proxy_chat(
    request_path: str,
    request: Request,
    db: Session = Depends(get_db),
) -> Response:
    agent, upstream_paths = _resolve_proxy_target(db, request, request_path)
    if not agent:
        raise HTTPException(status_code=404, detail="Chat endpoint not found")
    if not _is_chat_available(agent):
        raise HTTPException(status_code=403, detail="Agent is unavailable")
    if not agent.upstream_base_url or not agent.upstream_token:
        raise HTTPException(status_code=404, detail="Chat upstream is not configured")

    query_string = _rewrite_query_for_upstream(agent, request.url.query)
    payload = _rewrite_payload_for_upstream(agent, request, await request.body())
    headers = _proxy_request_headers(request)
    logger.info(
        "chat_proxy.request proxy_id=%s method=%s path=/chat/%s candidates=%s",
        agent.proxy_id,
        request.method,
        request_path,
        len(upstream_paths),
    )

    try:
        async with httpx.AsyncClient(follow_redirects=False, timeout=60.0) as client:
            upstream: httpx.Response | None = None
            for idx, upstream_path in enumerate(upstream_paths):
                upstream_url = f"{agent.upstream_base_url.rstrip('/')}{upstream_path}"
                if query_string:
                    upstream_url = f"{upstream_url}?{query_string}"
                candidate = await client.request(
                    request.method,
                    upstream_url,
                    headers=headers,
                    content=payload,
                )
                # Some upstream endpoints require /chat/{token}/..., others /chat/... .
                # Try fallback path before returning a 404.
                if _should_try_fallback_path(candidate) and idx + 1 < len(upstream_paths):
                    logger.info(
                        "chat_proxy.fallback proxy_id=%s method=%s path=/chat/%s attempt=%s status=%s",
                        agent.proxy_id,
                        request.method,
                        request_path,
                        idx + 1,
                        candidate.status_code,
                    )
                    continue
                upstream = candidate
                break
            if upstream is None:
                raise HTTPException(status_code=502, detail="Failed to proxy chat request")
    except httpx.HTTPError as exc:
        logger.exception(
            "chat_proxy.http_error proxy_id=%s method=%s path=/chat/%s",
            agent.proxy_id,
            request.method,
            request_path,
        )
        raise HTTPException(status_code=502, detail="Failed to proxy chat request") from exc

    response = Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_proxy_response_headers(upstream.headers, agent),
    )
    logger.info(
        "chat_proxy.response proxy_id=%s method=%s path=/chat/%s status=%s",
        agent.proxy_id,
        request.method,
        request_path,
        upstream.status_code,
    )
    response.set_cookie(
        key=_PROXY_ID_COOKIE,
        value=agent.proxy_id,
        path="/chat",
        samesite="lax",
    )
    return response
