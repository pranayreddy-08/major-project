from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.security import (
    AuthenticatedUser,
    create_access_token,
    get_current_user,
    verify_missing_user_password,
    verify_password,
)
from app.db.session import get_db_session
from app.models import UserAccount
from app.schemas.platform import TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/token", response_model=TokenResponse)
async def issue_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    response: Response,
) -> TokenResponse:
    account = await session.scalar(
        select(UserAccount).where(UserAccount.username == form.username.strip().lower())
    )
    valid = False
    if account is None:
        verify_missing_user_password(form.password)
    else:
        valid = verify_password(form.password, account.password_hash)
    if account is None or not valid or not account.active:
        await record_audit(
            session,
            actor_username=form.username[:100] or "unknown",
            action="login_failed",
            resource_type="authentication",
            detail={"reason": "invalid_credentials"},
            ip_address=request.client.host if request.client else None,
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token, expires_in = create_access_token(account)
    await record_audit(
        session,
        actor_username=account.username,
        action="login_succeeded",
        resource_type="authentication",
        resource_id=str(account.id),
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=UserPublic)
async def read_current_user(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
) -> UserPublic:
    return UserPublic.model_validate(user)
