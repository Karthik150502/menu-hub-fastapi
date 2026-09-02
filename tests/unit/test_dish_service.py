"""
Unit tests for DishService.create — runs against a fake in-memory Supabase
client, no network required.
"""
import uuid

import pytest

from app.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from app.schemas.dish import DishCreate
from app.schemas.price import DiscountCreate, ItemPriceCreate
from app.schemas.restaurant import RestaurantCreate
from app.services.dish_service import DishService
from app.services.restaurant_service import RestaurantService
from tests.fake_supabase import FakeSupabaseClient


async def _make_restaurant(fake_supabase: FakeSupabaseClient, owner_id: uuid.UUID) -> uuid.UUID:
    restaurant = await RestaurantService(fake_supabase).create(
        owner_id, RestaurantCreate(name="Test Kitchen")
    )
    return uuid.UUID(restaurant["id"])


@pytest.mark.asyncio
async def test_create_dish_with_price(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    restaurant_id = await _make_restaurant(fake_supabase, owner_id)

    dish = await DishService(fake_supabase).create(
        owner_id,
        DishCreate(
            restaurant_id=restaurant_id,
            name="Paneer Tikka",
            category="Starters",
            price=ItemPriceCreate(base_price=250),
        ),
    )

    assert dish.name == "Paneer Tikka"
    assert dish.price.base_price == 250
    assert dish.price.final_price == 250
    assert dish.price.total_tax_amount == 0
    assert dish.price.discount is None

    # dishes.base_price / currency_code mirror item_prices, set explicitly
    # at creation since the DB trigger only fires on item_prices writes
    dish_row = fake_supabase.tables["dishes"][str(dish.id)]
    assert dish_row["base_price"] == 250
    assert dish_row["currency_code"] == "INR"


@pytest.mark.asyncio
async def test_create_dish_for_restaurant_i_dont_own_is_forbidden(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    restaurant_id = await _make_restaurant(fake_supabase, owner_id)

    with pytest.raises(ForbiddenError):
        await DishService(fake_supabase).create(
            other_id,
            DishCreate(
                restaurant_id=restaurant_id,
                name="Sneaky Dish",
                category="Mains",
                price=ItemPriceCreate(base_price=100),
            ),
        )


@pytest.mark.asyncio
async def test_create_dish_for_missing_restaurant_raises_not_found(fake_supabase: FakeSupabaseClient):
    with pytest.raises(NotFoundError):
        await DishService(fake_supabase).create(
            uuid.uuid4(),
            DishCreate(
                restaurant_id=uuid.uuid4(),
                name="Ghost Dish",
                category="Mains",
                price=ItemPriceCreate(base_price=100),
            ),
        )


@pytest.mark.asyncio
async def test_percentage_discount_reduces_final_price(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    restaurant_id = await _make_restaurant(fake_supabase, owner_id)

    dish = await DishService(fake_supabase).create(
        owner_id,
        DishCreate(
            restaurant_id=restaurant_id,
            name="Discounted Dish",
            category="Mains",
            price=ItemPriceCreate(
                base_price=200,
                discount=DiscountCreate(type="percentage", on="basePrice", value=10),
            ),
        ),
    )
    assert dish.price.final_price == 180
    assert dish.price.discount.type == "percentage"
    assert dish.price.discount.value == 10


@pytest.mark.asyncio
async def test_fixed_discount_reduces_final_price(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    restaurant_id = await _make_restaurant(fake_supabase, owner_id)

    dish = await DishService(fake_supabase).create(
        owner_id,
        DishCreate(
            restaurant_id=restaurant_id,
            name="Discounted Dish 2",
            category="Mains",
            price=ItemPriceCreate(
                base_price=200,
                discount=DiscountCreate(type="fixed", on="basePrice", value=30),
            ),
        ),
    )
    assert dish.price.final_price == 170


@pytest.mark.asyncio
async def test_failed_price_insert_rolls_back_the_dish(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    restaurant_id = await _make_restaurant(fake_supabase, owner_id)
    fake_supabase.fail_inserts.add("item_prices")

    with pytest.raises(BadRequestError):
        await DishService(fake_supabase).create(
            owner_id,
            DishCreate(
                restaurant_id=restaurant_id,
                name="Doomed Dish",
                category="Mains",
                price=ItemPriceCreate(base_price=100),
            ),
        )

    assert fake_supabase.tables["dishes"] == {}
    assert fake_supabase.tables["item_prices"] == {}
