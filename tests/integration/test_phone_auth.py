"""
Integration tests for /api/v1/auth/phone/otp and /phone/verify.
"""
import pytest
from httpx import AsyncClient

BASE = "/api/v1/auth"


@pytest.mark.asyncio
async def test_send_and_verify_phone_otp(client: AsyncClient):
    send_resp = await client.post(f"{BASE}/phone/otp", json={"phone": "+919876543210"})
    assert send_resp.status_code == 200

    verify_resp = await client.post(
        f"{BASE}/phone/verify", json={"phone": "+919876543210", "token": "123456"}
    )
    assert verify_resp.status_code == 200
    data = verify_resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data

    me_resp = await client.get(f"{BASE}/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()["data"]
    assert me_data["phone"] == "+919876543210"
    assert me_data["email"] is None


@pytest.mark.asyncio
async def test_verify_phone_otp_wrong_code(client: AsyncClient):
    await client.post(f"{BASE}/phone/otp", json={"phone": "+919876543210"})
    resp = await client.post(
        f"{BASE}/phone/verify", json={"phone": "+919876543210", "token": "999999"}
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_phone_otp_rejects_malformed_number(client: AsyncClient):
    resp = await client.post(f"{BASE}/phone/otp", json={"phone": "not-a-phone"})
    assert resp.status_code == 422
