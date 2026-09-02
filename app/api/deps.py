"""
Reusable FastAPI dependencies.
Import these in route handlers via Depends().
"""
import uuid
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.db.supabase import AsyncClient

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import verify_supabase_token
from app.db.supabase import get_anon_client, get_service_client
from app.schemas.user import UserRead
from app.services.profile_service import ProfileService

bearer_scheme = HTTPBearer(auto_error=False)

# ── Type aliases ───────────────────────────────────────────────────────────────
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]
AnonSupabase = Annotated[AsyncClient, Depends(get_anon_client)]
ServiceSupabase = Annotated[AsyncClient, Depends(get_service_client)]


# ── Auth dependencies ──────────────────────────────────────────────────────────

async def get_current_user(
    credentials: BearerToken,
    client: ServiceSupabase,
) -> UserRead:
    """Verify the caller's Supabase-issued token and load their profile.

    email_confirmed is approximated as True here rather than looked up —
    Supabase's access-token claims don't carry email-confirmation status,
    and a project with "confirm email" enabled won't issue a session to an
    unconfirmed account in the first place. register() (auth_service.py)
    reports the real value from the sign-up response, where it matters.
    """
    if not credentials:
        raise UnauthorizedError()

    try:
        claims = await verify_supabase_token(credentials.credentials, client)
    except ValueError:
        raise UnauthorizedError("Invalid or expired token")

    user_id = uuid.UUID(claims["sub"])
    profile = await ProfileService(client).get(user_id)

    return UserRead(
        id=user_id,
        email=claims.get("email") or None,
        phone=claims.get("phone") or None,
        full_name=profile.get("full_name"),
        avatar_url=profile.get("avatar_url"),
        is_active=profile["is_active"],
        is_superuser=profile["is_superuser"],
        email_confirmed=True,
        created_at=profile["created_at"],
        updated_at=profile["updated_at"],
    )


async def get_current_active_user(
    current_user: Annotated[UserRead, Depends(get_current_user)],
) -> UserRead:
    if not current_user.is_active:
        raise ForbiddenError("Inactive account")
    return current_user


async def get_current_superuser(
    current_user: Annotated[UserRead, Depends(get_current_active_user)],
) -> UserRead:
    if not current_user.is_superuser:
        raise ForbiddenError("Superuser access required")
    return current_user


# ── Convenience aliases ────────────────────────────────────────────────────────
CurrentUser = Annotated[UserRead, Depends(get_current_active_user)]
SuperUser = Annotated[UserRead, Depends(get_current_superuser)]
