import logging

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, security
from ..auth import get_current_user
from ..auth.auth import oauth2_scheme
from ..permissions import get_user_role_names_async, summarize_permissions_async
from ..db import get_db
from ..services.auth_sessions import (
    cache_login_session,
    clear_auth_cookie,
    create_login_session,
    end_session_for_token,
    extract_auth_token,
    set_auth_cookie,
)
from ..services.sso import build_user_public_async, get_system_auth_setting_async, normalize_enabled_methods
from ..security import decrypt_login_payload, get_login_public_key

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


async def _verify_password_safe(plain: str, hashed: str) -> bool:
    try:
        return await security.verify_password_async(plain, hashed)
    except Exception:
        return False


def _resolve_login_credentials(
    *,
    account: str | None,
    password: str | None,
    encrypted_payload: str | None,
    key_id: str | None,
    request: Request | None = None,
) -> tuple[str, str]:
    resolved_account = str(account or "").strip()
    resolved_password = str(password or "")
    if encrypted_payload:
        try:
            decrypted = decrypt_login_payload(encrypted_payload, key_id=key_id)
        except HTTPException as exc:
            client_host = request.client.host if request and request.client else "-"
            logger.warning(
                "login credential decrypt rejected: detail=%r key_id=%r client=%s path=%s",
                exc.detail,
                key_id,
                client_host,
                request.url.path if request else "-",
            )
            raise
        except Exception as exc:
            client_host = request.client.host if request and request.client else "-"
            logger.exception(
                "login credential decrypt failed unexpectedly: key_id=%r client=%s path=%s",
                key_id,
                client_host,
                request.url.path if request else "-",
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="登录凭据处理失败，请刷新页面后重试",
            ) from exc
        resolved_account = str(decrypted.get("account") or decrypted.get("username") or resolved_account).strip()
        resolved_password = str(decrypted.get("password") or resolved_password)

    if not resolved_account or not resolved_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="账号和密码不能为空",
        )
    return resolved_account, resolved_password


@router.get("/login-key", response_model=schemas.LoginKeyResponse)
async def get_login_key() -> schemas.LoginKeyResponse:
    key = get_login_public_key()
    return schemas.LoginKeyResponse(**key)


@router.post("/register", response_model=schemas.UserPublic, status_code=201)
async def register(payload: schemas.RegisterRequest, db: AsyncSession = Depends(get_db)) -> schemas.UserPublic:
    existing = (
        await db.execute(select(models.User).where(models.User.account == payload.account))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Account already registered")

    email_existing = (
        await db.execute(select(models.User).where(models.User.email == payload.email))
    ).scalar_one_or_none()
    if email_existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    username_existing = (
        await db.execute(select(models.User).where(models.User.username == payload.username))
    ).scalar_one_or_none()
    if username_existing:
        raise HTTPException(status_code=409, detail="Username already registered")

    user = models.User(
        account=payload.account,
        username=payload.username,
        email=payload.email,
        password_hash=await security.hash_password_async(payload.password),
        role="user",
    )
    db.add(user)
    await db.flush()
    db.add(models.UserRole(user_id=user.id, role_name="user"))
    await db.commit()
    await db.refresh(user)
    roles = await get_user_role_names_async(db, user)
    user_public = await build_user_public_async(db, user)
    user_public.roles = roles
    return user_public


@router.post("/login", response_model=schemas.LoginResponse)
async def login(
    payload: schemas.LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> schemas.LoginResponse:
    auth_settings = await get_system_auth_setting_async(db)
    if "local" not in normalize_enabled_methods(list(auth_settings.enabled_methods or [])):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号登录未启用",
        )

    account, password = _resolve_login_credentials(
        account=payload.account,
        password=payload.password,
        encrypted_payload=payload.encrypted_payload,
        key_id=payload.key_id,
        request=request,
    )

    user = (
        await db.execute(select(models.User).where(models.User.account == account))
    ).scalar_one_or_none()

    if not user or not await _verify_password_safe(password, user.password_hash):
        logger.info(
            "login rejected: account=%r reason=%s client=%s",
            account,
            "password_mismatch" if user else "account_not_found",
            request.client.host if request.client else "-",
        )
        if user and user.source != "local":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="该账号请使用单点登录",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号或密码错误",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该用户被禁用，无法登陆",
        )

    permissions = schemas.PermissionSummary(**(await summarize_permissions_async(db, user)))
    token, session = await create_login_session(db, user=user, request=request, login_method="local")
    await db.commit()
    await cache_login_session(user, session)
    set_auth_cookie(response, token, request=request)
    return schemas.LoginResponse(
        access_token="",
        token_type="cookie",
        user=await build_user_public_async(db, user),
        permissions=permissions,
        session_expires_at=session.expires_at,
    )


@router.get("/me", response_model=schemas.UserPublic)
async def me(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.UserPublic:
    return await build_user_public_async(db, current_user)


@router.get("/permissions", response_model=schemas.PermissionSummary)
async def permissions(
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> schemas.PermissionSummary:
    summary = await summarize_permissions_async(db, current_user)
    return schemas.PermissionSummary(**summary)


@router.post("/password")
async def change_password(
    payload: schemas.PasswordChangeRequest,
    current_user: models.User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    db_user = await db.get(models.User, current_user.id)
    if not db_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="访问需要登录")
    if not await security.verify_password_async(payload.current_password, db_user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    db_user.password_hash = await security.hash_password_async(payload.new_password)
    await db.commit()
    return {"status": "ok"}


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> dict:
    resolved_token = token or extract_auth_token(request)
    if resolved_token:
        try:
            await end_session_for_token(db, resolved_token)
            await db.commit()
        except HTTPException:
            await db.rollback()
    clear_auth_cookie(response)
    return {"status": "ok"}
