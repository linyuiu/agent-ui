from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import ALGORITHM, SECRET_KEY

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="访问需要登录",
    )


async def get_user_from_token(token: str, db: AsyncSession) -> User:
    credentials_exception = _credentials_exception()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    try:
        user_pk = int(user_id)
    except (TypeError, ValueError) as exc:
        raise credentials_exception from exc

    user = await db.get(User, user_pk)
    if not user:
        raise credentials_exception
    if user.status != "active":
        raise credentials_exception

    return user


def get_user_from_token_sync(token: str, db: Session) -> User:
    credentials_exception = _credentials_exception()

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise credentials_exception from exc

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    try:
        user_pk = int(user_id)
    except (TypeError, ValueError) as exc:
        raise credentials_exception from exc

    user = db.query(User).filter(User.id == user_pk).first()
    if not user:
        raise credentials_exception
    if user.status != "active":
        raise credentials_exception

    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    return await get_user_from_token(token, db)
