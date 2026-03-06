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
    normalize_provider_key,
    normalize_protocol,
)

router = APIRouter(prefix="/sso/providers", tags=["admin_sso"])
_SENSITIVE_KEYWORDS = ("secret", "password", "token", "apikey", "api_key", "private", "credential")


def _validate_protocol_config(protocol: str, config: dict) -> None:
    if protocol == "ldap":
        if not str(config.get("server_url") or "").strip():
            raise HTTPException(status_code=400, detail="LDAP 配置缺少 server_url")
        if not str(config.get("base_dn") or "").strip():
            raise HTTPException(status_code=400, detail="LDAP 配置缺少 base_dn")
        return

    if protocol == "cas":
        if not str(config.get("cas_base_url") or "").strip():
            raise HTTPException(status_code=400, detail="CAS 配置缺少 cas_base_url")
        return

    if protocol in {"oidc", "oauth2"}:
        has_discovery = str(config.get("discovery_url") or "").strip() or str(config.get("issuer") or "").strip()
        has_pair = str(config.get("authorize_url") or "").strip() and str(config.get("token_url") or "").strip()
        if not (has_discovery or has_pair):
            raise HTTPException(
                status_code=400,
                detail="OIDC/OAuth2 配置需要 discovery_url/issuer 或 authorize_url+token_url",
            )
        if not str(config.get("client_id") or "").strip():
            raise HTTPException(status_code=400, detail="OIDC/OAuth2 配置缺少 client_id")
        return

    if protocol == "saml2" and not str(config.get("sso_url") or "").strip():
        raise HTTPException(status_code=400, detail="SAML2 配置缺少 sso_url")


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
        if bind_dn:
            conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True)
        else:
            conn = Connection(server, auto_bind=True)
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
        cas_base = str(config.get("cas_base_url") or "").strip().rstrip("/")
        probe_url = str(config.get("login_url") or (f"{cas_base}/login" if cas_base else "")).strip()
        try:
            async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
                resp = await client.get(probe_url)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"CAS 连接测试失败: {exc}") from exc
        if resp.status_code >= 500:
            raise HTTPException(status_code=400, detail=f"CAS 服务不可用: {resp.status_code}")
        return "CAS 连接成功"

    if protocol in {"oidc", "oauth2"}:
        discovery_url = str(config.get("discovery_url") or "").strip()
        issuer = str(config.get("issuer") or "").strip().rstrip("/")
        if not discovery_url and issuer:
            discovery_url = f"{issuer}/.well-known/openid-configuration"
        if discovery_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    payload = (await client.get(discovery_url)).json()
            except Exception as exc:
                raise HTTPException(status_code=400, detail=f"OIDC/OAuth2 discovery 测试失败: {exc}") from exc
            if not isinstance(payload, dict):
                raise HTTPException(status_code=400, detail="OIDC/OAuth2 discovery 返回格式错误")
            return "OIDC/OAuth2 discovery 连接成功"
        authorize_url = str(config.get("authorize_url") or "").strip()
        token_url = str(config.get("token_url") or "").strip()
        try:
            a = urlparse(authorize_url)
            t = urlparse(token_url)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"OIDC/OAuth2 URL 校验失败: {exc}") from exc
        if not a.scheme or not a.netloc or not t.scheme or not t.netloc:
            raise HTTPException(status_code=400, detail="OIDC/OAuth2 URL 格式不合法")
        return "OIDC/OAuth2 配置校验成功"

    if protocol == "saml2":
        sso_url = str(config.get("sso_url") or "").strip()
        parsed = urlparse(sso_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise HTTPException(status_code=400, detail="SAML2 sso_url 格式不合法")
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
    key = normalize_provider_key(payload.key)
    if not key:
        raise HTTPException(status_code=400, detail="provider key 不合法")
    existing = (
        await db.execute(select(models.AuthProviderConfig.id).where(models.AuthProviderConfig.key == key))
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="provider key 已存在")
    role = (
        await db.execute(select(models.Role.id).where(models.Role.name == (payload.default_role or "user")))
    ).scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=400, detail="Role not found")

    config = normalize_config(payload.config)
    _validate_protocol_config(protocol, config)

    provider = models.AuthProviderConfig(
        key=key,
        name=payload.name.strip(),
        protocol=protocol,
        enabled=bool(payload.enabled),
        auto_create_user=bool(payload.auto_create_user),
        default_role=(payload.default_role or "user").strip() or "user",
        default_workspace=(payload.default_workspace or "default").strip() or "default",
        config=config,
        attribute_mapping=normalize_mapping(payload.attribute_mapping),
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

    if payload.key is not None:
        key = normalize_provider_key(payload.key)
        if not key:
            raise HTTPException(status_code=400, detail="provider key 不合法")
        existing = (
            await db.execute(
                select(models.AuthProviderConfig.id).where(
                    models.AuthProviderConfig.key == key,
                    models.AuthProviderConfig.id != provider_id,
                )
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="provider key 已存在")
        provider.key = key

    if payload.name is not None:
        provider.name = payload.name.strip()
    if payload.protocol is not None:
        provider.protocol = normalize_protocol(payload.protocol)
    if payload.enabled is not None:
        provider.enabled = bool(payload.enabled)
    if payload.auto_create_user is not None:
        provider.auto_create_user = bool(payload.auto_create_user)
    if payload.default_role is not None:
        role = (
            await db.execute(select(models.Role.id).where(models.Role.name == (payload.default_role or "user")))
        ).scalar_one_or_none()
        if role is None:
            raise HTTPException(status_code=400, detail="Role not found")
        provider.default_role = (payload.default_role or "user").strip() or "user"
    if payload.default_workspace is not None:
        provider.default_workspace = (payload.default_workspace or "default").strip() or "default"
    if payload.config is not None:
        provider.config = _merge_sensitive_config(dict(provider.config or {}), normalize_config(payload.config))
    if payload.attribute_mapping is not None:
        provider.attribute_mapping = normalize_mapping(payload.attribute_mapping)

    _validate_protocol_config(provider.protocol, dict(provider.config or {}))

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
