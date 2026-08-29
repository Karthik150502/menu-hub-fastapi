"""
Integration tests for /api/v1/restaurants.
"""
import pytest
from httpx import AsyncClient

AUTH_BASE = "/api/v1/auth"
BASE = "/api/v1/restaurants"


async def _register_and_login(client: AsyncClient, email: str, password: str = "strongpass1") -> str:
    await client.post(f"{AUTH_BASE}/register", json={"email": email, "password": password})
    login = await client.post(f"{AUTH_BASE}/login", json={"email": email, "password": password})
    return login.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_create_and_get_restaurant(client: AsyncClient):
    token = await _register_and_login(client, "owner@example.com")
    create_resp = await client.post(
        BASE, json={"name": "Test Diner"}, headers={"Authorization": f"Bearer {token}"}
    )
    assert create_resp.status_code == 201
    restaurant_id = create_resp.json()["data"]["id"]

    get_resp = await client.get(f"{BASE}/{restaurant_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["data"]["name"] == "Test Diner"


@pytest.mark.asyncio
async def test_list_restaurants_is_public(client: AsyncClient):
    token = await _register_and_login(client, "owner2@example.com")
    await client.post(BASE, json={"name": "Public Spot"}, headers={"Authorization": f"Bearer {token}"})

    resp = await client.get(BASE)
    assert resp.status_code == 200
    assert any(r["name"] == "Public Spot" for r in resp.json()["data"])


@pytest.mark.asyncio
async def test_create_requires_auth(client: AsyncClient):
    resp = await client.post(BASE, json={"name": "No Auth"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_update_by_owner_succeeds(client: AsyncClient):
    token = await _register_and_login(client, "owner3@example.com")
    create_resp = await client.post(
        BASE, json={"name": "Before"}, headers={"Authorization": f"Bearer {token}"}
    )
    restaurant_id = create_resp.json()["data"]["id"]

    update_resp = await client.patch(
        f"{BASE}/{restaurant_id}",
        json={"name": "After"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["name"] == "After"


@pytest.mark.asyncio
async def test_update_by_non_owner_is_forbidden(client: AsyncClient):
    owner_token = await _register_and_login(client, "owner4@example.com")
    create_resp = await client.post(
        BASE, json={"name": "Mine"}, headers={"Authorization": f"Bearer {owner_token}"}
    )
    restaurant_id = create_resp.json()["data"]["id"]

    other_token = await _register_and_login(client, "intruder@example.com")
    update_resp = await client.patch(
        f"{BASE}/{restaurant_id}",
        json={"name": "Hijacked"},
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert update_resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_by_owner_succeeds(client: AsyncClient):
    token = await _register_and_login(client, "owner5@example.com")
    create_resp = await client.post(
        BASE, json={"name": "Temporary"}, headers={"Authorization": f"Bearer {token}"}
    )
    restaurant_id = create_resp.json()["data"]["id"]

    delete_resp = await client.delete(
        f"{BASE}/{restaurant_id}", headers={"Authorization": f"Bearer {token}"}
    )
    assert delete_resp.status_code == 204

    get_resp = await client.get(f"{BASE}/{restaurant_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_my_restaurants(client: AsyncClient):
    token = await _register_and_login(client, "owner6@example.com")
    await client.post(BASE, json={"name": "A"}, headers={"Authorization": f"Bearer {token}"})
    await client.post(BASE, json={"name": "B"}, headers={"Authorization": f"Bearer {token}"})

    resp = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert len(resp.json()["data"]) == 2
