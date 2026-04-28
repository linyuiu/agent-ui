from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..services.auth_sessions import extract_auth_token, validate_session_token, validate_session_token_sync

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="访问需要登录",
    )


async def get_user_from_token(token: str, db: AsyncSession) -> User:
    return await validate_session_token(token, db)


def get_user_from_token_sync(token: str, db: Session) -> User:
    return validate_session_token_sync(token, db)


async def get_current_user(
    request: Request,
    response: Response,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    resolved_token = token or extract_auth_token(request)
    if not resolved_token:
        raise _credentials_exception()
    return await validate_session_token(resolved_token, db, request=request, response=response)
