from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import record_audit
from app.core.security import (
    AuthenticatedUser,
    create_access_token,
    get_current_user,
    hash_password,
    verify_missing_user_password,
    verify_password,
)
from app.db.session import get_db_session
from app.models import UserAccount, UserRole
from app.schemas.platform import (
    InitialAdministratorCreate,
    SetupStatus,
    TokenResponse,
    UserPublic,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/setup-status", response_model=SetupStatus)
async def setup_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SetupStatus:
    user_count = await session.scalar(select(func.count()).select_from(UserAccount))
    return SetupStatus(setup_required=(user_count or 0) == 0)


@router.post("/setup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def create_initial_administrator(
    payload: InitialAdministratorCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
    response: Response,
) -> TokenResponse:
    bind = session.get_bind()
    if bind.dialect.name == "postgresql":
        await session.execute(text("LOCK TABLE user_accounts IN EXCLUSIVE MODE"))
    user_count = await session.scalar(select(func.count()).select_from(UserAccount))
    if user_count:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Platform setup has already been completed",
        )

    account = UserAccount(
        username=payload.username.strip().lower(),
        full_name=payload.full_name.strip(),
        password_hash=hash_password(payload.password),
        role=UserRole.administrator,
        active=True,
    )
    session.add(account)
    await session.flush()
    await record_audit(
        session,
        actor_username=account.username,
        action="initial_administrator_created",
        resource_type="user_account",
        resource_id=str(account.id),
        detail={"role": UserRole.administrator.value},
        ip_address=request.client.host if request.client else None,
    )
    token, expires_in = create_access_token(account)
    await session.commit()
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    return TokenResponse(access_token=token, expires_in=expires_in)


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
