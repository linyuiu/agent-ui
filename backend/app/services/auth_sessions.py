from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from fastapi import HTTPException, Request, Response, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..config import settings
from ..models import User, UserLoginSession
from ..security import ALGORITHM, SECRET_KEY, create_access_token
from .redis_client import RedisError, get_redis_client

SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_EXPIRED = "expired"
SESSION_STATUS_LOGOUT = "logout"
SESSION_STATUS_REVOKED = "revoked"

SESSION_EXPIRES_HEADER = "X-Session-Expires-At"
AUTH_COOKIE_NAME = settings.AUTH_COOKIE_NAME


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _session_cache_key(session_id: str) -> str:
    return f"{settings.AUTH_SESSION_REDIS_PREFIX}:{session_id}"


def _idle_timeout() -> timedelta:
    minutes = max(1, int(settings.AUTH_SESSION_IDLE_TIMEOUT_MINUTES or 480))
    return timedelta(minutes=minutes)


def _touch_interval() -> timedelta:
    seconds = max(0, int(settings.AUTH_SESSION_TOUCH_INTERVAL_SECONDS or 0))
    return timedelta(seconds=seconds)


def _token_ttl() -> timedelta:
    idle_minutes = max(1, int(settings.AUTH_SESSION_IDLE_TIMEOUT_MINUTES or 480))
    ttl_minutes = max(idle_minutes, int(settings.AUTH_SESSION_TOKEN_TTL_MINUTES or idle_minutes))
    return timedelta(minutes=ttl_minutes)


def _cookie_max_age_seconds() -> int:
    return max(60, int(_idle_timeout().total_seconds()))


def _cookie_secure(request: Request | None) -> bool:
    if settings.AUTH_COOKIE_SECURE:
        return True
    return bool(request and request.url.scheme == "https")


def set_auth_cookie(response: Response, token: str, *, request: Request | None = None) -> None:
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=token,
        path="/",
        max_age=_cookie_max_age_seconds(),
        httponly=True,
        secure=_cookie_secure(request),
        samesite=settings.AUTH_COOKIE_SAMESITE,
        domain=settings.AUTH_COOKIE_DOMAIN,
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
        path="/",
        domain=settings.AUTH_COOKIE_DOMAIN,
    )


def _client_ip(request: Request | None) -> str:
    if request is None:
        return ""
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",", 1)[0].strip()
    if forwarded:
        return forwarded[:64]
    client = getattr(request, "client", None)
    return str(getattr(client, "host", "") or "")[:64]


def _user_agent(request: Request | None) -> str:
    if request is None:
        return ""
    return (request.headers.get("user-agent") or "")[:512]


def extract_bearer_token(request: Request) -> str:
    raw = (request.headers.get("authorization") or "").strip()
    if raw:
        parts = raw.split(None, 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    return ""


def extract_auth_token(request: Request) -> str:
    return extract_bearer_token(request) or str(request.cookies.get(AUTH_COOKIE_NAME) or "").strip()


def _session_payload(user: User, session: UserLoginSession) -> dict[str, Any]:
    return {
        "sub": str(user.id),
        "sid": session.id,
        "email": user.email,
        "username": user.username,
        "account": user.account,
        "source": user.source,
        "source_provider": user.source_provider,
    }


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="访问需要登录",
    )


def decode_session_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise _credentials_exception() from exc


def _token_identity(payload: dict[str, Any]) -> tuple[int, str]:
    user_id = payload.get("sub")
    session_id = str(payload.get("sid") or "").strip()
    if not user_id or not session_id:
        raise _credentials_exception()
    try:
        return int(user_id), session_id
    except (TypeError, ValueError) as exc:
        raise _credentials_exception() from exc


async def create_login_session(
    db: AsyncSession,
    *,
    user: User,
    request: Request | None,
    login_method: str,
) -> tuple[str, UserLoginSession]:
    now = _now()
    session = UserLoginSession(
        id=uuid4().hex,
        user_id=user.id,
        status=SESSION_STATUS_ACTIVE,
        login_method=(login_method or "local")[:64],
        ip_address=_client_ip(request),
        user_agent=_user_agent(request),
        issued_at=now,
        last_seen_at=now,
        expires_at=now + _idle_timeout(),
        created_at=now,
    )
    db.add(session)
    await db.flush()

    token = create_access_token(_session_payload(user, session), expires_delta=_token_ttl())
    session.token_hash = _token_hash(token)
    await db.flush()
    return token, session


def _session_expired(session: UserLoginSession, *, now: datetime) -> bool:
    return _as_aware(session.expires_at) <= now


def _should_touch(session: UserLoginSession, *, now: datetime) -> bool:
    interval = _touch_interval()
    if interval.total_seconds() <= 0:
        return True
    return _as_aware(session.last_seen_at) + interval <= now


def _set_session_headers(response: Response | None, session: UserLoginSession) -> None:
    if response is None:
        return
    response.headers[SESSION_EXPIRES_HEADER] = _as_aware(session.expires_at).isoformat()


def _set_response_expiry_header(response: Response | None, expires_at: datetime) -> None:
    if response is None:
        return
    response.headers[SESSION_EXPIRES_HEADER] = _as_aware(expires_at).isoformat()


def _set_request_session_state(request: Request | None, session: UserLoginSession) -> None:
    if request is None:
        return
    request.state.session_expires_at = _as_aware(session.expires_at).isoformat()


def _set_request_session_expiry(request: Request | None, expires_at: datetime) -> None:
    if request is None:
        return
    request.state.session_expires_at = _as_aware(expires_at).isoformat()


def _seconds_until(value: datetime, *, now: datetime | None = None) -> int:
    current = now or _now()
    return max(1, int((_as_aware(value) - current).total_seconds()))


def _serialize_user(user: User) -> dict[str, Any]:
    return {
        "id": user.id,
        "account": user.account,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "status": user.status,
        "source": user.source,
        "source_provider": user.source_provider,
        "source_subject": user.source_subject,
        "workspace": user.workspace,
        "created_at": _as_aware(user.created_at).isoformat() if user.created_at else None,
    }


def _user_from_cache(payload: dict[str, Any]) -> User:
    created_at = payload.get("created_at")
    return User(
        id=int(payload.get("id") or 0),
        account=str(payload.get("account") or ""),
        username=str(payload.get("username") or ""),
        email=str(payload.get("email") or ""),
        role=str(payload.get("role") or "user"),
        status=str(payload.get("status") or "active"),
        source=str(payload.get("source") or "local"),
        source_provider=str(payload.get("source_provider") or "local"),
        source_subject=str(payload.get("source_subject") or ""),
        workspace=str(payload.get("workspace") or "default"),
        created_at=datetime.fromisoformat(created_at) if created_at else _now(),
    )


def _session_cache_payload(
    *,
    user: User,
    session: UserLoginSession,
    now: datetime,
) -> dict[str, Any]:
    return {
        "session_id": session.id,
        "user_id": user.id,
        "status": session.status,
        "expires_at": _as_aware(session.expires_at).isoformat(),
        "last_seen_at": _as_aware(session.last_seen_at).isoformat(),
        "db_checked_at": now.isoformat(),
        "user": _serialize_user(user),
    }


async def cache_login_session(user: User, session: UserLoginSession) -> None:
    client = get_redis_client()
    if client is None:
        return
    now = _now()
    try:
        await client.set(
            _session_cache_key(session.id),
            json.dumps(_session_cache_payload(user=user, session=session, now=now), separators=(",", ":")),
            ex=_seconds_until(session.expires_at, now=now),
        )
    except RedisError:
        return


async def _delete_cached_session(session_id: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        await client.delete(_session_cache_key(session_id))
    except RedisError:
        return


async def _load_cached_session(session_id: str) -> dict[str, Any] | None:
    client = get_redis_client()
    if client is None:
        return None
    try:
        raw = await client.get(_session_cache_key(session_id))
    except RedisError:
        return None
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        await _delete_cached_session(session_id)
        return None
    if not isinstance(payload, dict):
        return None
    return payload


async def _store_cached_payload(session_id: str, payload: dict[str, Any], expires_at: datetime) -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        await client.set(
            _session_cache_key(session_id),
            json.dumps(payload, separators=(",", ":")),
            ex=_seconds_until(expires_at),
        )
    except RedisError:
        return


async def validate_session_token(
    token: str,
    db: AsyncSession,
    *,
    request: Request | None = None,
    response: Response | None = None,
) -> User:
    payload = decode_session_token(token)
    user_id, session_id = _token_identity(payload)
    now = _now()

    cached = await _load_cached_session(session_id)
    if cached and int(cached.get("user_id") or 0) == user_id:
        try:
            cached_expires_at = datetime.fromisoformat(str(cached.get("expires_at") or ""))
            cached_db_checked_at = datetime.fromisoformat(str(cached.get("db_checked_at") or ""))
        except ValueError:
            await _delete_cached_session(session_id)
        else:
            user_payload = cached.get("user") if isinstance(cached.get("user"), dict) else {}
            user = _user_from_cache(user_payload)
            if cached.get("status") != SESSION_STATUS_ACTIVE or user.status != "active":
                await _delete_cached_session(session_id)
                raise _credentials_exception()
            if _as_aware(cached_expires_at) <= now:
                await _delete_cached_session(session_id)
                raise _credentials_exception()

            db_touch_due = _as_aware(cached_db_checked_at) + _touch_interval() <= now
            new_expires_at = now + _idle_timeout()
            cached["expires_at"] = new_expires_at.isoformat()
            cached["last_seen_at"] = now.isoformat()

            if db_touch_due:
                row = (
                    await db.execute(
                        select(User, UserLoginSession)
                        .join(UserLoginSession, UserLoginSession.user_id == User.id)
                        .where(User.id == user_id, UserLoginSession.id == session_id)
                    )
                ).one_or_none()
                if row is None:
                    await _delete_cached_session(session_id)
                    raise _credentials_exception()
                db_user, session = row
                if session.status != SESSION_STATUS_ACTIVE:
                    await _delete_cached_session(session_id)
                    raise _credentials_exception()
                if _session_expired(session, now=now):
                    session.status = SESSION_STATUS_EXPIRED
                    session.ended_at = now
                    await db.commit()
                    await _delete_cached_session(session_id)
                    raise _credentials_exception()
                if db_user.status != "active":
                    session.status = SESSION_STATUS_REVOKED
                    session.ended_at = now
                    await db.commit()
                    await _delete_cached_session(session_id)
                    raise _credentials_exception()

                session.last_seen_at = now
                session.expires_at = new_expires_at
                session.ip_address = _client_ip(request) or session.ip_address
                session.user_agent = _user_agent(request) or session.user_agent
                await db.commit()
                user = db_user
                cached = _session_cache_payload(user=db_user, session=session, now=now)
            else:
                await _store_cached_payload(session_id, cached, new_expires_at)
            if db_touch_due:
                await _store_cached_payload(session_id, cached, new_expires_at)

            _set_request_session_expiry(request, new_expires_at)
            _set_response_expiry_header(response, new_expires_at)
            if response is not None:
                set_auth_cookie(response, token, request=request)
            return user

    row = (
        await db.execute(
            select(User, UserLoginSession)
            .join(UserLoginSession, UserLoginSession.user_id == User.id)
            .where(User.id == user_id, UserLoginSession.id == session_id)
        )
    ).one_or_none()
    if row is None:
        raise _credentials_exception()

    user, session = row
    if session.status != SESSION_STATUS_ACTIVE:
        raise _credentials_exception()
    if _session_expired(session, now=now):
        session.status = SESSION_STATUS_EXPIRED
        session.ended_at = now
        await db.commit()
        raise _credentials_exception()
    if user.status != "active":
        session.status = SESSION_STATUS_REVOKED
        session.ended_at = now
        await db.commit()
        raise _credentials_exception()

    if _should_touch(session, now=now):
        session.last_seen_at = now
        session.expires_at = now + _idle_timeout()
        session.ip_address = _client_ip(request) or session.ip_address
        session.user_agent = _user_agent(request) or session.user_agent
        await db.commit()

    await cache_login_session(user, session)
    _set_request_session_state(request, session)
    _set_session_headers(response, session)
    if response is not None:
        set_auth_cookie(response, token, request=request)
    return user


def validate_session_token_sync(token: str, db: Session) -> User:
    payload = decode_session_token(token)
    user_id, session_id = _token_identity(payload)

    row = (
        db.query(User, UserLoginSession)
        .join(UserLoginSession, UserLoginSession.user_id == User.id)
        .filter(User.id == user_id, UserLoginSession.id == session_id)
        .first()
    )
    if row is None:
        raise _credentials_exception()

    user, session = row
    now = _now()
    if session.status != SESSION_STATUS_ACTIVE:
        raise _credentials_exception()
    if _session_expired(session, now=now):
        session.status = SESSION_STATUS_EXPIRED
        session.ended_at = now
        db.commit()
        raise _credentials_exception()
    if user.status != "active":
        session.status = SESSION_STATUS_REVOKED
        session.ended_at = now
        db.commit()
        raise _credentials_exception()

    if _should_touch(session, now=now):
        session.last_seen_at = now
        session.expires_at = now + _idle_timeout()
        db.commit()
    return user


async def end_session_for_token(
    db: AsyncSession,
    token: str,
    *,
    status_value: str = SESSION_STATUS_LOGOUT,
) -> None:
    payload = decode_session_token(token)
    _user_id, session_id = _token_identity(payload)
    session = await db.get(UserLoginSession, session_id)
    if session is None:
        return
    if session.status == SESSION_STATUS_ACTIVE:
        session.status = status_value
        session.ended_at = _now()
        await db.flush()
    await _delete_cached_session(session_id)
