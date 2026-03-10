from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
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
    build_login_options_out,
    build_provider_public,
    build_redirect_login_url,
    build_user_public_async,
    get_provider_bundle_async,
    identity_from_profile,
    list_enabled_provider_bundles_async,
    normalize_protocol,
    parse_state_token,
    upsert_sso_user_async,
)
from ..permissions import summarize_permissions_async
from .auth import _resolve_login_credentials

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
    permissions = schemas.PermissionSummary(**(await summarize_permissions_async(db, user)))
    return schemas.LoginResponse(
        access_token=token,
        token_type="bearer",
        user=await build_user_public_async(db, user),
        permissions=permissions,
    )


@router.get("/providers", response_model=list[schemas.SsoProviderPublic])
async def list_enabled_sso_providers(db: AsyncSession = Depends(get_db)) -> list[schemas.SsoProviderPublic]:
    bundles, _setting = await list_enabled_provider_bundles_async(db)
    return [build_provider_public(provider) for provider, _setting in bundles]


@router.get("/options", response_model=schemas.SsoLoginOptions)
async def get_sso_login_options(db: AsyncSession = Depends(get_db)) -> schemas.SsoLoginOptions:
    bundles, setting = await list_enabled_provider_bundles_async(db)
    providers = [build_provider_public(provider) for provider, _item in bundles]
    return build_login_options_out(setting, providers)


@router.post("/password-login", response_model=schemas.LoginResponse)
async def sso_password_login(
    payload: schemas.SsoPasswordLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    provider, setting = await get_provider_bundle_async(db, payload.provider_key, enabled_only=True)
    if not provider:
        return JSONResponse(status_code=404, content={"detail": "单点登录配置不存在或未启用"})
    if normalize_protocol(provider.protocol) not in PASSWORD_PROTOCOLS:
        return JSONResponse(status_code=400, content={"detail": "该单点协议不支持账号密码登录"})

    account, password = _resolve_login_credentials(
        account=payload.account,
        password=payload.password,
        encrypted_payload=payload.encrypted_payload,
        key_id=payload.key_id,
    )
    profile = await authenticate_password_provider(provider, account, password)
    identity = identity_from_profile(provider, profile)
    try:
        user = await upsert_sso_user_async(db, provider, setting, identity)
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
    provider, _setting = await get_provider_bundle_async(db, provider_key, enabled_only=True)
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
    provider, setting = await get_provider_bundle_async(db, provider_key, enabled_only=True)
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
        user = await upsert_sso_user_async(db, provider, setting, identity, redirect=target)
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
