"""
CRUD over public.restaurants via the Supabase SDK — mirrors
app/services/profile_service.py's dict-based pattern. Ownership is
enforced in Python (not RLS) for the owner-scoped operations, same
reasoning as ProfileService: app/db/supabase.py's clients are module-level
singletons shared across requests, so per-request-scoped auth isn't safe
here without a bigger redesign. Public reads (list/get) rely on RLS's
"restaurants are publicly readable" policy instead — see the caller in
app/api/v1/endpoints/restaurants.py for which client each method expects.
"""
from __future__ import annotations

import uuid
from typing import Any

from supabase import AsyncClient

from app.core.exceptions import ForbiddenError, NotFoundError
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate


class RestaurantService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def _get_or_404(self, restaurant_id: uuid.UUID) -> dict[str, Any]:
        response = await (
            self.client.table("restaurants")
            .select("*")
            .eq("id", str(restaurant_id))
            .maybe_single()
            .execute()
        )
        if response and response.data:
            return response.data
        raise NotFoundError("Restaurant")

    async def create(self, owner_id: uuid.UUID, payload: RestaurantCreate) -> dict[str, Any]:
        data = payload.model_dump()
        data["owner_id"] = str(owner_id)
        response = await self.client.table("restaurants").insert(data).execute()
        return response.data[0]

    async def get(self, restaurant_id: uuid.UUID) -> dict[str, Any]:
        return await self._get_or_404(restaurant_id)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        response = await (
            self.client.table("restaurants")
            .select("*")
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data or []

    async def list_by_owner(
        self, owner_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        response = await (
            self.client.table("restaurants")
            .select("*")
            .eq("owner_id", str(owner_id))
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data or []

    async def update(
        self, restaurant_id: uuid.UUID, owner_id: uuid.UUID, payload: RestaurantUpdate
    ) -> dict[str, Any]:
        restaurant = await self._get_or_404(restaurant_id)
        if restaurant["owner_id"] != str(owner_id):
            raise ForbiddenError("You do not own this restaurant")

        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            return restaurant

        response = await (
            self.client.table("restaurants")
            .update(update_data)
            .eq("id", str(restaurant_id))
            .execute()
        )
        return response.data[0]

    async def delete(self, restaurant_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        restaurant = await self._get_or_404(restaurant_id)
        if restaurant["owner_id"] != str(owner_id):
            raise ForbiddenError("You do not own this restaurant")
        await self.client.table("restaurants").delete().eq("id", str(restaurant_id)).execute()
