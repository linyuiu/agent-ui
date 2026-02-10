from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas, security
from ..auth import get_current_user
from ..permissions import get_user_role_names, summarize_permissions
from ..db import get_db
from ..services.sso import build_user_public

router = APIRouter(prefix="/auth", tags=["auth"])


def _verify_password_safe(plain: str, hashed: str) -> bool:
    try:
        return security.verify_password(plain, hashed)
    except Exception:
        return False


@router.post("/register", response_model=schemas.UserPublic, status_code=201)
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)) -> schemas.UserPublic:
    existing = (
        db.query(models.User)
        .filter(models.User.account == payload.account)
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Account already registered")

    email_existing = (
        db.query(models.User)
        .filter(models.User.email == payload.email)
        .first()
    )
    if email_existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = models.User(
        account=payload.account,
        username=payload.username,
        email=payload.email,
        password_hash=security.hash_password(payload.password),
        role="user",
    )
    db.add(user)
    db.flush()
    db.add(models.UserRole(user_id=user.id, role_name="user"))
    db.commit()
    db.refresh(user)
    roles = get_user_role_names(db, user)
    user_public = build_user_public(db, user)
    user_public.roles = roles
    return user_public


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)) -> schemas.LoginResponse:
    user = (
        db.query(models.User)
        .filter(models.User.account == payload.account)
        .first()
    )

    if not user or not _verify_password_safe(payload.password, user.password_hash):
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
        user=build_user_public(db, user),
    )


@router.get("/me", response_model=schemas.UserPublic)
def me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.UserPublic:
    return build_user_public(db, current_user)


@router.get("/permissions", response_model=schemas.PermissionSummary)
def permissions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> schemas.PermissionSummary:
    summary = summarize_permissions(db, current_user)
    return schemas.PermissionSummary(**summary)


@router.post("/password")
def change_password(
    payload: schemas.PasswordChangeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not security.verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="当前密码不正确")
    current_user.password_hash = security.hash_password(payload.new_password)
    db.commit()
    return {"status": "ok"}
