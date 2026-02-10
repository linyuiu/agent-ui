from __future__ import annotations

import base64
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode
from uuid import uuid4
from xml.etree import ElementTree

import httpx
from fastapi import HTTPException
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..config import settings
from ..permissions import get_user_role_names

SSO_PROTOCOLS = {"ldap", "cas", "oidc", "oauth2", "saml2"}
PASSWORD_PROTOCOLS = {"ldap"}
REDIRECT_PROTOCOLS = SSO_PROTOCOLS - PASSWORD_PROTOCOLS
_SSO_STATE_ALGORITHM = "HS256"
_SENSITIVE_KEYWORDS = (
    "secret",
    "password",
    "token",
    "apikey",
    "api_key",
    "private",
    "credential",
)


def normalize_provider_key(raw: str) -> str:
    cleaned = "".join(ch for ch in str(raw or "").strip().lower() if ch.isalnum() or ch in {"-", "_"})
    return cleaned


def provider_login_mode(protocol: str) -> str:
    return "password" if protocol in PASSWORD_PROTOCOLS else "redirect"


def normalize_protocol(raw: str) -> str:
    protocol = str(raw or "").strip().lower()
    if protocol not in SSO_PROTOCOLS:
        raise HTTPException(status_code=400, detail=f"Unsupported protocol: {protocol}")
    return protocol


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


def mask_sensitive_dict(payload: dict[str, Any]) -> dict[str, Any]:
    masked: dict[str, Any] = {}
    for key, value in payload.items():
        lower_key = str(key).lower()
        if any(keyword in lower_key for keyword in _SENSITIVE_KEYWORDS):
            text = str(value or "")
            if len(text) <= 4:
                masked[key] = "****"
            else:
                masked[key] = f"****{text[-4:]}"
            continue
        masked[key] = value
    return masked


def build_provider_out(provider: models.AuthProviderConfig) -> schemas.SsoProviderOut:
    return schemas.SsoProviderOut(
        id=provider.id,
        key=provider.key,
        name=provider.name,
        protocol=provider.protocol,
        enabled=bool(provider.enabled),
        auto_create_user=bool(provider.auto_create_user),
        default_role=provider.default_role or "user",
        default_workspace=provider.default_workspace or "default",
        config=mask_sensitive_dict(dict(provider.config or {})),
        attribute_mapping=dict(provider.attribute_mapping or {}),
        created_at=provider.created_at,
    )


def build_provider_public(provider: models.AuthProviderConfig) -> schemas.SsoProviderPublic:
    return schemas.SsoProviderPublic(
        key=provider.key,
        name=provider.name,
        protocol=provider.protocol,
        login_mode=provider_login_mode(provider.protocol),
    )


def build_user_public(db: Session, user: models.User) -> schemas.UserPublic:
    roles = get_user_role_names(db, user)
    return schemas.UserPublic(
        id=user.id,
        account=user.account,
        username=user.username,
        email=user.email,
        role=user.role,
        roles=roles,
        status=user.status,
        source=user.source,
        source_provider=user.source_provider or "local",
        source_subject=user.source_subject or "",
        workspace=user.workspace,
    )


def _ensure_role_exists(db: Session, role_name: str) -> str:
    normalized = str(role_name or "").strip() or "user"
    role = db.query(models.Role).filter(models.Role.name == normalized).first()
    if role:
        return role.name
    fallback = db.query(models.Role).filter(models.Role.name == "user").first()
    if fallback:
        return fallback.name
    db.add(models.Role(name="user", description="普通用户"))
    db.flush()
    return "user"


def _set_single_user_role(db: Session, user: models.User, role_name: str) -> None:
    db.query(models.UserRole).filter(models.UserRole.user_id == user.id).delete(synchronize_session=False)
    db.add(models.UserRole(user_id=user.id, role_name=role_name))
    user.role = role_name


def _unique_account(db: Session, preferred: str) -> str:
    base = str(preferred or "").strip() or f"sso-{uuid4().hex[:8]}"
    existing = db.query(models.User).filter(models.User.account == base).first()
    if not existing:
        return base
    for idx in range(1, 1000):
        candidate = f"{base}-{idx}"
        existing = db.query(models.User).filter(models.User.account == candidate).first()
        if not existing:
            return candidate
    return f"{base}-{uuid4().hex[:6]}"


def _safe_email(account: str, email: str | None) -> str:
    raw = str(email or "").strip()
    if raw and "@" in raw:
        return raw
    local = account.replace(" ", ".").replace("/", ".").strip(".")
    local = local or f"user-{uuid4().hex[:6]}"
    return f"{local}@example.com"


def _read_claim(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if isinstance(value, (list, tuple)):
        for item in value:
            text = str(item or "").strip()
            if text:
                return text
        return ""
    return str(value or "").strip()


def identity_from_profile(
    provider: models.AuthProviderConfig,
    profile: dict[str, Any],
) -> dict[str, str]:
    mapping = {
        "subject": "sub",
        "account": "preferred_username",
        "username": "name",
        "email": "email",
        "workspace": "workspace",
    }
    mapping.update(normalize_mapping(provider.attribute_mapping))

    subject = _read_claim(profile, mapping["subject"]) or _read_claim(profile, "id")
    account = _read_claim(profile, mapping["account"]) or _read_claim(profile, "username") or subject
    username = _read_claim(profile, mapping["username"]) or account or subject
    email = _read_claim(profile, mapping["email"])
    workspace = _read_claim(profile, mapping["workspace"]) or provider.default_workspace or "default"

    if not subject:
        subject = account or username
    if not account:
        account = subject or f"sso-{uuid4().hex[:8]}"

    return {
        "subject": subject,
        "account": account,
        "username": username or account,
        "email": _safe_email(account, email),
        "workspace": workspace,
    }


def upsert_sso_user(
    db: Session,
    provider: models.AuthProviderConfig,
    identity: dict[str, str],
) -> models.User:
    subject = str(identity.get("subject") or "").strip()
    account = str(identity.get("account") or "").strip()
    username = str(identity.get("username") or "").strip() or account
    workspace = str(identity.get("workspace") or provider.default_workspace or "default").strip() or "default"
    email = _safe_email(account, identity.get("email"))

    existing = None
    if subject:
        existing = (
            db.query(models.User)
            .filter(
                models.User.source_provider == provider.key,
                models.User.source_subject == subject,
            )
            .first()
        )
    if not existing and account:
        existing = db.query(models.User).filter(models.User.account == account).first()

    if existing:
        existing.username = username or existing.username
        existing.email = email or existing.email
        existing.workspace = workspace
        existing.source = provider.protocol
        existing.source_provider = provider.key
        existing.source_subject = subject
        if not existing.password_hash:
            existing.password_hash = security.hash_password(uuid4().hex)
        db.flush()
        return existing

    if not provider.auto_create_user:
        raise HTTPException(status_code=403, detail="该单点配置不允许自动创建用户")

    role_name = _ensure_role_exists(db, provider.default_role or "user")
    safe_account = _unique_account(db, account)

    user = models.User(
        account=safe_account,
        username=username or safe_account,
        email=email,
        password_hash=security.hash_password(uuid4().hex),
        role=role_name,
        status="active",
        source=provider.protocol,
        source_provider=provider.key,
        source_subject=subject,
        workspace=workspace,
    )
    db.add(user)
    db.flush()
    _set_single_user_role(db, user, role_name)
    db.flush()
    return user


def build_state_token(provider_key: str, redirect: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "provider_key": provider_key,
        "redirect": redirect,
        "nonce": secrets.token_urlsafe(12),
        "exp": now + timedelta(minutes=10),
    }
    return jwt.encode(payload, security.SECRET_KEY, algorithm=_SSO_STATE_ALGORITHM)


def parse_state_token(state_token: str, provider_key: str) -> str:
    try:
        payload = jwt.decode(
            state_token,
            security.SECRET_KEY,
            algorithms=[_SSO_STATE_ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(status_code=400, detail="SSO state 校验失败") from exc
    state_provider = str(payload.get("provider_key") or "").strip()
    if state_provider != provider_key:
        raise HTTPException(status_code=400, detail="SSO state provider 不匹配")
    redirect = str(payload.get("redirect") or "/home/agents")
    if not redirect.startswith("/"):
        redirect = "/home/agents"
    return redirect


def build_callback_url(provider_key: str) -> str:
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    return f"{base}/auth/sso/callback/{quote(provider_key, safe='')}"


def build_frontend_redirect(token: str, target_path: str = "/home/agents") -> str:
    base = settings.FRONTEND_BASE_URL.rstrip("/")
    safe_target = target_path if target_path.startswith("/") else "/home/agents"
    return f"{base}/login?redirect={quote(safe_target, safe='')}&sso=1#token={quote(token, safe='')}"


def _http_json(url: str, *, method: str = "GET", data: dict | None = None, headers: dict | None = None) -> dict:
    with httpx.Client(timeout=20.0) as client:
        if method == "POST":
            resp = client.post(url, data=data or {}, headers=headers or {})
        else:
            resp = client.get(url, params=data or {}, headers=headers or {})
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail=f"上游认证服务异常: {resp.status_code}")
    payload = resp.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="上游认证响应格式错误")
    return payload


def _get_oidc_endpoints(config: dict[str, Any]) -> tuple[str, str]:
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

    payload = _http_json(discovery_url)
    authorize_url = str(payload.get("authorization_endpoint") or "").strip()
    token_url = str(payload.get("token_endpoint") or "").strip()
    if not authorize_url or not token_url:
        raise HTTPException(status_code=400, detail="OIDC discovery 缺少授权端点")
    return authorize_url, token_url


def build_redirect_login_url(provider: models.AuthProviderConfig, redirect: str) -> str:
    protocol = provider.protocol
    config = dict(provider.config or {})
    state = build_state_token(provider.key, redirect)
    callback_url = build_callback_url(provider.key)

    if protocol in {"oidc", "oauth2"}:
        authorize_url, _ = _get_oidc_endpoints(config)
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
        cas_base_url = str(config.get("cas_base_url") or "").strip().rstrip("/")
        if not cas_base_url:
            raise HTTPException(status_code=400, detail="CAS 配置缺少 cas_base_url")
        login_url = str(config.get("login_url") or f"{cas_base_url}/login").strip()
        service_url = f"{callback_url}?state={quote(state, safe='')}"
        return f"{login_url}?{urlencode({'service': service_url})}"

    if protocol == "saml2":
        sso_url = str(config.get("sso_url") or "").strip()
        if not sso_url:
            raise HTTPException(status_code=400, detail="SAML2 配置缺少 sso_url")
        relay_key = str(config.get("relay_state_key") or "RelayState").strip() or "RelayState"
        acs_key = str(config.get("acs_key") or "acs").strip() or "acs"
        params = {relay_key: state, acs_key: callback_url}
        return f"{sso_url}?{urlencode(params)}"

    raise HTTPException(status_code=400, detail="该协议不支持跳转登录")


def _decode_id_token_claims(id_token: str) -> dict[str, Any]:
    try:
        return jwt.get_unverified_claims(id_token)
    except Exception:
        return {}


def _exchange_oidc_code(provider: models.AuthProviderConfig, code: str) -> dict[str, Any]:
    config = dict(provider.config or {})
    _, token_url = _get_oidc_endpoints(config)
    callback_url = build_callback_url(provider.key)

    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback_url,
        "client_id": str(config.get("client_id") or "").strip(),
        "client_secret": str(config.get("client_secret") or "").strip(),
    }
    headers = {"accept": "application/json"}
    token_data = _http_json(token_url, method="POST", data=payload, headers=headers)
    profile: dict[str, Any] = {}
    id_token = str(token_data.get("id_token") or "").strip()
    if id_token:
        profile.update(_decode_id_token_claims(id_token))

    userinfo_url = str(config.get("userinfo_url") or "").strip()
    access_token = str(token_data.get("access_token") or "").strip()
    if userinfo_url and access_token:
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(
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


def _validate_cas_ticket(provider: models.AuthProviderConfig, ticket: str, state: str) -> dict[str, Any]:
    config = dict(provider.config or {})
    cas_base_url = str(config.get("cas_base_url") or "").strip().rstrip("/")
    if not cas_base_url:
        raise HTTPException(status_code=400, detail="CAS 配置缺少 cas_base_url")
    validate_url = str(config.get("validate_url") or f"{cas_base_url}/serviceValidate").strip()
    service_url = f"{build_callback_url(provider.key)}?state={quote(state, safe='')}"

    with httpx.Client(timeout=20.0) as client:
        resp = client.get(validate_url, params={"service": service_url, "ticket": ticket})
    if resp.status_code >= 400:
        raise HTTPException(status_code=400, detail="CAS 票据校验失败")
    return _parse_cas_xml(resp.text)


def _parse_saml_response(raw: str) -> dict[str, Any]:
    if not raw:
        raise HTTPException(status_code=400, detail="SAMLResponse 为空")
    try:
        decoded = base64.b64decode(raw)
        xml_text = decoded.decode("utf-8")
    except Exception as exc:
        raise HTTPException(status_code=400, detail="SAMLResponse 解码失败") from exc

    try:
        root = ElementTree.fromstring(xml_text)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="SAMLResponse XML 解析失败") from exc

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


def authenticate_password_provider(
    provider: models.AuthProviderConfig,
    account: str,
    password: str,
) -> dict[str, Any]:
    if provider.protocol != "ldap":
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
    user_filter_tpl = str(config.get("user_filter") or "").strip()
    if not user_filter_tpl:
        user_filter_tpl = f"({account_attr}={{account}})"
    escaped_account = escape_filter_chars(str(account or "").strip())
    user_filter = user_filter_tpl.replace("{account}", escaped_account)

    server = Server(server_url, get_info=ALL)
    try:
        if bind_dn:
            admin_conn = Connection(server, user=bind_dn, password=bind_password, auto_bind=True)
        else:
            admin_conn = Connection(server, auto_bind=True)
        admin_conn.search(
            search_base=base_dn,
            search_filter=user_filter,
            attributes=["*", "+"],
            size_limit=1,
        )
        if not admin_conn.entries:
            raise HTTPException(status_code=401, detail="LDAP 用户不存在")
        entry = admin_conn.entries[0]
        user_dn = str(entry.entry_dn)
        if not user_dn:
            raise HTTPException(status_code=401, detail="LDAP 用户 DN 无效")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail="LDAP 查询失败") from exc

    try:
        user_conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        if not user_conn.bound:
            raise HTTPException(status_code=401, detail="LDAP 认证失败")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=401, detail="LDAP 认证失败") from exc

    attributes = {}
    try:
        attributes = dict(entry.entry_attributes_as_dict or {})
    except Exception:
        attributes = {}
    attributes.setdefault("sub", user_dn)
    attributes.setdefault("username", account)
    attributes.setdefault("preferred_username", account)
    return attributes


def authenticate_redirect_provider(
    provider: models.AuthProviderConfig,
    *,
    query_params: dict[str, str],
    body_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    protocol = provider.protocol
    state = str(query_params.get("state") or body_params and body_params.get("RelayState") or "").strip()
    if not state:
        raise HTTPException(status_code=400, detail="缺少 state 参数")

    if protocol in {"oidc", "oauth2"}:
        code = str(query_params.get("code") or "").strip()
        if not code:
            raise HTTPException(status_code=400, detail="缺少授权 code")
        return _exchange_oidc_code(provider, code)

    if protocol == "cas":
        ticket = str(query_params.get("ticket") or "").strip()
        if not ticket:
            raise HTTPException(status_code=400, detail="缺少 CAS ticket")
        return _validate_cas_ticket(provider, ticket, state)

    if protocol == "saml2":
        saml_response = str(query_params.get("SAMLResponse") or "").strip()
        if not saml_response:
            data = body_params or {}
            saml_response = str(data.get("SAMLResponse") or "").strip()
        return _parse_saml_response(saml_response)

    raise HTTPException(status_code=400, detail="该协议不支持回调登录")
