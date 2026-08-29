"""
Auth endpoints — register, login, refresh, me.
Backed by Supabase Auth (see app/services/auth_service.py).
"""
from fastapi import APIRouter

from app.api.deps import AnonSupabase, CurrentUser
from app.schemas.common import Response
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Response[UserRead], status_code=201)
async def register(payload: UserCreate, client: AnonSupabase) -> Response[UserRead]:
    """Create a new user account via Supabase Auth."""
    service = AuthService(client)
    user = await service.register(payload)
    return Response(message="Account created", data=user)


@router.post("/login", response_model=Response[TokenPair])
async def login(payload: LoginRequest, client: AnonSupabase) -> Response[TokenPair]:
    """Authenticate and receive an access + refresh token pair."""
    service = AuthService(client)
    tokens = await service.login(payload.email, payload.password)
    return Response(data=tokens)


@router.post("/refresh", response_model=Response[TokenPair])
async def refresh(payload: RefreshRequest, client: AnonSupabase) -> Response[TokenPair]:
    """Exchange a valid refresh token for a new token pair."""
    service = AuthService(client)
    tokens = await service.refresh(payload.refresh_token)
    return Response(data=tokens)


@router.get("/me", response_model=Response[UserRead])
async def me(current_user: CurrentUser) -> Response[UserRead]:
    """Return the currently authenticated user's profile."""
    return Response(data=current_user)
