"""
Unit tests for UserService business logic.
These run against an in-memory SQLite DB — no network required.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnauthorizedError
from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_create_user(session: AsyncSession):
    service = UserService(session)
    user = await service.create(UserCreate(email="alice@example.com", password="secret123"))
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.hashed_password != "secret123"


@pytest.mark.asyncio
async def test_create_duplicate_user_raises_conflict(session: AsyncSession):
    service = UserService(session)
    payload = UserCreate(email="bob@example.com", password="secret123")
    await service.create(payload)
    with pytest.raises(ConflictError):
        await service.create(payload)


@pytest.mark.asyncio
async def test_authenticate_success(session: AsyncSession):
    service = UserService(session)
    await service.create(UserCreate(email="carol@example.com", password="correct_password"))
    user = await service.authenticate("carol@example.com", "correct_password")
    assert user.email == "carol@example.com"


@pytest.mark.asyncio
async def test_authenticate_wrong_password(session: AsyncSession):
    service = UserService(session)
    await service.create(UserCreate(email="dave@example.com", password="correct_password"))
    with pytest.raises(UnauthorizedError):
        await service.authenticate("dave@example.com", "wrong_password")


@pytest.mark.asyncio
async def test_update_user(session: AsyncSession):
    service = UserService(session)
    user = await service.create(UserCreate(email="eve@example.com", password="secret123"))
    updated = await service.update(user.id, UserUpdate(full_name="Eve Smith"))
    assert updated.full_name == "Eve Smith"
