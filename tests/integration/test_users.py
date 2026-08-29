"""
Integration tests for /api/v1/users — self-service and admin-only.
"""
import pytest
from httpx import AsyncClient

from tests.fake_supabase import FakeSupabaseClient

AUTH_BASE = "/api/v1/auth"
BASE = "/api/v1/users"


async def _register_and_login(client: AsyncClient, email: str, password: str = "strongpass1") -> str:
    await client.post(f"{AUTH_BASE}/register", json={"email": email, "password": password})
    login = await client.post(f"{AUTH_BASE}/login", json={"email": email, "password": password})
    return login.json()["data"]["access_token"]


@pytest.mark.asyncio
async def test_update_me(client: AsyncClient):
    token = await _register_and_login(client, "self@example.com")
    resp = await client.patch(
        f"{BASE}/me",
        json={"full_name": "Self Service"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["full_name"] == "Self Service"


@pytest.mark.asyncio
async def test_non_superuser_cannot_list_users(client: AsyncClient):
    token = await _register_and_login(client, "plain@example.com")
    resp = await client.get(BASE, headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_superuser_can_list_and_delete_users(
    client: AsyncClient, fake_supabase: FakeSupabaseClient
):
    token = await _register_and_login(client, "admin@example.com")

    # promote directly in the store — stand-in for flipping is_superuser via SQL
    admin_id = next(u.id for u in fake_supabase.users_by_id.values() if u.email == "admin@example.com")
    fake_supabase.profiles[admin_id]["is_superuser"] = True

    list_resp = await client.get(BASE, headers={"Authorization": f"Bearer {token}"})
    assert list_resp.status_code == 200
    assert len(list_resp.json()["data"]) >= 1

    delete_resp = await client.delete(f"{BASE}/{admin_id}", headers={"Authorization": f"Bearer {token}"})
    assert delete_resp.status_code == 204
    assert admin_id not in fake_supabase.users_by_id

    # the now-stale token must be rejected cleanly (401), not blow up (500)
    me_resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 401
