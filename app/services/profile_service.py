"""
CRUD over public.profiles via the service-role client.

Profile rows are created by the handle_new_user DB trigger on signup
(migration 0004) — never insert here. Deletion happens by deleting the
auth.users row instead (see users.py's admin delete endpoint), which
cascades into profiles via its FK.
"""
import uuid
from typing import Any

from supabase import AsyncClient

from app.core.exceptions import NotFoundError
from app.schemas.user import UserUpdate


class ProfileService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def _get_or_404(self, user_id: uuid.UUID) -> dict[str, Any]:
        response = await (
            self.client.table("profiles")
            .select("*")
            .eq("id", str(user_id))
            .maybe_single()
            .execute()
        )
        if response and response.data:
            return response.data
        raise NotFoundError("Profile")

    async def get(self, user_id: uuid.UUID) -> dict[str, Any]:
        return await self._get_or_404(user_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        response = await (
            self.client.table("profiles")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data or []

    async def update(self, user_id: uuid.UUID, payload: UserUpdate) -> dict[str, Any]:
        await self._get_or_404(user_id)
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get(user_id)

        response = await (
            self.client.table("profiles")
            .update(update_data)
            .eq("id", str(user_id))
            .execute()
        )
        return response.data[0]
