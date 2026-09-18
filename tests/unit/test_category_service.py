"""
Unit tests for CategoryService — runs against a fake in-memory Supabase
client, no network required.
"""
import uuid
from datetime import UTC, datetime

import pytest

from app.schemas.dish import DishCreate
from app.schemas.price import ItemPriceCreate
from app.schemas.restaurant import RestaurantCreate
from app.services.category_service import CategoryService
from app.services.dish_service import DishService
from app.services.restaurant_service import RestaurantService
from tests.fake_supabase import FakeSupabaseClient


async def _make_restaurant(fake_supabase: FakeSupabaseClient, owner_id: uuid.UUID) -> uuid.UUID:
    restaurant = await RestaurantService(fake_supabase).create(
        owner_id, RestaurantCreate(name="Test Kitchen")
    )
    return uuid.UUID(restaurant["id"])


def _make_category(fake_supabase: FakeSupabaseClient, label: str) -> uuid.UUID:
    category_id = uuid.uuid4()
    now = datetime.now(UTC).isoformat()
    fake_supabase.tables["categories"][str(category_id)] = {
        "id": str(category_id),
        "label": label,
        "created_at": now,
    }
    return category_id


@pytest.mark.asyncio
async def test_list_by_restaurant_returns_only_categories_in_use(
    fake_supabase: FakeSupabaseClient,
):
    owner_id = uuid.uuid4()
    restaurant_id = await _make_restaurant(fake_supabase, owner_id)
    other_restaurant_id = await _make_restaurant(fake_supabase, owner_id)
    starters_id = _make_category(fake_supabase, "Starters")
    mains_id = _make_category(fake_supabase, "Mains")
    _make_category(fake_supabase, "Desserts")  # unused by any dish
    dish_service = DishService(fake_supabase)
    await dish_service.create(
        owner_id,
        DishCreate(
            restaurant_id=restaurant_id,
            name="Paneer Tikka",
            category_id=starters_id,
            price=ItemPriceCreate(base_price=250),
        ),
    )
    await dish_service.create(
        owner_id,
        DishCreate(
            restaurant_id=restaurant_id,
            name="Butter Chicken",
            category_id=mains_id,
            price=ItemPriceCreate(base_price=320),
        ),
    )
    # a dish on a different restaurant shouldn't leak into this list
    await dish_service.create(
        owner_id,
        DishCreate(
            restaurant_id=other_restaurant_id,
            name="Someone Else's Dish",
            category_id=starters_id,
            price=ItemPriceCreate(base_price=100),
        ),
    )

    categories = await CategoryService(fake_supabase).list_by_restaurant(restaurant_id)

    assert {c["label"] for c in categories} == {"Starters", "Mains"}


@pytest.mark.asyncio
async def test_list_by_restaurant_returns_empty_when_no_dishes(
    fake_supabase: FakeSupabaseClient,
):
    owner_id = uuid.uuid4()
    restaurant_id = await _make_restaurant(fake_supabase, owner_id)

    categories = await CategoryService(fake_supabase).list_by_restaurant(restaurant_id)

    assert categories == []


@pytest.mark.asyncio
async def test_list_by_restaurant_respects_pagination(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    restaurant_id = await _make_restaurant(fake_supabase, owner_id)
    dish_service = DishService(fake_supabase)
    for label in ["Starters", "Mains", "Desserts"]:
        category_id = _make_category(fake_supabase, label)
        await dish_service.create(
            owner_id,
            DishCreate(
                restaurant_id=restaurant_id,
                name=f"{label} Dish",
                category_id=category_id,
                price=ItemPriceCreate(base_price=100),
            ),
        )

    page = await CategoryService(fake_supabase).list_by_restaurant(restaurant_id, limit=2, offset=0)
    assert len(page) == 2

    next_page = await CategoryService(fake_supabase).list_by_restaurant(
        restaurant_id, limit=2, offset=2
    )
    assert len(next_page) == 1
