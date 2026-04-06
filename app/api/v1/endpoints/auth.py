"""
Auth endpoints — register, login, refresh, logout, me.
"""
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, DBSession
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.core.exceptions import UnauthorizedError
from app.schemas.common import Response
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Response[UserRead], status_code=201)
async def register(payload: UserCreate, session: DBSession) -> Response[UserRead]:
    """Create a new user account."""
    service = UserService(session)
    user = await service.create(payload)
    return Response(message="Account created", data=UserRead.model_validate(user))


@router.post("/login", response_model=Response[TokenPair])
async def login(payload: LoginRequest, session: DBSession) -> Response[TokenPair]:
    """Authenticate and receive an access + refresh token pair."""
    service = UserService(session)
    user = await service.authenticate(payload.email, payload.password)
    tokens = TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
    return Response(data=tokens)


@router.post("/refresh", response_model=Response[TokenPair])
async def refresh(payload: RefreshRequest) -> Response[TokenPair]:
    """Exchange a valid refresh token for a new token pair."""
    try:
        data = decode_token(payload.refresh_token)
    except ValueError:
        raise UnauthorizedError("Invalid or expired refresh token")

    if data.get("type") != "refresh":
        raise UnauthorizedError("Wrong token type")

    subject = data["sub"]
    tokens = TokenPair(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject),
    )
    return Response(data=tokens)


@router.get("/me", response_model=Response[UserRead])
async def me(current_user: CurrentUser) -> Response[UserRead]:
    """Return the currently authenticated user's profile."""
    return Response(data=UserRead.model_validate(current_user))
