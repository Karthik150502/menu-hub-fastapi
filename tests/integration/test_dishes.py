"""
Integration tests for POST /api/v1/dishes and
GET /api/v1/restaurants/{id}/dishes.
"""
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from tests.fake_supabase import FakeSupabaseClient

AUTH_BASE = "/api/v1/auth"
RESTAURANTS_BASE = "/api/v1/restaurants"
BASE = "/api/v1/dishes"


async def _register_and_login(client: AsyncClient, email: str, password: str = "strongpass1") -> str:
    await client.post(f"{AUTH_BASE}/register", json={"email": email, "password": password})
    login = await client.post(f"{AUTH_BASE}/login", json={"email": email, "password": password})
    return login.json()["data"]["access_token"]


def _make_category(fake_supabase: FakeSupabaseClient, label: str) -> str:
    """Seeds a category row directly — there's no create-category endpoint
    (categories is a read-only reference table for clients), so tests that
    need a category_id to create a dish write one straight into the fake
    store, same as they would land there via the seed migration."""
    category_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    fake_supabase.tables["categories"][category_id] = {
        "id": category_id,
        "label": label,
        "created_at": now,
    }
    return category_id


@pytest.mark.asyncio
async def test_create_dish_with_price(client: AsyncClient, fake_supabase: FakeSupabaseClient):
    token = await _register_and_login(client, "chef@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    category_id = _make_category(fake_supabase, "Mains")

    restaurant_resp = await client.post(
        RESTAURANTS_BASE, json={"name": "Chef's Place"}, headers=headers
    )
    restaurant_id = restaurant_resp.json()["data"]["id"]

    dish_resp = await client.post(
        BASE,
        json={
            "restaurant_id": restaurant_id,
            "name": "Butter Chicken",
            "category_id": category_id,
            "price": {
                "base_price": 320,
                "discount": {"type": "percentage", "on": "basePrice", "value": 10},
            },
        },
        headers=headers,
    )
    assert dish_resp.status_code == 201
    data = dish_resp.json()["data"]
    assert data["name"] == "Butter Chicken"
    assert data["category"]["label"] == "Mains"
    assert data["price"]["base_price"] == 320
    assert data["price"]["final_price"] == 288
    assert data["price"]["discount"]["type"] == "percentage"


@pytest.mark.asyncio
async def test_create_dish_requires_auth(client: AsyncClient, fake_supabase: FakeSupabaseClient):
    category_id = _make_category(fake_supabase, "Mains")
    resp = await client.post(
        BASE,
        json={
            "restaurant_id": "00000000-0000-0000-0000-000000000000",
            "name": "No Auth Dish",
            "category_id": category_id,
            "price": {"base_price": 100},
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_dish_for_restaurant_i_dont_own_is_forbidden(
    client: AsyncClient, fake_supabase: FakeSupabaseClient
):
    owner_token = await _register_and_login(client, "owner@example.com")
    restaurant_resp = await client.post(
        RESTAURANTS_BASE,
        json={"name": "Owner's Place"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    restaurant_id = restaurant_resp.json()["data"]["id"]
    category_id = _make_category(fake_supabase, "Mains")

    intruder_token = await _register_and_login(client, "intruder@example.com")
    dish_resp = await client.post(
        BASE,
        json={
            "restaurant_id": restaurant_id,
            "name": "Intruder Dish",
            "category_id": category_id,
            "price": {"base_price": 100},
        },
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert dish_resp.status_code == 403


@pytest.mark.asyncio
async def test_create_dish_for_missing_category_returns_404(
    client: AsyncClient, fake_supabase: FakeSupabaseClient
):
    token = await _register_and_login(client, "chef2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    restaurant_resp = await client.post(
        RESTAURANTS_BASE, json={"name": "Chef's Place 2"}, headers=headers
    )
    restaurant_id = restaurant_resp.json()["data"]["id"]

    dish_resp = await client.post(
        BASE,
        json={
            "restaurant_id": restaurant_id,
            "name": "Ghost Category Dish",
            "category_id": str(uuid.uuid4()),
            "price": {"base_price": 100},
        },
        headers=headers,
    )
    assert dish_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_restaurant_dishes(client: AsyncClient, fake_supabase: FakeSupabaseClient):
    token = await _register_and_login(client, "menu-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    starters_id = _make_category(fake_supabase, "Starters")
    mains_id = _make_category(fake_supabase, "Mains")

    restaurant_resp = await client.post(
        RESTAURANTS_BASE, json={"name": "Menu Place"}, headers=headers
    )
    restaurant_id = restaurant_resp.json()["data"]["id"]

    for name, category_id in [("Paneer Tikka", starters_id), ("Butter Chicken", mains_id)]:
        await client.post(
            BASE,
            json={
                "restaurant_id": restaurant_id,
                "name": name,
                "category_id": category_id,
                "price": {"base_price": 100},
            },
            headers=headers,
        )

    resp = await client.get(f"{RESTAURANTS_BASE}/{restaurant_id}/dishes")
    assert resp.status_code == 200
    body = resp.json()
    assert {d["name"] for d in body["data"]} == {"Paneer Tikka", "Butter Chicken"}
    assert body["page"] == 1
    assert body["has_next"] is False

    mains_resp = await client.get(
        f"{RESTAURANTS_BASE}/{restaurant_id}/dishes", params={"category_id": mains_id}
    )
    assert [d["name"] for d in mains_resp.json()["data"]] == ["Butter Chicken"]


@pytest.mark.asyncio
async def test_list_restaurant_dishes_paginates_for_infinite_scroll(
    client: AsyncClient, fake_supabase: FakeSupabaseClient
):
    token = await _register_and_login(client, "paginated-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    category_id = _make_category(fake_supabase, "Mains")

    restaurant_resp = await client.post(
        RESTAURANTS_BASE, json={"name": "Big Menu"}, headers=headers
    )
    restaurant_id = restaurant_resp.json()["data"]["id"]

    for i in range(3):
        await client.post(
            BASE,
            json={
                "restaurant_id": restaurant_id,
                "name": f"Dish {i}",
                "category_id": category_id,
                "price": {"base_price": 100},
            },
            headers=headers,
        )

    first_page = await client.get(
        f"{RESTAURANTS_BASE}/{restaurant_id}/dishes", params={"page": 1, "page_size": 2}
    )
    assert len(first_page.json()["data"]) == 2
    assert first_page.json()["has_next"] is True

    second_page = await client.get(
        f"{RESTAURANTS_BASE}/{restaurant_id}/dishes", params={"page": 2, "page_size": 2}
    )
    assert len(second_page.json()["data"]) == 1
    assert second_page.json()["has_next"] is False


@pytest.mark.asyncio
async def test_list_dishes_for_missing_restaurant_returns_404(client: AsyncClient):
    resp = await client.get(f"{RESTAURANTS_BASE}/00000000-0000-0000-0000-000000000000/dishes")
    assert resp.status_code == 404
