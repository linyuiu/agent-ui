from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode
from uuid import uuid4
from xml.etree import ElementTree

import httpx
from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from .. import models, schemas, security
from ..config import settings
from ..permissions import get_user_role_names_async
from .http_client import get_shared_async_client
from .chat_user_sync import resolve_sso_chat_user_identity, upsert_user_chat_binding

SSO_PROTOCOLS = {"ldap", "cas", "oidc", "oauth2", "saml2"}
LOGIN_METHODS = {"local", *SSO_PROTOCOLS}
PASSWORD_PROTOCOLS = {"ldap"}
REDIRECT_PROTOCOLS = SSO_PROTOCOLS - PASSWORD_PROTOCOLS
_SSO_TOKEN_ALGORITHM = "HS256"
_SENSITIVE_KEYWORDS = (
    "secret",
    "password",
    "token",
    "apikey",
    "api_key",
    "private",
    "credential",
)
_DEFAULT_MAPPING_KEYS = {
    "subject": ("sub", "id", "username", "preferred_username"),
    "username": ("username", "preferred_username", "name", "uid", "login", "id"),
    "nick_name": ("name", "displayName", "display_name", "cn", "nick_name", "username"),
    "email": ("email", "mail", "userPrincipalName"),
    "account": ("preferred_username", "username", "uid", "login", "id"),
    "workspace": ("workspace",),
}
DEFAULT_SSO_WORKSPACE = "default"


class SsoBindRequiredError(Exception):
    def __init__(
        self,
        *,
        bind_token: str,
        provider_key: str,
        provider_name: str,
        provider_protocol: str,
        username: str,
        message: str,
    ) -> None:
        self.bind_token = bind_token
        self.provider_key = provider_key
        self.provider_name = provider_name
        self.provider_protocol = provider_protocol
        self.username = username
        self.message = message
        super().__init__(message)

    def to_schema(self) -> schemas.SsoBindPending:
        return schemas.SsoBindPending(
            bind_token=self.bind_token,
            provider_key=self.provider_key,
            provider_name=self.provider_name,
            provider_protocol=self.provider_protocol,
            username=self.username,
            message=self.message,
        )


@dataclass(slots=True)
class SsoIdentity:
    subject: str
    username: str
    nick_name: str
    email: str
    account: str
    workspace: str
    raw_profile: dict[str, Any]

    def to_payload(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "username": self.username,
            "nick_name": self.nick_name,
            "email": self.email,
            "account": self.account,
            "workspace": self.workspace,
            "raw_profile": self.raw_profile,
        }


def normalize_provider_key(raw: str) -> str:
    cleaned = "".join(ch for ch in str(raw or "").strip().lower() if ch.isalnum() or ch in {"-", "_"})
    return cleaned


def normalize_protocol(raw: str) -> str:
    protocol = str(raw or "").strip().lower()
    if protocol not in SSO_PROTOCOLS:
        raise HTTPException(status_code=400, detail=f"Unsupported protocol: {protocol}")
    return protocol


def normalize_login_method(raw: str) -> str:
    method = str(raw or "").strip().lower()
    if method not in LOGIN_METHODS:
        raise HTTPException(status_code=400, detail=f"Unsupported login method: {method}")
    return method


def provider_login_mode(protocol: str) -> str:
    return "password" if normalize_protocol(protocol) in PASSWORD_PROTOCOLS else "redirect"


def normalize_mapping(raw: dict | None) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {}
    cleaned: dict[str, str] = {}
    for key, value in raw.items():
        field = str(key or "").strip()
        claim = str(value or "").strip()
        if not field or not claim:
            continue
        cleaned[field] = claim
    return cleaned


def normalize_config(raw: dict | None) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def normalize_enabled_methods(raw: list[str] | None) -> list[str]:
    seen: set[str] = set()
    methods: list[str] = []
    for item in raw or []:
        method = normalize_login_method(item)
        if method in seen:
            continue
        seen.add(method)
        methods.append(method)
    return methods or ["local"]


async def ensure_system_auth_setting_async(db: AsyncSession) -> models.SystemAuthSetting:
    setting = (
        await db.execute(
            select(models.SystemAuthSetting).order_by(models.SystemAuthSetting.id.asc()).limit(1)
        )
    ).scalar_one_or_none()
    if not setting:
        setting = models.SystemAuthSetting(
            enabled_methods=["local"],
            default_login_method="local",
            auto_create_user=True,
            default_role="user",
        )
        db.add(setting)
        await db.flush()
        return setting

    changed = False
    enabled_methods = normalize_enabled_methods(list(setting.enabled_methods or []))
    if enabled_methods != list(setting.enabled_methods or []):
        setting.enabled_methods = enabled_methods
        changed = True

    default_login_method = str(setting.default_login_method or "").strip().lower() or "local"
    if default_login_method not in enabled_methods:
        default_login_method = "local" if "local" in enabled_methods else enabled_methods[0]
    if setting.default_login_method != default_login_method:
        setting.default_login_method = default_login_method
        changed = True

    default_role = str(setting.default_role or "").strip() or "user"
    if setting.default_role != default_role:
        setting.default_role = default_role
        changed = True

    if changed:
        await db.flush()
    return setting


async def get_system_auth_setting_async(db: AsyncSession) -> models.SystemAuthSetting:
    return await ensure_system_auth_setting_async(db)


def _provider_enabled(setting: models.SystemAuthSetting, provider: models.AuthProviderConfig) -> bool:
    return normalize_protocol(provider.protocol) in normalize_enabled_methods(list(setting.enabled_methods or []))


async def get_provider_bundle_async(
    db: AsyncSession,
    provider_key: str,
    *,
    enabled_only: bool = False,
) -> tuple[models.AuthProviderConfig | None, models.SystemAuthSetting]:
    setting = await ensure_system_auth_setting_async(db)
    provider = (
        await db.execute(
            select(models.AuthProviderConfig).where(models.AuthProviderConfig.key == provider_key)
        )
    ).scalar_one_or_none()
    if not provider:
        return None, setting
    if enabled_only and not _provider_enabled(setting, provider):
        return None, setting
    return provider, setting


async def list_enabled_provider_bundles_async(
    db: AsyncSession,
) -> tuple[list[tuple[models.AuthProviderConfig, models.SystemAuthSetting]], models.SystemAuthSetting]:
    setting = await ensure_system_auth_setting_async(db)
    enabled_protocols = {
        item for item in normalize_enabled_methods(list(setting.enabled_methods or [])) if item != "local"
    }
    if not enabled_protocols:
        return [], setting
    providers = (
        await db.execute(
            select(models.AuthProviderConfig).order_by(models.AuthProviderConfig.id.asc())
        )
    ).scalars().all()
    return [
        (provider, setting)
        for provider in providers
        if normalize_protocol(provider.protocol) in enabled_protocols
    ], setting


def mask_sensitive_dict(payload: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in payload.items():
        lower_key = str(key).lower()
        if any(keyword in lower_key for keyword in _SENSITIVE_KEYWORDS):
            text = str(value or "")
            masked[key] = "****" if len(text) <= 4 else f"****{text[-4:]}"
            continue
        masked[key] = value
    return masked


async def _bound_provider_keys(db: AsyncSession, user_id: int) -> list[str]:
    rows = (
        await db.execute(
            select(models.UserSsoBinding.provider_key)
            .where(models.UserSsoBinding.user_id == user_id)
            .order_by(models.UserSsoBinding.provider_key.asc())
        )
    ).scalars().all()
    return [str(item) for item in rows]


async def build_user_public_async(db: AsyncSession, user: models.User) -> schemas.UserPublic:
    return schemas.UserPublic(
        id=user.id,
        account=user.account,
        username=user.username,
        email=user.email,
        role=user.role,
        roles=await get_user_role_names_async(db, user),
        status=user.status,
        source=user.source,
        source_provider=user.source_provider or "local",
        workspace=user.workspace,
        bound_providers=await _bound_provider_keys(db, user.id),
    )


def build_provider_out(provider: models.AuthProviderConfig) -> schemas.SsoProviderOut:
    protocol = normalize_protocol(provider.protocol)
    return schemas.SsoProviderOut(
        id=provider.id,
        key=provider.key,
        name=provider.name,
        protocol=protocol,
        config=mask_sensitive_dict(dict(provider.config or {})),
        field_mapping=dict(provider.field_mapping or {}),
        created_at=provider.created_at,
    )


def build_system_auth_setting_out(
    setting: models.SystemAuthSetting,
) -> schemas.SystemAuthSettingOut:
    return schemas.SystemAuthSettingOut(
        id=setting.id,
        enabled_methods=normalize_enabled_methods(list(setting.enabled_methods or [])),
        default_login_method=normalize_login_method(setting.default_login_method or "local"),
        auto_create_user=bool(setting.auto_create_user),
        default_role=setting.default_role or "user",
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )


def build_provider_public(provider: models.AuthProviderConfig) -> schemas.SsoProviderPublic:
    protocol = normalize_protocol(provider.protocol)
    return schemas.SsoProviderPublic(
        key=provider.key,
        name=provider.name,
        protocol=protocol,
        login_mode=provider_login_mode(protocol),
    )


def build_login_options_out(
    setting: models.SystemAuthSetting,
    providers: list[schemas.SsoProviderPublic],
) -> schemas.SsoLoginOptions:
    configured_methods = {provider.protocol for provider in providers}
    enabled_methods = [
        item
        for item in normalize_enabled_methods(list(setting.enabled_methods or []))
        if item == "local" or item in configured_methods
    ]
    if not enabled_methods:
        enabled_methods = ["local"]
    default_login_method = normalize_login_method(setting.default_login_method or "local")
    if default_login_method not in enabled_methods:
        default_login_method = "local" if "local" in enabled_methods else enabled_methods[0]
    return schemas.SsoLoginOptions(
        enabled_methods=enabled_methods,
        default_login_method=default_login_method,
        providers=providers,
    )


async def _ensure_role_exists(db: AsyncSession, role_name: str) -> str:
    normalized = str(role_name or "").strip() or "user"
    role = (await db.execute(select(models.Role).where(models.Role.name == normalized))).scalar_one_or_none()
    if role:
        return role.name
    fallback = (await db.execute(select(models.Role).where(models.Role.name == "user"))).scalar_one_or_none()
    if fallback:
        return fallback.name
    db.add(models.Role(name="user", description="普通用户"))
    await db.flush()
    return "user"


async def _set_single_user_role(db: AsyncSession, user: models.User, role_name: str) -> None:
    existing_rows = (
        await db.execute(select(models.UserRole).where(models.UserRole.user_id == user.id))
    ).scalars().all()
    for row in existing_rows:
        await db.delete(row)
    db.add(models.UserRole(user_id=user.id, role_name=role_name))
    user.role = role_name


async def _unique_account(db: AsyncSession, preferred: str) -> str:
    base = str(preferred or "").strip() or f"sso-{uuid4().hex[:8]}"
    candidate = base
    suffix = 1
    while True:
        existing = (
            await db.execute(select(models.User.id).where(models.User.account == candidate))
        ).scalar_one_or_none()
        if existing is None:
            return candidate
        candidate = f"{base}-{suffix}"
        suffix += 1


async def _unique_email(db: AsyncSession, preferred: str, username: str) -> str:
    if preferred and "@" in preferred:
        base_local, _, base_domain = preferred.partition("@")
        base_local = base_local or username or f"user-{uuid4().hex[:6]}"
        base_domain = base_domain or "example.com"
    else:
        base_local = username or f"user-{uuid4().hex[:6]}"
        base_domain = "example.com"
    candidate = f"{base_local}@{base_domain}"
    suffix = 1
    while True:
        existing = (
            await db.execute(select(models.User.id).where(models.User.email == candidate))
        ).scalar_one_or_none()
        if existing is None:
            return candidate
        candidate = f"{base_local}+{suffix}@{base_domain}"
        suffix += 1


def _read_claim(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if isinstance(value, (list, tuple)):
        for item in value:
            text = str(item or "").strip()
            if text:
                return text
        return ""
    return str(value or "").strip()


def _first_claim(data: dict[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        value = _read_claim(data, key)
        if value:
            return value
    return ""


def identity_from_profile(provider: models.AuthProviderConfig, profile: dict[str, Any]) -> dict[str, Any]:
    protocol = normalize_protocol(provider.protocol)
    profile = profile if isinstance(profile, dict) else {}
    config = dict(provider.config or {})
    mapping = normalize_mapping(dict(provider.field_mapping or {}))

    if protocol == "cas":
        username = _first_claim(profile, ("username", "user", "sub", "id"))
        subject = _first_claim(profile, ("sub", "id", "username", "user")) or username
        nick_name = _first_claim(profile, ("name", "displayName", "display_name", "cn")) or username
        email = _first_claim(profile, ("email", "mail"))
        workspace = DEFAULT_SSO_WORKSPACE
        account = username
    else:
        subject = _read_claim(profile, mapping.get("subject", "")) or _first_claim(profile, _DEFAULT_MAPPING_KEYS["subject"])
        username = _read_claim(profile, mapping.get("username", "")) or _first_claim(profile, _DEFAULT_MAPPING_KEYS["username"])
        nick_name = _read_claim(profile, mapping.get("nick_name", "")) or _first_claim(profile, _DEFAULT_MAPPING_KEYS["nick_name"])
        email = _read_claim(profile, mapping.get("email", "")) or _first_claim(profile, _DEFAULT_MAPPING_KEYS["email"])
        account = _read_claim(profile, mapping.get("account", "")) or _first_claim(profile, _DEFAULT_MAPPING_KEYS["account"])
        workspace = _read_claim(profile, mapping.get("workspace", "")) or _first_claim(profile, _DEFAULT_MAPPING_KEYS["workspace"])
        workspace = workspace or DEFAULT_SSO_WORKSPACE

    username = str(username or account or subject).strip()
    subject = str(subject or username or account).strip()
    account = str(account or username).strip()
    nick_name = str(nick_name or username).strip()
    email = str(email or "").strip()
    workspace = str(workspace or DEFAULT_SSO_WORKSPACE).strip() or DEFAULT_SSO_WORKSPACE

    if not username:
        raise HTTPException(status_code=400, detail="单点返回中缺少用户名")
    if not subject:
        raise HTTPException(status_code=400, detail="单点返回中缺少用户标识")

    identity = SsoIdentity(
        subject=subject,
        username=username,
        nick_name=nick_name,
        email=email,
        account=account or username,
        workspace=workspace,
        raw_profile=profile,
    )
    return identity.to_payload()


def build_state_token(provider_key: str, redirect: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "provider_key": provider_key,
        "redirect": redirect if redirect.startswith("/") else "/home/agents",
        "nonce": secrets.token_urlsafe(12),
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, security.SECRET_KEY, algorithm=_SSO_TOKEN_ALGORITHM)


def parse_state_token(state_token: str, provider_key: str) -> str:
    try:
        payload = jwt.decode(state_token, security.SECRET_KEY, algorithms=[_SSO_TOKEN_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="SSO state 校验失败") from exc
    if str(payload.get("provider_key") or "").strip() != provider_key:
        raise HTTPException(status_code=400, detail="SSO state provider 不匹配")
    redirect = str(payload.get("redirect") or "/home/agents")
    return redirect if redirect.startswith("/") else "/home/agents"


def build_callback_url(provider: models.AuthProviderConfig) -> str:
    configured = str((provider.config or {}).get("callback_url") or "").strip()
    if configured:
        return configured
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/auth/sso/callback/{quote(provider.key, safe='')}"


def build_frontend_redirect(token: str, target_path: str = "/home/agents") -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    safe_target = target_path if target_path.startswith("/") else "/home/agents"
    return f"{base}/login?redirect={quote(safe_target, safe='')}#token={quote(token, safe='')}"


def build_frontend_bind_redirect(
    *,
    bind_token: str,
    target_path: str,
    message: str,
    provider_name: str,
) -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    safe_target = target_path if target_path.startswith("/") else "/home/agents"
    query = urlencode(
        {
            "redirect": safe_target,
            "bind_token": bind_token,
            "bind_message": message,
            "bind_provider": provider_name,
        }
    )
    return f"{base}/login?{query}"


def create_bind_token(provider: models.AuthProviderConfig, identity: dict[str, Any], redirect: str) -> str:
    payload = {
        "provider_key": provider.key,
        "provider_protocol": normalize_protocol(provider.protocol),
        "provider_name": provider.name,
        "redirect": redirect if redirect.startswith("/") else "/home/agents",
        "subject": str(identity.get("subject") or "").strip(),
        "username": str(identity.get("username") or "").strip(),
        "nick_name": str(identity.get("nick_name") or identity.get("username") or "").strip(),
        "email": str(identity.get("email") or "").strip(),
        "account": str(identity.get("account") or identity.get("username") or "").strip(),
        "workspace": str(identity.get("workspace") or DEFAULT_SSO_WORKSPACE).strip() or DEFAULT_SSO_WORKSPACE,
        "raw_profile": dict(identity.get("raw_profile") or {}),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
    }
    return jwt.encode(payload, security.SECRET_KEY, algorithm=_SSO_TOKEN_ALGORITHM)


def parse_bind_token(bind_token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(bind_token, security.SECRET_KEY, algorithms=[_SSO_TOKEN_ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="绑定令牌已失效，请重新发起单点登录") from exc
    return payload


async def _http_json(
    url: str,
    *,
    method: str = "GET",
    data: dict | None = None,
    headers: dict | None = None,
) -> dict:
    client = get_shared_async_client()
    if method == "POST":
        resp = await client.post(url, data=data or {}, headers=headers or {})
    else:
        resp = await client.get(url, params=data or {}, headers=headers or {})
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"上游认证服务异常: {resp.status_code}")
    payload = resp.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="上游认证响应格式错误")
    return payload


async def _get_oidc_endpoints(config: dict[str, Any]) -> tuple[str, str]:
    authorize_url = str(config.get("authorize_url") or "").strip()
    token_url = str(config.get("token_url") or "").strip()
    if authorize_url and token_url:
        return authorize_url, token_url

    discovery_url = str(config.get("discovery_url") or "").strip()
    issuer = str(config.get("issuer") or "").strip().rstrip("/")
    if not discovery_url and issuer:
        discovery_url = f"{issuer}/.well-known/openid-configuration"
    if not discovery_url:
        raise HTTPException(status_code=400, detail="OIDC/OAuth2 配置缺少 authorize_url/token_url")

    payload = await _http_json(discovery_url)
    authorize_url = str(payload.get("authorization_endpoint") or "").strip()
    token_url = str(payload.get("token_endpoint") or "").strip()
    if not authorize_url or not token_url:
        raise HTTPException(status_code=400, detail="OIDC discovery 缺少授权端点")
    return authorize_url, token_url


async def build_redirect_login_url(provider: models.AuthProviderConfig, redirect: str) -> str:
    protocol = normalize_protocol(provider.protocol)
    config = dict(provider.config or {})
    state = build_state_token(provider.key, redirect)
    callback_url = build_callback_url(provider)

    if protocol in {"oidc", "oauth2"}:
        authorize_url, _ = await _get_oidc_endpoints(config)
        scopes = str(config.get("scope") or config.get("scopes") or "openid profile email").strip()
        query = {
            "response_type": "code",
            "client_id": str(config.get("client_id") or "").strip(),
            "redirect_uri": callback_url,
            "scope": scopes,
            "state": state,
        }
        audience = str(config.get("audience") or "").strip()
        if audience:
            query["audience"] = audience
        return f"{authorize_url}?{urlencode(query)}"

    if protocol == "cas":
        cas_base_url = str(config.get("cas_base_url") or config.get("idp_uri") or "").strip().rstrip("/")
        if not cas_base_url:
            raise HTTPException(status_code=400, detail="CAS 配置缺少 idp_uri")
        login_url = str(config.get("login_url") or f"{cas_base_url}/login").strip()
        service_url = f"{callback_url}?state={quote(state, safe='')}"
        return f"{login_url}?{urlencode({'service': service_url})}"

    if protocol == "saml2":
        sso_url = str(config.get("sso_url") or "").strip()
        if not sso_url:
            raise HTTPException(status_code=400, detail="SAML2 配置缺少 sso_url")
        relay_key = str(config.get("relay_state_key") or "RelayState").strip() or "RelayState"
        acs_key = str(config.get("acs_key") or "acs").strip() or "acs"
        return f"{sso_url}?{urlencode({relay_key: state, acs_key: callback_url})}"

    raise HTTPException(status_code=400, detail="该协议不支持跳转登录")


def _decode_id_token_claims(id_token: str) -> dict[str, Any]:
    try:
        return jwt.get_unverified_claims(id_token)
    except Exception:
        return {}


async def _exchange_oidc_code(provider: models.AuthProviderConfig, code: str) -> dict[str, Any]:
    config = dict(provider.config or {})
    _, token_url = await _get_oidc_endpoints(config)
    callback_url = build_callback_url(provider)
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback_url,
        "client_id": str(config.get("client_id") or "").strip(),
        "client_secret": str(config.get("client_secret") or "").strip(),
    }
    token_data = await _http_json(
        token_url,
        method="POST",
        data=payload,
        headers={"accept": "application/json"},
    )
    profile: dict[str, Any] = {}
    id_token = str(token_data.get("id_token") or "").strip()
    if id_token:
        profile.update(_decode_id_token_claims(id_token))

    userinfo_url = str(config.get("userinfo_url") or "").strip()
    access_token = str(token_data.get("access_token") or "").strip()
    if userinfo_url and access_token:
        client = get_shared_async_client()
        resp = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}", "accept": "application/json"},
        )
        if resp.status_code < 400:
            userinfo = resp.json()
            if isinstance(userinfo, dict):
                profile.update(userinfo)
    if not profile:
        raise HTTPException(status_code=400, detail="OIDC/OAuth2 未返回用户信息")
    return profile


def _parse_cas_xml(xml_text: str) -> dict[str, Any]:
    try:
        root = ElementTree.fromstring(xml_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="CAS 响应解析失败") from exc

    profile: dict[str, Any] = {}
    user = root.findtext(".//{*}user") or ""
    if user:
        profile["username"] = user
        profile["sub"] = user

    attrs = root.find(".//{*}attributes")
    if attrs is not None:
        for child in list(attrs):
            key = child.tag.split("}")[-1]
            text = (child.text or "").strip()
            if text:
                profile[key] = text
    if not profile:
        raise HTTPException(status_code=400, detail="CAS 未返回有效用户")
    return profile


async def _validate_cas_ticket(provider: models.AuthProviderConfig, ticket: str, state: str) -> dict[str, Any]:
    config = dict(provider.config or {})
    cas_base_url = str(config.get("cas_base_url") or config.get("idp_uri") or "").strip().rstrip("/")
    if not cas_base_url:
        raise HTTPException(status_code=400, detail="CAS 配置缺少 idp_uri")
    validate_url = str(config.get("validate_url") or f"{cas_base_url}/serviceValidate").strip()
    service_url = f"{build_callback_url(provider)}?state={quote(state, safe='')}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(validate_url, params={"service": service_url, "ticket": ticket})
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail="CAS 票据校验失败")
    return _parse_cas_xml(resp.text)


def _parse_saml_response(raw: str) -> dict[str, Any]:
    if not raw:
        raise HTTPException(status_code=400, detail="SAMLResponse 为空")
    try:
        xml_text = base64.b64decode(raw).decode("utf-8")
        root = ElementTree.fromstring(xml_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="SAMLResponse 解析失败") from exc

    profile: dict[str, Any] = {}
    name_id = root.findtext(".//{*}NameID")
    if name_id:
        profile["sub"] = name_id.strip()
        profile["username"] = name_id.strip()
    for attr in root.findall(".//{*}Attribute"):
        name = str(attr.attrib.get("Name") or "").strip()
        if not name:
            continue
        values = [
            (node.text or "").strip()
            for node in attr.findall(".//{*}AttributeValue")
            if (node.text or "").strip()
        ]
        if not values:
            continue
        profile[name] = values[0] if len(values) == 1 else values
    if not profile:
        raise HTTPException(status_code=400, detail="SAML2 未返回有效用户")
    return profile


def _authenticate_password_provider_sync(
    provider: models.AuthProviderConfig,
    account: str,
    password: str,
) -> dict[str, Any]:
    if normalize_protocol(provider.protocol) != "ldap":
        raise HTTPException(status_code=400, detail="当前单点协议不支持账号密码登录")
    config = dict(provider.config or {})
    server_url = str(config.get("server_url") or "").strip()
    base_dn = str(config.get("base_dn") or "").strip()
    account_attr = str(config.get("account_attr") or "uid").strip()
    if not server_url or not base_dn:
        raise HTTPException(status_code=400, detail="LDAP 配置缺少 server_url/base_dn")

    try:
        from ldap3 import ALL, Connection, Server  # type: ignore
        from ldap3.utils.conv import escape_filter_chars  # type: ignore
    except Exception as exc:
        raise HTTPException(status_code=503, detail="LDAP 依赖缺失，请安装 ldap3") from exc

    bind_dn = str(config.get("bind_dn") or "").strip()
    bind_password = str(config.get("bind_password") or "").strip()
    user_filter_tpl = str(config.get("user_filter") or "").strip() or f"({account_attr}={{account}})"
    escaped_account = escape_filter_chars(str(account or "").strip())
    user_filter = user_filter_tpl.replace("{account}", escaped_account)

    server = Server(server_url, get_info=ALL)
    try:
        admin_conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True) if bind_dn else Connection(server, auto_bind=True)
        admin_conn.search(search_base=base_dn, search_filter=user_filter, attributes=["*", "+"], size_limit=1)
        if not admin_conn.entries:
            raise HTTPException(status_code=401, detail="LDAP 用户不存在")
        entry = admin_conn.entries[0]
        user_dn = str(entry.entry_dn)
        if not user_dn:
            raise HTTPException(status_code=401, detail="LDAP 用户 DN 无效")
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        if not user_conn.bound:
            raise HTTPException(status_code=401, detail="LDAP 认证失败")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="LDAP 认证失败") from exc

    attributes = dict(getattr(entry, "entry_attributes_as_dict", {}) or {})
    attributes.setdefault("sub", user_dn)
    attributes.setdefault("username", account)
    attributes.setdefault("preferred_username", account)
    return attributes


async def authenticate_password_provider(provider: models.AuthProviderConfig, account: str, password: str) -> dict[str, Any]:
    return await run_in_threadpool(_authenticate_password_provider_sync, provider, account, password)


async def authenticate_redirect_provider(
    provider: models.AuthProviderConfig,
    *,
    query_params: dict[str, str],
    body_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    protocol = normalize_protocol(provider.protocol)
    state = str(query_params.get("state") or (body_params or {}).get("RelayState") or "").strip()
    if not state:
        raise HTTPException(status_code=400, detail="缺少 state 参数")

    if protocol in {"oidc", "oauth2"}:
        code = str(query_params.get("code") or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail="缺少授权 code")
        return await _exchange_oidc_code(provider, code)
    if protocol == "cas":
        ticket = str(query_params.get("ticket") or "").strip()
        if not ticket:
            raise HTTPException(status_code=400, detail="缺少 CAS ticket")
        return await _validate_cas_ticket(provider, ticket, state)
    if protocol == "saml2":
        saml_response = str(query_params.get("SAMLResponse") or (body_params or {}).get("SAMLResponse") or "").strip()
        return _parse_saml_response(saml_response)
    raise HTTPException(status_code=400, detail="该协议不支持回调登录")


async def _find_binding(
    db: AsyncSession,
    *,
    provider_key: str,
    subject: str,
) -> models.UserSsoBinding | None:
    if not provider_key or not subject:
        return None
    return (
        await db.execute(
            select(models.UserSsoBinding).where(
                models.UserSsoBinding.provider_key == provider_key,
                models.UserSsoBinding.external_subject == subject,
            )
        )
    ).scalar_one_or_none()


async def _sync_existing_binding(
    binding: models.UserSsoBinding,
    *,
    provider: models.AuthProviderConfig,
    identity: dict[str, Any],
) -> None:
    binding.provider_protocol = normalize_protocol(provider.protocol)
    binding.external_username = str(identity.get("username") or "").strip()
    binding.external_email = str(identity.get("email") or "").strip()
    binding.raw_profile = dict(identity.get("raw_profile") or {})


async def _create_binding(
    db: AsyncSession,
    *,
    user: models.User,
    provider: models.AuthProviderConfig,
    identity: dict[str, Any],
) -> models.UserSsoBinding:
    provider_key = provider.key
    subject = str(identity.get("subject") or "").strip()
    if not subject:
        raise HTTPException(status_code=400, detail="单点返回中缺少用户标识")

    existing_subject = await _find_binding(db, provider_key=provider_key, subject=subject)
    if existing_subject:
        if existing_subject.user_id != user.id:
            raise HTTPException(status_code=409, detail="该单点账号已绑定到其他系统用户")
        await _sync_existing_binding(existing_subject, provider=provider, identity=identity)
        return existing_subject

    existing_provider = (
        await db.execute(
            select(models.UserSsoBinding).where(
                models.UserSsoBinding.user_id == user.id,
                models.UserSsoBinding.provider_key == provider_key,
            )
        )
    ).scalar_one_or_none()
    if existing_provider:
        raise HTTPException(status_code=409, detail="当前账号已绑定该单点系统")

    binding = models.UserSsoBinding(
        user_id=user.id,
        provider_key=provider_key,
        provider_protocol=normalize_protocol(provider.protocol),
        external_subject=subject,
        external_username=str(identity.get("username") or "").strip(),
        external_email=str(identity.get("email") or "").strip(),
        raw_profile=dict(identity.get("raw_profile") or {}),
    )
    db.add(binding)
    await db.flush()
    return binding


async def _create_user_from_identity(
    db: AsyncSession,
    *,
    provider: models.AuthProviderConfig,
    setting: models.SystemAuthSetting,
    identity: dict[str, Any],
    chat_user: models.ChatUser | None = None,
) -> models.User:
    role_name = await _ensure_role_exists(db, setting.default_role or "user")
    username = str(identity.get("username") or "").strip()
    account = await _unique_account(db, str(identity.get("account") or username).strip())
    email = await _unique_email(db, str(identity.get("email") or "").strip(), username)
    source_value = str(chat_user.source or "").strip() if chat_user else ""
    user = models.User(
        account=account,
        username=username,
        email=email,
        password_hash=await security.hash_password_async(uuid4().hex),
        role=role_name,
        status="active",
        source=source_value or normalize_protocol(provider.protocol),
        source_provider=provider.key,
        source_subject=str(identity.get("subject") or "").strip(),
        workspace=str(identity.get("workspace") or DEFAULT_SSO_WORKSPACE).strip() or DEFAULT_SSO_WORKSPACE,
    )
    db.add(user)
    await db.flush()
    await _set_single_user_role(db, user, role_name)
    return user


async def _existing_user_by_username(db: AsyncSession, username: str) -> models.User | None:
    if not username:
        return None
    return (
        await db.execute(select(models.User).where(models.User.username == username))
    ).scalar_one_or_none()


async def upsert_sso_user_async(
    db: AsyncSession,
    provider: models.AuthProviderConfig,
    setting: models.SystemAuthSetting,
    identity: dict[str, Any],
    *,
    redirect: str = "/home/agents",
) -> models.User:
    provider_protocol = normalize_protocol(provider.protocol)
    merged_identity = dict(identity)
    username = str(merged_identity.get("username") or "").strip()
    chat_user = await resolve_sso_chat_user_identity(db, provider=provider, identity=merged_identity)

    binding = await _find_binding(
        db,
        provider_key=provider.key,
        subject=str(merged_identity.get("subject") or "").strip(),
    )
    if binding:
        user = await db.get(models.User, binding.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="绑定的系统用户不存在")
        await _sync_existing_binding(binding, provider=provider, identity=merged_identity)
        if chat_user:
            await upsert_user_chat_binding(db, user=user, chat_user=chat_user, binding_source="sso")
        await db.flush()
        return user

    existing_user = await _existing_user_by_username(db, username)
    if existing_user:
        message = (
            "系统已有本地用户，请先使用本地用户登录后绑定单点系统"
            if str(existing_user.source or "local").strip().lower() == "local"
            else "系统已有同名用户，请先使用已有账号登录后绑定单点系统"
        )
        raise SsoBindRequiredError(
            bind_token=create_bind_token(provider, merged_identity, redirect),
            provider_key=provider.key,
            provider_name=provider.name,
            provider_protocol=provider_protocol,
            username=username,
            message=message,
        )

    if not setting.auto_create_user:
        raise HTTPException(status_code=403, detail="该单点配置不允许自动创建用户")

    user = await _create_user_from_identity(
        db,
        provider=provider,
        setting=setting,
        identity=merged_identity,
        chat_user=chat_user,
    )
    await _create_binding(db, user=user, provider=provider, identity=merged_identity)
    if chat_user:
        await upsert_user_chat_binding(db, user=user, chat_user=chat_user, binding_source="sso")
    await db.flush()
    return user


async def bind_sso_identity_async(
    db: AsyncSession,
    *,
    current_user: models.User,
    bind_token: str,
) -> models.UserSsoBinding:
    payload = parse_bind_token(bind_token)
    provider_key = str(payload.get("provider_key") or "").strip()
    provider = (
        await db.execute(select(models.AuthProviderConfig).where(models.AuthProviderConfig.key == provider_key))
    ).scalar_one_or_none()
    if not provider:
        raise HTTPException(status_code=404, detail="单点配置不存在")

    username = str(payload.get("username") or "").strip()
    if username and current_user.username != username:
        raise HTTPException(status_code=409, detail="当前登录账号与待绑定用户名不一致")

    identity = {
        "subject": str(payload.get("subject") or "").strip(),
        "username": username or current_user.username,
        "nick_name": str(payload.get("nick_name") or current_user.username).strip(),
        "email": str(payload.get("email") or current_user.email).strip(),
        "account": str(payload.get("account") or username or current_user.account).strip(),
        "workspace": str(payload.get("workspace") or current_user.workspace).strip() or current_user.workspace,
        "raw_profile": dict(payload.get("raw_profile") or {}),
    }
    binding = await _create_binding(db, user=current_user, provider=provider, identity=identity)
    chat_user = await resolve_sso_chat_user_identity(db, provider=provider, identity=identity)
    if chat_user:
        await upsert_user_chat_binding(db, user=current_user, chat_user=chat_user, binding_source="sso")
    await db.flush()
    return binding
