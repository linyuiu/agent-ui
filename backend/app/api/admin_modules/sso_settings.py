from __future__ import annotations

from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from ... import models, schemas
from ...auth import get_current_user
from ...db import get_db
from ...permissions import require_manage_menu_async, require_menu_action_async
from ...services.sso import (
    SSO_PROTOCOLS,
    build_provider_out,
    normalize_config,
    normalize_mapping,
    normalize_protocol,
)

router = APIRouter(prefix="/sso/providers", tags=["admin_sso"])
_SENSITIVE_KEYWORDS = ("secret", "password", "token", "apikey", "api_key", "private", "credential")
_PROTOCOL_LABELS = {
    "ldap": "LDAP 登录",
    "cas": "CAS 登录",
    "oidc": "OIDC 登录",
    "oauth2": "OAuth2 登录",
    "saml2": "SAML2 登录",
}


def _provider_key(protocol: str, raw_key: str | None) -> str:
    key = str(raw_key or "").strip().lower()
    return key or protocol


def _validate_protocol_config(protocol: str, config: dict) -> None:
    if protocol == "ldap":
        if not str(config.get("server_url") or "").strip():
            raise HTTPException(status_code=400, detail="LDAP 配置缺少 LDAP 地址")
        if not str(config.get("base_dn") or "").strip():
            raise HTTPException(status_code=400, detail="LDAP 配置缺少用户 OU")
        return

    if protocol == "cas":
        if not str(config.get("cas_base_url") or config.get("idp_uri") or "").strip():
            raise HTTPException(status_code=400, detail="CAS 配置缺少 IdpUri")
        if not str(config.get("validate_url") or "").strip():
            raise HTTPException(status_code=400, detail="CAS 配置缺少验证地址")
        return

    if protocol == "oidc":
        if not str(config.get("discovery_url") or config.get("issuer") or "").strip():
            raise HTTPException(status_code=400, detail="OIDC 配置缺少 Discovery 地址")
        if not str(config.get("client_id") or "").strip():
            raise HTTPException(status_code=400, detail="OIDC 配置缺少客户端 ID")
        return

    if protocol == "oauth2":
        for key, label in (
            ("authorize_url", "授权端地址"),
            ("token_url", "Token 端地址"),
            ("userinfo_url", "用户信息端地址"),
            ("client_id", "客户端 ID"),
        ):
            if not str(config.get(key) or "").strip():
                raise HTTPException(status_code=400, detail=f"OAuth2 配置缺少{label}")
        return

    if protocol == "saml2":
        if not str(config.get("sso_url") or "").strip():
            raise HTTPException(status_code=400, detail="SAML2 配置缺少 SSO 地址")
        return


def _merge_sensitive_config(current: dict, incoming: dict) -> dict:
    merged = dict(incoming or {})
    baseline = dict(current or {})
    for key, value in list(merged.items()):
        key_lower = str(key).lower()
        if not any(word in key_lower for word in _SENSITIVE_KEYWORDS):
            continue
        text = str(value or "").strip()
        if text.startswith("****") or text == "":
            if str(baseline.get(key) or "").strip():
                merged[key] = baseline[key]
    return merged


def _test_ldap_connection_sync(config: dict) -> str:
    try:
        from ldap3 import ALL, Connection, Server  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail="LDAP 依赖缺失，请安装 ldap3") from exc

    try:
        server = Server(str(config.get("server_url") or "").strip(), get_info=ALL)
        bind_dn = str(config.get("bind_dn") or "").strip()
        bind_password = str(config.get("bind_password") or "").strip()
        conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True) if bind_dn else Connection(server, auto_bind=True)
        conn.unbind()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"LDAP 连接测试失败: {exc}") from exc
    return "LDAP 连接成功"


async def _test_protocol_connection(protocol: str, config: dict) -> str:
    if protocol == "ldap":
        return await run_in_threadpool(_test_ldap_connection_sync, config)

    if protocol == "cas":
        validate_url = str(config.get("validate_url") or "").strip()
        try:
            async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
                resp = await client.get(validate_url)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"CAS 连接测试失败: {exc}") from exc
        if resp.status_code >= 500:
            raise HTTPException(status_code=400, detail=f"CAS 服务不可用: {resp.status_code}")
        return "CAS 连接成功"

    if protocol == "oidc":
        discovery_url = str(config.get("discovery_url") or "").strip()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                payload = (await client.get(discovery_url)).json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"OIDC discovery 测试失败: {exc}") from exc
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="OIDC discovery 返回格式错误")
        return "OIDC 连接成功"

    if protocol == "oauth2":
        for key in ("authorize_url", "token_url", "userinfo_url"):
            parsed = urlparse(str(config.get(key) or "").strip())
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise HTTPException(status_code=400, detail=f"OAuth2 配置 {key} 格式不合法")
        return "OAuth2 配置校验成功"

    if protocol == "saml2":
        parsed = urlparse(str(config.get("sso_url") or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="SAML2 配置 sso_url 格式不合法")
        return "SAML2 配置校验成功"

    raise HTTPException(status_code=400, detail="不支持的协议")


@router.get("/protocols")
async def list_sso_protocols(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")
    return {"protocols": sorted(SSO_PROTOCOLS)}


@router.get("", response_model=list[schemas.SsoProviderOut])
async def list_sso_providers(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[schemas.SsoProviderOut]:
    await require_menu_action_async(db, current_user, action="view", menu_id="admin")
    rows = (
        await db.execute(select(models.AuthProviderConfig).order_by(models.AuthProviderConfig.id.asc()))
    ).scalars().all()
    return [build_provider_out(row) for row in rows]


@router.post("/test", response_model=schemas.SsoProviderTestResponse)
async def test_sso_provider(
    payload: schemas.SsoProviderTestRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.SsoProviderTestResponse:
    await require_manage_menu_async(db, current_user)
    protocol = normalize_protocol(payload.protocol)
    config = normalize_config(payload.config)
    _validate_protocol_config(protocol, config)
    message = await _test_protocol_connection(protocol, config)
    return schemas.SsoProviderTestResponse(status="ok", message=message)


@router.post("", response_model=schemas.SsoProviderOut, status_code=201)
async def create_sso_provider(
    payload: schemas.SsoProviderCreate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.SsoProviderOut:
    await require_manage_menu_async(db, current_user)
    protocol = normalize_protocol(payload.protocol)
    existing_protocol = (
        await db.execute(select(models.AuthProviderConfig.id).where(models.AuthProviderConfig.protocol == protocol))
    ).scalar_one_or_none()
    if existing_protocol is not None:
        raise HTTPException(status_code=409, detail="该协议已存在配置，请直接更新")

    role_name = (payload.default_role or "user").strip() or "user"
    role = (await db.execute(select(models.Role.id).where(models.Role.name == role_name))).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=400, detail="Role not found")

    config = normalize_config(payload.config)
    _validate_protocol_config(protocol, config)
    provider = models.AuthProviderConfig(
        key=_provider_key(protocol, payload.key),
        name=(payload.name or _PROTOCOL_LABELS.get(protocol, protocol.upper())).strip(),
        protocol=protocol,
        enabled=bool(payload.enabled),
        auto_create_user=bool(payload.auto_create_user),
        default_role=role_name,
        default_workspace=(payload.default_workspace or "default").strip() or "default",
        config=config,
        field_mapping={} if protocol == "cas" else normalize_mapping(payload.field_mapping),
    )
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return build_provider_out(provider)


@router.put("/{provider_id}", response_model=schemas.SsoProviderOut)
async def update_sso_provider(
    provider_id: int,
    payload: schemas.SsoProviderUpdate,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.SsoProviderOut:
    await require_manage_menu_async(db, current_user)
    provider = await db.get(models.AuthProviderConfig, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="provider 不存在")

    next_protocol = normalize_protocol(payload.protocol or provider.protocol)
    if payload.protocol and payload.protocol != provider.protocol:
        existing_protocol = (
            await db.execute(
                select(models.AuthProviderConfig.id).where(
                    models.AuthProviderConfig.protocol == next_protocol,
                    models.AuthProviderConfig.id != provider_id,
                )
            )
        ).scalar_one_or_none()
        if existing_protocol is not None:
            raise HTTPException(status_code=409, detail="该协议已存在配置")
        provider.protocol = next_protocol
        provider.key = _provider_key(next_protocol, payload.key or provider.key)
    elif payload.key is not None:
        provider.key = _provider_key(next_protocol, payload.key)

    if payload.name is not None:
        provider.name = payload.name.strip()
    elif not provider.name:
        provider.name = _PROTOCOL_LABELS.get(next_protocol, next_protocol.upper())

    if payload.enabled is not None:
        provider.enabled = bool(payload.enabled)
    if payload.auto_create_user is not None:
        provider.auto_create_user = bool(payload.auto_create_user)
    if payload.default_role is not None:
        role_name = (payload.default_role or "user").strip() or "user"
        role = (await db.execute(select(models.Role.id).where(models.Role.name == role_name))).scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=400, detail="Role not found")
        provider.default_role = role_name
    if payload.default_workspace is not None:
        provider.default_workspace = (payload.default_workspace or "default").strip() or "default"
    if payload.config is not None:
        provider.config = _merge_sensitive_config(dict(provider.config or {}), normalize_config(payload.config))
    if payload.field_mapping is not None:
        provider.field_mapping = {} if next_protocol == "cas" else normalize_mapping(payload.field_mapping)
    elif next_protocol == "cas":
        provider.field_mapping = {}

    _validate_protocol_config(next_protocol, dict(provider.config or {}))
    await db.commit()
    await db.refresh(provider)
    return build_provider_out(provider)


@router.delete("/{provider_id}")
async def delete_sso_provider(
    provider_id: int,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    await require_manage_menu_async(db, current_user)
    provider = await db.get(models.AuthProviderConfig, provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="provider 不存在")
    await db.delete(provider)
    await db.commit()
    return {"status": "deleted"}
