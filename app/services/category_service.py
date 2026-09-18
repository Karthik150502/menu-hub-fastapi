"""
Reads over public.categories via the Supabase SDK — mirrors
RestaurantService's dict-based pattern. Categories is a small, publicly
readable reference table (see supabase/schemas/05_categories.sql); there's
no client-facing write path yet, only reads.
"""
from __future__ import annotations

import uuid
from typing import Any

from app.core.exceptions import NotFoundError
from supabase import AsyncClient


class CategoryService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def list(self) -> list[dict[str, Any]]:
        response = await self.client.table("categories").select("*").order("label").execute()
        return response.data or []

    async def get(self, category_id: uuid.UUID) -> dict[str, Any]:
        response = await (
            self.client.table("categories")
            .select("*")
            .eq("id", str(category_id))
            .maybe_single()
            .execute()
        )
        if response and response.data:
            return response.data
        raise NotFoundError("Category")

    async def list_by_restaurant(
        self, restaurant_id: uuid.UUID, *, limit: int = 20, offset: int = 0
    ) -> list[dict[str, Any]]:
        """Categories actually used by this restaurant's dishes — not the
        full global list, so a restaurant's category picker only shows
        tabs it has dishes in. No embedded-select join available (same
        constraint as DishService), so this is dishes.category_id fetched
        distinct, then categories looked up and paginated by that set."""
        dish_response = await (
            self.client.table("dishes")
            .select("category_id")
            .eq("restaurant_id", str(restaurant_id))
            .execute()
        )
        category_ids = list({row["category_id"] for row in (dish_response.data or [])})
        if not category_ids:
            return []

        response = await (
            self.client.table("categories")
            .select("*")
            .in_("id", category_ids)
            .order("label")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return response.data or []
