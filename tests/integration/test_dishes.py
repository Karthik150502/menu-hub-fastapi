"""
Integration test for POST /api/v1/dishes.
"""
import pytest
from httpx import AsyncClient

AUTH_BASE = "/api/v1/auth"
RESTAURANTS_BASE = "/api/v1/restaurants"
BASE = "/api/v1/dishes"


async def _register_and_login(client: AsyncClient, email: str, password: str = "strongpass1") -> str:
    await client.post(f"{AUTH_BASE}/register", json={"email": email, "password": password})
    login = await client.post(f"{AUTH_BASE}/login", json={"email": email, "password": password})
    return login.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_dish_with_price(client: AsyncClient):
    token = await _register_and_login(client, "chef@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    restaurant_resp = await client.post(RESTAURANTS_BASE, json={"name": "Chef's Place"}, headers=headers)
    restaurant_id = restaurant_resp.json()["data"]["id"]

    dish_resp = await client.post(
        BASE,
        json={
            "restaurant_id": restaurant_id,
            "name": "Butter Chicken",
            "category": "Mains",
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
    assert data["price"]["base_price"] == 320
    assert data["price"]["final_price"] == 288
    assert data["price"]["discount"]["type"] == "percentage"


@pytest.mark.asyncio
async def test_create_dish_requires_auth(client: AsyncClient):
    resp = await client.post(
        BASE,
        json={
            "restaurant_id": "00000000-0000-0000-0000-000000000000",
            "name": "No Auth Dish",
            "category": "Mains",
            "price": {"base_price": 100},
        },
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_create_dish_for_restaurant_i_dont_own_is_forbidden(client: AsyncClient):
    owner_token = await _register_and_login(client, "owner@example.com")
    restaurant_resp = await client.post(
        RESTAURANTS_BASE, json={"name": "Owner's Place"}, headers={"Authorization": f"Bearer {owner_token}"}
    )
    restaurant_id = restaurant_resp.json()["data"]["id"]

    intruder_token = await _register_and_login(client, "intruder@example.com")
    dish_resp = await client.post(
        BASE,
        json={
            "restaurant_id": restaurant_id,
            "name": "Intruder Dish",
            "category": "Mains",
            "price": {"base_price": 100},
        },
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert dish_resp.status_code == 403
