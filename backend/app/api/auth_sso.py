from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, security
from ..auth import get_current_user
from ..db import get_db
from ..services.sso import (
    PASSWORD_PROTOCOLS,
    REDIRECT_PROTOCOLS,
    SsoBindRequiredError,
    authenticate_password_provider,
    authenticate_redirect_provider,
    bind_sso_identity_async,
    build_frontend_bind_redirect,
    build_frontend_redirect,
    build_provider_public,
    build_redirect_login_url,
    build_user_public_async,
    identity_from_profile,
    normalize_protocol,
    parse_state_token,
    upsert_sso_user_async,
)

router = APIRouter(prefix="/auth/sso", tags=["auth_sso"])


async def _issue_login_response(db: AsyncSession, user: models.User) -> schemas.LoginResponse:
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该用户被禁用，无法登陆",
        )
    token = security.create_access_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "username": user.username,
            "account": user.account,
            "source": user.source,
            "source_provider": user.source_provider,
        }
    )
    return schemas.LoginResponse(
        access_token=token,
        token_type="bearer",
        user=await build_user_public_async(db, user),
    )


@router.get("/providers", response_model=list[schemas.SsoProviderPublic])
async def list_enabled_sso_providers(db: AsyncSession = Depends(get_db)) -> list[schemas.SsoProviderPublic]:
    providers = (
        await db.execute(
            select(models.AuthProviderConfig)
            .where(models.AuthProviderConfig.enabled.is_(True))
            .order_by(models.AuthProviderConfig.id.asc())
        )
    ).scalars().all()
    return [build_provider_public(provider) for provider in providers]


@router.post("/password-login", response_model=schemas.LoginResponse)
async def sso_password_login(
    payload: schemas.SsoPasswordLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    provider = (
        await db.execute(
            select(models.AuthProviderConfig).where(
                models.AuthProviderConfig.key == payload.provider_key,
                models.AuthProviderConfig.enabled.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not provider:
        return JSONResponse(status_code=404, content={"detail": "单点登录配置不存在或未启用"})
    if normalize_protocol(provider.protocol) not in PASSWORD_PROTOCOLS:
        return JSONResponse(status_code=400, content={"detail": "该单点协议不支持账号密码登录"})

    profile = await authenticate_password_provider(provider, payload.account, payload.password)
    identity = identity_from_profile(provider, profile)
    try:
        user = await upsert_sso_user_async(db, provider, identity)
    except SsoBindRequiredError as exc:
        await db.rollback()
        return JSONResponse(status_code=409, content=exc.to_schema().model_dump())
    await db.commit()
    await db.refresh(user)
    login_response = await _issue_login_response(db, user)
    return login_response


@router.get("/start/{provider_key}")
async def start_sso_login(
    provider_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    provider = (
        await db.execute(
            select(models.AuthProviderConfig).where(
                models.AuthProviderConfig.key == provider_key,
                models.AuthProviderConfig.enabled.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not provider:
        return RedirectResponse(url=build_frontend_bind_redirect(
            bind_token="",
            target_path="/home/agents",
            message="单点登录配置不存在或未启用",
            provider_name=provider_key,
        ), status_code=307)
    if normalize_protocol(provider.protocol) not in REDIRECT_PROTOCOLS:
        return RedirectResponse(url=build_frontend_bind_redirect(
            bind_token="",
            target_path="/home/agents",
            message="该单点协议不支持跳转登录",
            provider_name=provider.name,
        ), status_code=307)

    redirect = str(request.query_params.get("redirect") or "/home/agents")
    if not redirect.startswith("/"):
        redirect = "/home/agents"
    url = await build_redirect_login_url(provider, redirect=redirect)
    return RedirectResponse(url=url, status_code=307)


@router.api_route("/callback/{provider_key}", methods=["GET", "POST"])
async def sso_login_callback(
    provider_key: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    provider = (
        await db.execute(
            select(models.AuthProviderConfig).where(
                models.AuthProviderConfig.key == provider_key,
                models.AuthProviderConfig.enabled.is_(True),
            )
        )
    ).scalar_one_or_none()
    if not provider:
        return RedirectResponse(
            url=build_frontend_bind_redirect(
                bind_token="",
                target_path="/home/agents",
                message="单点登录配置不存在或未启用",
                provider_name=provider_key,
            ),
            status_code=307,
        )
    if normalize_protocol(provider.protocol) not in REDIRECT_PROTOCOLS:
        return RedirectResponse(
            url=build_frontend_bind_redirect(
                bind_token="",
                target_path="/home/agents",
                message="该单点协议不支持回调",
                provider_name=provider.name,
            ),
            status_code=307,
        )

    query_params = {key: value for key, value in request.query_params.items()}
    body_params: dict[str, str] = {}
    if request.method.upper() == "POST":
        raw = await request.body()
        if raw:
            body_params = {key: value for key, value in parse_qsl(raw.decode("utf-8"), keep_blank_values=True)}
            if "state" not in query_params and "RelayState" in body_params:
                query_params["state"] = body_params["RelayState"]

    profile = await authenticate_redirect_provider(provider, query_params=query_params, body_params=body_params)
    state = str(query_params.get("state") or "").strip()
    target = parse_state_token(state, provider.key)
    identity = identity_from_profile(provider, profile)
    try:
        user = await upsert_sso_user_async(db, provider, identity, redirect=target)
    except SsoBindRequiredError as exc:
        await db.rollback()
        redirect_url = build_frontend_bind_redirect(
            bind_token=exc.bind_token,
            target_path=target,
            message=exc.message,
            provider_name=exc.provider_name,
        )
        return RedirectResponse(url=redirect_url, status_code=307)
    await db.commit()
    await db.refresh(user)
    login_payload = await _issue_login_response(db, user)
    redirect_url = build_frontend_redirect(login_payload.access_token, target)
    return RedirectResponse(url=redirect_url, status_code=307)


@router.post("/bind")
async def bind_sso_identity(
    payload: schemas.SsoBindRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    binding = await bind_sso_identity_async(db, current_user=current_user, bind_token=payload.bind_token)
    await db.commit()
    return {
        "status": "ok",
        "provider_key": binding.provider_key,
        "provider_protocol": binding.provider_protocol,
    }
