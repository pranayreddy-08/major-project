from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID, uuid4

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt.exceptions import InvalidTokenError
from pwdlib import PasswordHash
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models import UserAccount, UserRole

ALGORITHM = "HS256"
password_hash = PasswordHash.recommended()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
_dummy_password_hash = password_hash.hash("not-a-real-user-password")


class AuthenticatedUser(BaseModel):
    id: UUID
    username: str
    full_name: str
    role: UserRole
    active: bool


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def verify_missing_user_password(password: str) -> None:
    password_hash.verify(password, _dummy_password_hash)


def create_access_token(user: UserAccount | AuthenticatedUser) -> tuple[str, int]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.access_token_expire_minutes)
    encoded = jwt.encode(
        {
            "sub": f"username:{user.username}",
            "role": user.role.value,
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "iat": now,
            "exp": expires,
            "jti": str(uuid4()),
        },
        settings.jwt_secret,
        algorithm=ALGORITHM,
    )
    return encoded, settings.access_token_expire_minutes * 60


def decode_access_token(token: str) -> tuple[str, UserRole]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "iat", "iss", "aud", "sub", "role", "jti"]},
        )
        subject = payload["sub"]
        if not isinstance(subject, str) or not subject.startswith("username:"):
            raise InvalidTokenError("invalid subject")
        return subject.removeprefix("username:"), UserRole(payload["role"])
    except (InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuthenticatedUser:
    username, token_role = decode_access_token(token)
    account = await session.scalar(select(UserAccount).where(UserAccount.username == username))
    if account is None or not account.active or account.role != token_role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is unavailable",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return AuthenticatedUser.model_validate(account, from_attributes=True)


def require_roles(*allowed_roles: UserRole) -> Callable:
    async def authorize(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient role for this operation",
            )
        return user

    return authorize
