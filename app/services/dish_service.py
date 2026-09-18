"""
Creates a Dish together with its one ItemPrice row — the two are 1:1
(item_prices.dish_id is a unique FK) and a dish without a price isn't a
meaningful resource on its own, so this is one combined operation rather
than two separate services/endpoints.

No cross-table transaction is available through the Supabase SDK (each
.table() call is its own PostgREST request). For just these two tables,
inserts run sequentially and a failed item_prices insert triggers a
compensating delete of the dish just created, rather than standing up a
Postgres RPC function for atomicity — that's the right answer for the
larger tax_line_items graph (still deferred), not for this.

list_by_restaurant follows the same two-request shape as create: dishes,
item_prices and categories are fetched separately (no embedded-select
join) and zipped in Python by id, since the same "no cross-table
operation" constraint applies to reads too. It filters directly on
dishes.category_id — the caller (list_restaurant_dishes) is expected to
already have a category_id, e.g. from GET /categories.
"""
from __future__ import annotations

import uuid
from typing import Any

from postgrest.exceptions import APIError

from app.core.exceptions import BadRequestError, ForbiddenError
from app.schemas.category import CategoryRead
from app.schemas.dish import DishCreate, DishRead
from app.schemas.price import DiscountCreate, ItemPriceCreate, ItemPriceRead
from app.services.category_service import CategoryService
from app.services.restaurant_service import RestaurantService
from supabase import AsyncClient


def _compute_final_price(price: ItemPriceCreate) -> float:
    """total_tax_amount is honestly 0 here — no tax_line_items are created
    in this flow — so final_price is just base_price adjusted by the
    discount, not trusted as a client-supplied value that could drift from
    base_price."""
    if price.discount is None:
        return price.base_price

    discount: DiscountCreate = price.discount
    if discount.type == "percentage":
        amount = price.base_price * discount.value / 100
    else:
        amount = discount.value
    return max(price.base_price - amount, 0)


def _item_price_row(dish_id: str, price: ItemPriceCreate) -> dict[str, Any]:
    row: dict[str, Any] = {
        "dish_id": dish_id,
        "base_price": price.base_price,
        "currency_code": price.currency_code,
        "total_tax_amount": 0,
        "final_price": _compute_final_price(price),
        "mrp": price.mrp,
        "discount_type": None,
        "discount_on": None,
        "discount_value": None,
        "discount_label": None,
        "discount_valid_from": None,
        "discount_valid_until": None,
    }
    if price.discount is not None:
        row.update(
            discount_type=price.discount.type,
            discount_on=price.discount.on,
            discount_value=price.discount.value,
            discount_label=price.discount.label,
            discount_valid_from=price.discount.valid_from,
            discount_valid_until=price.discount.valid_until,
        )
    return row


class DishService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def create(self, owner_id: uuid.UUID, payload: DishCreate) -> DishRead:
        restaurant = await RestaurantService(self.client).get(payload.restaurant_id)
        if restaurant["owner_id"] != str(owner_id):
            raise ForbiddenError("You do not own this restaurant")

        category = await CategoryService(self.client).get(payload.category_id)

        dish_data = {
            "restaurant_id": str(payload.restaurant_id),
            "name": payload.name,
            "description": payload.description,
            "base_price": payload.price.base_price,
            "currency_code": payload.price.currency_code,
            "category_id": str(payload.category_id),
            "image_url": payload.image_url,
            "available": payload.available,
            "veg": payload.veg,
            "show_in_menu": payload.show_in_menu,
            "tag": payload.tag,
        }
        try:
            dish_response = await self.client.table("dishes").insert(dish_data).execute()
        except APIError as exc:
            raise BadRequestError(exc.message or "Could not create dish") from exc
        dish = dish_response.data[0]

        try:
            price_row = _item_price_row(dish["id"], payload.price)
            price_response = await self.client.table("item_prices").insert(price_row).execute()
        except APIError as exc:
            # roll back the dish we just created — no transaction to rely on
            await self.client.table("dishes").delete().eq("id", dish["id"]).execute()
            raise BadRequestError(exc.message or "Could not create item price") from exc

        price = price_response.data[0]
        return DishRead(
            **dish,
            category=CategoryRead.model_validate(category),
            price=ItemPriceRead.from_row(price),
        )

    async def list_by_restaurant(
        self,
        restaurant_id: uuid.UUID,
        *,
        category_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> list[DishRead]:
        query = self.client.table("dishes").select("*").eq("restaurant_id", str(restaurant_id))
        if category_id is not None:
            query = query.eq("category_id", str(category_id))
        response = await (
            query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
        )
        dishes = response.data or []
        if not dishes:
            return []

        dish_ids = [dish["id"] for dish in dishes]
        category_ids = list({dish["category_id"] for dish in dishes})
        price_response = await (
            self.client.table("item_prices").select("*").in_("dish_id", dish_ids).execute()
        )
        categories_response = await (
            self.client.table("categories").select("*").in_("id", category_ids).execute()
        )
        prices_by_dish = {price["dish_id"]: price for price in (price_response.data or [])}
        categories_by_id = {cat["id"]: cat for cat in (categories_response.data or [])}
        return [
            DishRead(
                **dish,
                category=CategoryRead.model_validate(categories_by_id[dish["category_id"]]),
                price=ItemPriceRead.from_row(prices_by_dish[dish["id"]]),
            )
            for dish in dishes
            if dish["id"] in prices_by_dish and dish["category_id"] in categories_by_id
        ]
