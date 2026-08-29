"""
Auth actions — register/login/refresh — wrapping Supabase Auth directly.
Always used with the anon client: these represent an end user's own auth
action, not a privileged server-side one (see app/db/supabase.py).

Password hashing, token issuance, and email-confirmation policy are all
Supabase's job now; this service just translates its responses/errors into
this app's schemas and exception types.
"""
import uuid

from supabase import AsyncClient
from supabase_auth.errors import AuthApiError

from app.core.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.schemas.user import TokenPair, UserCreate, UserRead


class AuthService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def register(self, payload: UserCreate) -> UserRead:
        try:
            response = await self.client.auth.sign_up({
                "email": payload.email,
                "password": payload.password,
                "options": {
                    "data": {"full_name": payload.full_name, "avatar_url": payload.avatar_url}
                },
            })
        except AuthApiError as exc:
            if exc.status == 422 or "already registered" in exc.message.lower():
                raise ConflictError("A user with that email already exists") from exc
            raise BadRequestError(exc.message) from exc

        user = response.user
        if user is None:
            raise BadRequestError("Sign up did not return a user")

        metadata = user.user_metadata or {}
        return UserRead(
            id=uuid.UUID(user.id),
            email=user.email,
            full_name=metadata.get("full_name"),
            avatar_url=metadata.get("avatar_url"),
            is_active=True,
            is_superuser=False,
            email_confirmed=user.email_confirmed_at is not None,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def login(self, email: str, password: str) -> TokenPair:
        try:
            response = await self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except AuthApiError as exc:
            raise UnauthorizedError("Invalid email or password") from exc

        session = response.session
        if session is None:
            raise UnauthorizedError("Email not confirmed yet")
        return TokenPair(access_token=session.access_token, refresh_token=session.refresh_token)

    async def refresh(self, refresh_token: str) -> TokenPair:
        try:
            response = await self.client.auth.refresh_session(refresh_token)
        except AuthApiError as exc:
            raise UnauthorizedError("Invalid or expired refresh token") from exc

        session = response.session
        if session is None:
            raise UnauthorizedError("Invalid or expired refresh token")
        return TokenPair(access_token=session.access_token, refresh_token=session.refresh_token)
