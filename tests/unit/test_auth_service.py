"""
Unit tests for AuthService / ProfileService business logic.
These run against a fake in-memory Supabase client — no network required.
"""
import uuid

import pytest

from app.core.exceptions import ConflictError, NotFoundError, UnauthorizedError
from app.schemas.user import UserCreate, UserUpdate
from app.services.auth_service import AuthService
from app.services.profile_service import ProfileService
from tests.fake_supabase import FakeSupabaseClient


@pytest.mark.asyncio
async def test_register_user(fake_supabase: FakeSupabaseClient):
    service = AuthService(fake_supabase)
    user = await service.register(UserCreate(email="alice@example.com", password="secret123"))
    assert user.id is not None
    assert user.email == "alice@example.com"


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_conflict(fake_supabase: FakeSupabaseClient):
    service = AuthService(fake_supabase)
    payload = UserCreate(email="bob@example.com", password="secret123")
    await service.register(payload)
    with pytest.raises(ConflictError):
        await service.register(payload)


@pytest.mark.asyncio
async def test_login_success(fake_supabase: FakeSupabaseClient):
    await AuthService(fake_supabase).register(
        UserCreate(email="carol@example.com", password="correct_password")
    )
    tokens = await AuthService(fake_supabase).login("carol@example.com", "correct_password")
    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_login_wrong_password(fake_supabase: FakeSupabaseClient):
    await AuthService(fake_supabase).register(
        UserCreate(email="dave@example.com", password="correct_password")
    )
    with pytest.raises(UnauthorizedError):
        await AuthService(fake_supabase).login("dave@example.com", "wrong_password")


@pytest.mark.asyncio
async def test_update_profile(fake_supabase: FakeSupabaseClient):
    user = await AuthService(fake_supabase).register(
        UserCreate(email="eve@example.com", password="secret123")
    )
    updated = await ProfileService(fake_supabase).update(user.id, UserUpdate(full_name="Eve Smith"))
    assert updated["full_name"] == "Eve Smith"


@pytest.mark.asyncio
async def test_get_missing_profile_raises_not_found(fake_supabase: FakeSupabaseClient):
    with pytest.raises(NotFoundError):
        await ProfileService(fake_supabase).get(uuid.uuid4())


@pytest.mark.asyncio
async def test_phone_otp_creates_account_and_logs_in(fake_supabase: FakeSupabaseClient):
    service = AuthService(fake_supabase)
    await service.send_phone_otp("+919876543210")

    # a profiles row exists already (handle_new_user fires on the phone
    # signup too), before the code is even verified
    assert len(fake_supabase.tables["profiles"]) == 1

    tokens = await service.verify_phone_otp("+919876543210", "123456")
    assert tokens.access_token
    assert tokens.refresh_token


@pytest.mark.asyncio
async def test_phone_otp_wrong_code_raises_unauthorized(fake_supabase: FakeSupabaseClient):
    service = AuthService(fake_supabase)
    await service.send_phone_otp("+919876543210")
    with pytest.raises(UnauthorizedError):
        await service.verify_phone_otp("+919876543210", "000000")


@pytest.mark.asyncio
async def test_phone_otp_reuses_existing_account(fake_supabase: FakeSupabaseClient):
    service = AuthService(fake_supabase)
    await service.send_phone_otp("+919876543210")
    await service.verify_phone_otp("+919876543210", "123456")

    # second login for the same number — no second account/profile created
    await service.send_phone_otp("+919876543210")
    assert len(fake_supabase.tables["profiles"]) == 1
