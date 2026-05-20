"""
User management endpoints.
  • GET  /users/me  — self-service profile
  • PATCH /users/me — update own profile
  • Admin-only: list, get by id, delete
"""
import uuid

from fastapi import APIRouter

from app.api.deps import CurrentUser, ServiceSupabase, SuperUser
from app.schemas.common import PaginatedResponse, Response
from app.schemas.user import UserRead, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


# ── Self-service ───────────────────────────────────────────────────────────────

@router.get("/me", response_model=Response[UserRead])
async def get_me(current_user: CurrentUser) -> Response[UserRead]:
    return Response(data=UserRead.model_validate(current_user))


@router.patch("/me", response_model=Response[UserRead])
async def update_me(
    payload: UserUpdate,
    current_user: CurrentUser,
    client: ServiceSupabase,
) -> Response[UserRead]:
    service = UserService(client)
    user = await service.update(current_user.id, payload)
    return Response(message="Profile updated", data=UserRead.model_validate(user))


# ── Admin-only ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users(
    _: SuperUser,
    client: ServiceSupabase,
    page: int = 1,
    page_size: int = 20,
) -> PaginatedResponse[UserRead]:
    service = UserService(client)
    offset = (page - 1) * page_size
    users = await service.list(limit=page_size + 1, offset=offset)
    has_next = len(users) > page_size
    return PaginatedResponse(
        data=[UserRead.model_validate(u) for u in users[:page_size]],
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
    service = UserService(client)
    user = await service.get(user_id)
    return Response(data=UserRead.model_validate(user))


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: uuid.UUID,
    _: SuperUser,
    client: ServiceSupabase,
) -> None:
    service = UserService(client)
    await service.delete(user_id)
