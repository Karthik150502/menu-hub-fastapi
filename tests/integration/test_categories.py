"""
Integration tests for GET /api/v1/categories and
GET /api/v1/restaurants/{id}/categories.
"""
import uuid
from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

from tests.fake_supabase import FakeSupabaseClient

AUTH_BASE = "/api/v1/auth"
RESTAURANTS_BASE = "/api/v1/restaurants"
DISHES_BASE = "/api/v1/dishes"
BASE = "/api/v1/categories"


async def _register_and_login(client: AsyncClient, email: str, password: str = "strongpass1") -> str:
    await client.post(f"{AUTH_BASE}/register", json={"email": email, "password": password})
    login = await client.post(f"{AUTH_BASE}/login", json={"email": email, "password": password})
    return login.json()["data"]["access_token"]


def _make_category(fake_supabase: FakeSupabaseClient, label: str) -> str:
    category_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    fake_supabase.tables["categories"][category_id] = {
        "id": category_id,
        "label": label,
        "created_at": now,
    }
    return category_id


@pytest.mark.asyncio
async def test_list_categories(client: AsyncClient, fake_supabase: FakeSupabaseClient):
    _make_category(fake_supabase, "Veg")
    _make_category(fake_supabase, "Beverages")

    resp = await client.get(BASE)

    assert resp.status_code == 200
    labels = [c["label"] for c in resp.json()["data"]]
    assert set(labels) == {"Veg", "Beverages"}


@pytest.mark.asyncio
async def test_list_categories_empty(client: AsyncClient):
    resp = await client.get(BASE)

    assert resp.status_code == 200
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_list_restaurant_categories(client: AsyncClient, fake_supabase: FakeSupabaseClient):
    token = await _register_and_login(client, "menu-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    starters_id = _make_category(fake_supabase, "Starters")
    mains_id = _make_category(fake_supabase, "Mains")
    _make_category(fake_supabase, "Desserts")  # unused, shouldn't show up

    restaurant_resp = await client.post(
        RESTAURANTS_BASE, json={"name": "Menu Place"}, headers=headers
    )
    restaurant_id = restaurant_resp.json()["data"]["id"]

    for name, category_id in [("Paneer Tikka", starters_id), ("Butter Chicken", mains_id)]:
        await client.post(
            DISHES_BASE,
            json={
                "restaurant_id": restaurant_id,
                "name": name,
                "category_id": category_id,
                "price": {"base_price": 100},
            },
            headers=headers,
        )

    resp = await client.get(f"{RESTAURANTS_BASE}/{restaurant_id}/categories")

    assert resp.status_code == 200
    body = resp.json()
    assert {c["label"] for c in body["data"]} == {"Starters", "Mains"}
    assert body["page"] == 1
    assert body["has_next"] is False


@pytest.mark.asyncio
async def test_list_restaurant_categories_paginates(
    client: AsyncClient, fake_supabase: FakeSupabaseClient
):
    token = await _register_and_login(client, "paginated-owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    restaurant_resp = await client.post(
        RESTAURANTS_BASE, json={"name": "Big Menu"}, headers=headers
    )
    restaurant_id = restaurant_resp.json()["data"]["id"]

    for i, label in enumerate(["Starters", "Mains", "Desserts"]):
        category_id = _make_category(fake_supabase, label)
        await client.post(
            DISHES_BASE,
            json={
                "restaurant_id": restaurant_id,
                "name": f"Dish {i}",
                "category_id": category_id,
                "price": {"base_price": 100},
            },
            headers=headers,
        )

    first_page = await client.get(
        f"{RESTAURANTS_BASE}/{restaurant_id}/categories", params={"page": 1, "page_size": 2}
    )
    assert len(first_page.json()["data"]) == 2
    assert first_page.json()["has_next"] is True

    second_page = await client.get(
        f"{RESTAURANTS_BASE}/{restaurant_id}/categories", params={"page": 2, "page_size": 2}
    )
    assert len(second_page.json()["data"]) == 1
    assert second_page.json()["has_next"] is False


@pytest.mark.asyncio
async def test_list_categories_for_missing_restaurant_returns_404(client: AsyncClient):
    resp = await client.get(f"{RESTAURANTS_BASE}/00000000-0000-0000-0000-000000000000/categories")
    assert resp.status_code == 404
