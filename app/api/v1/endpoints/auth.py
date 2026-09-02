"""
Auth endpoints — register, login, refresh, me, phone/otp, phone/verify.
Backed by Supabase Auth (see app/services/auth_service.py).
"""
from fastapi import APIRouter

from app.api.deps import AnonSupabase, CurrentUser
from app.schemas.common import Response
from app.schemas.user import (
    LoginRequest,
    PhoneOtpRequest,
    PhoneVerifyRequest,
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


@router.post("/phone/otp", response_model=Response[None])
async def send_phone_otp(payload: PhoneOtpRequest, client: AnonSupabase) -> Response[None]:
    """Send a login code by SMS — creates a new phone-only account on
    first use. Always returns the same generic message, whether or not the
    phone already has an account."""
    service = AuthService(client)
    await service.send_phone_otp(payload.phone)
    return Response(message="If that number is valid, a code has been sent")


@router.post("/phone/verify", response_model=Response[TokenPair])
async def verify_phone_otp(payload: PhoneVerifyRequest, client: AnonSupabase) -> Response[TokenPair]:
    """Verify an SMS code and receive an access + refresh token pair."""
    service = AuthService(client)
    tokens = await service.verify_phone_otp(payload.phone, payload.token)
    return Response(data=tokens)
