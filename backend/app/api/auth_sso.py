from __future__ import annotations

from urllib.parse import parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..db import get_db
from ..services.sso import (
    PASSWORD_PROTOCOLS,
    REDIRECT_PROTOCOLS,
    authenticate_password_provider,
    authenticate_redirect_provider,
    build_frontend_redirect,
    build_provider_public,
    build_redirect_login_url,
    build_user_public,
    identity_from_profile,
    parse_state_token,
    upsert_sso_user,
)

router = APIRouter(prefix="/auth/sso", tags=["auth_sso"])


def _find_enabled_provider(db: Session, provider_key: str) -> models.AuthProviderConfig:
    provider = (
        db.query(models.AuthProviderConfig)
        .filter(
            models.AuthProviderConfig.key == provider_key,
            models.AuthProviderConfig.enabled.is_(True),
        )
        .first()
    )
    if not provider:
        raise HTTPException(status_code=404, detail="单点登录配置不存在或未启用")
    return provider


def _issue_login_response(db: Session, user: models.User) -> schemas.LoginResponse:
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
        user=build_user_public(db, user),
    )


@router.get("/providers", response_model=list[schemas.SsoProviderPublic])
def list_enabled_sso_providers(db: Session = Depends(get_db)) -> list[schemas.SsoProviderPublic]:
    providers = (
        db.query(models.AuthProviderConfig)
        .filter(models.AuthProviderConfig.enabled.is_(True))
        .order_by(models.AuthProviderConfig.id.asc())
        .all()
    )
    return [build_provider_public(provider) for provider in providers]


@router.post("/password-login", response_model=schemas.LoginResponse)
def sso_password_login(
    payload: schemas.SsoPasswordLoginRequest,
    db: Session = Depends(get_db),
) -> schemas.LoginResponse:
    provider = _find_enabled_provider(db, payload.provider_key)
    if provider.protocol not in PASSWORD_PROTOCOLS:
        raise HTTPException(status_code=400, detail="该单点协议不支持账号密码登录")

    profile = authenticate_password_provider(provider, payload.account, payload.password)
    identity = identity_from_profile(provider, profile)
    user = upsert_sso_user(db, provider, identity)
    db.commit()
    db.refresh(user)
    return _issue_login_response(db, user)


@router.get("/start/{provider_key}")
def start_sso_login(
    provider_key: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    provider = _find_enabled_provider(db, provider_key)
    if provider.protocol not in REDIRECT_PROTOCOLS:
        raise HTTPException(status_code=400, detail="该单点协议不支持跳转登录")
    redirect = str(request.query_params.get("redirect") or "/home/agents")
    if not redirect.startswith("/"):
        redirect = "/home/agents"
    url = build_redirect_login_url(provider, redirect=redirect)
    return RedirectResponse(url=url, status_code=307)


@router.api_route("/callback/{provider_key}", methods=["GET", "POST"])
async def sso_login_callback(
    provider_key: str,
    request: Request,
    db: Session = Depends(get_db),
) -> RedirectResponse:
    provider = _find_enabled_provider(db, provider_key)
    if provider.protocol not in REDIRECT_PROTOCOLS:
        raise HTTPException(status_code=400, detail="该单点协议不支持回调")

    query_params = {key: value for key, value in request.query_params.items()}
    body_params: dict[str, str] = {}
    if request.method.upper() == "POST":
        raw = await request.body()
        if raw:
            body_params = {key: value for key, value in parse_qsl(raw.decode("utf-8"), keep_blank_values=True)}
            if "state" not in query_params and "RelayState" in body_params:
                query_params["state"] = body_params["RelayState"]

    profile = authenticate_redirect_provider(
        provider,
        query_params=query_params,
        body_params=body_params,
    )
    state = str(query_params.get("state") or "").strip()
    target = parse_state_token(state, provider.key)
    identity = identity_from_profile(provider, profile)
    user = upsert_sso_user(db, provider, identity)
    db.commit()
    db.refresh(user)
    login_payload = _issue_login_response(db, user)
    redirect_url = build_frontend_redirect(login_payload.access_token, target)
    return RedirectResponse(url=redirect_url, status_code=307)
