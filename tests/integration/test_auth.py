"""
Integration tests for /api/v1/auth endpoints.
Spins up the full ASGI app with the Supabase clients replaced by an
in-memory fake (see tests/fake_supabase.py) — no real network calls.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1/auth"


@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    resp = await client.post(f"{BASE}/register", json={
        "email": "test_reg@example.com",
        "password": "strongpass1",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["email"] == "test_reg@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    payload = {"email": "test_dup@example.com", "password": "strongpass1"}
    await client.post(f"{BASE}/register", json=payload)
    resp = await client.post(f"{BASE}/register", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_login(client: AsyncClient):
    await client.post(f"{BASE}/register", json={
        "email": "test_login@example.com",
        "password": "strongpass1",
    })
    resp = await client.post(f"{BASE}/login", json={
        "email": "test_login@example.com",
        "password": "strongpass1",
    })
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_me(client: AsyncClient):
    await client.post(f"{BASE}/register", json={
        "email": "test_me@example.com",
        "password": "strongpass1",
    })
    login = await client.post(f"{BASE}/login", json={
        "email": "test_me@example.com",
        "password": "strongpass1",
    })
    token = login.json()["data"]["access_token"]
    resp = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["data"]["email"] == "test_me@example.com"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    await client.post(f"{BASE}/register", json={
        "email": "test_wrong@example.com",
        "password": "correctpass",
    })
    resp = await client.post(f"{BASE}/login", json={
        "email": "test_wrong@example.com",
        "password": "wrongpass",
    })
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_without_token(client: AsyncClient):
    resp = await client.get(f"{BASE}/me")
    assert resp.status_code == 401
