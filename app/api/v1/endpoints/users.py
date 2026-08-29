"""
User management endpoints.
  • GET  /users/me  — self-service profile
  • PATCH /users/me — update own profile
  • Admin-only: list, get by id, delete
"""
import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, ServiceSupabase, SuperUser
from app.db.supabase import AsyncClient
from app.schemas.common import PaginatedResponse, Response
from app.schemas.user import UserRead, UserUpdate
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/users", tags=["users"])


async def _to_user_read(profile: dict, client: AsyncClient) -> UserRead:
    """Merge a profiles row with its auth.users email — profile.py has no
    email column, that lives only in Supabase's own auth.users table."""
    user_response = await client.auth.admin.get_user_by_id(str(profile["id"]))
    user = user_response.user
    return UserRead(
        id=uuid.UUID(profile["id"]),
        email=user.email if user else "",
        full_name=profile.get("full_name"),
        avatar_url=profile.get("avatar_url"),
        is_active=profile["is_active"],
        is_superuser=profile["is_superuser"],
        email_confirmed=bool(user and user.email_confirmed_at is not None),
        created_at=profile["created_at"],
        updated_at=profile["updated_at"],
    )


# ── Self-service ───────────────────────────────────────────────────────────────

@router.get("/me", response_model=Response[UserRead])
async def get_me(current_user: CurrentUser) -> Response[UserRead]:
    return Response(data=current_user)


@router.patch("/me", response_model=Response[UserRead])
async def update_me(
    payload: UserUpdate,
    current_user: CurrentUser,
    client: ServiceSupabase,
) -> Response[UserRead]:
    profile = await ProfileService(client).update(current_user.id, payload)
    user = UserRead(
        id=current_user.id,
        email=current_user.email,
        full_name=profile.get("full_name"),
        avatar_url=profile.get("avatar_url"),
        is_active=profile["is_active"],
        is_superuser=profile["is_superuser"],
        email_confirmed=current_user.email_confirmed,
        created_at=profile["created_at"],
        updated_at=profile["updated_at"],
    )
    return Response(message="Profile updated", data=user)


# ── Admin-only ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users(
    _: SuperUser,
    client: ServiceSupabase,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[UserRead]:
    offset = (page - 1) * page_size
    profiles = await ProfileService(client).list(limit=page_size + 1, offset=offset)
    has_next = len(profiles) > page_size
    users = [await _to_user_read(p, client) for p in profiles[:page_size]]
    return PaginatedResponse(
        data=users,
        total=-1,
        page=page,
        page_size=page_size,
        has_next=has_next,
    )


@router.get("/{user_id}", response_model=Response[UserRead])
async def get_user(
    user_id: uuid.UUID,
    _: SuperUser,
    client: ServiceSupabase,
) -> Response[UserRead]:
    profile = await ProfileService(client).get(user_id)
    return Response(data=await _to_user_read(profile, client))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    _: SuperUser,
    client: ServiceSupabase,
) -> None:
    """Delete via the Supabase Admin API — cascades into profiles and
    restaurants through their FKs into auth.users, instead of deleting the
    profile row directly."""
    await ProfileService(client).get(user_id)  # 404 if it doesn't exist
    await client.auth.admin.delete_user(str(user_id))
