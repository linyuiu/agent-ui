from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, security
from ..auth import get_current_user
from ..permissions import get_user_role_names_async, summarize_permissions_async
from ..db import get_db
from ..services.sso import build_user_public_async

router = APIRouter(prefix="/auth", tags=["auth"])


async def _verify_password_safe(plain: str, hashed: str) -> bool:
    try:
        return await security.verify_password_async(plain, hashed)
    except Exception:
        return False


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
async def login(payload: schemas.LoginRequest, db: AsyncSession = Depends(get_db)) -> schemas.LoginResponse:
    user = (
        await db.execute(select(models.User).where(models.User.account == payload.account))
    ).scalar_one_or_none()

    if not user or not await _verify_password_safe(payload.password, user.password_hash):
        if user and user.source != "local":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="该账号请使用单点登录",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="该用户被禁用，无法登陆",
        )

    token = security.create_access_token(
        {"sub": str(user.id), "email": user.email, "username": user.username, "account": user.account}
    )
    return schemas.LoginResponse(
        access_token=token,
        token_type="bearer",
        user=await build_user_public_async(db, user),
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
    if not await security.verify_password_async(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    current_user.password_hash = await security.hash_password_async(payload.new_password)
    await db.commit()
    return {"status": "ok"}
