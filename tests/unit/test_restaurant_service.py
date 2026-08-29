"""
Unit tests for RestaurantService business logic.
These run against a fake in-memory Supabase client — no network required.
"""
import uuid

import pytest

from app.core.exceptions import ForbiddenError, NotFoundError
from app.schemas.restaurant import RestaurantCreate, RestaurantUpdate
from app.services.restaurant_service import RestaurantService
from tests.fake_supabase import FakeSupabaseClient


@pytest.mark.asyncio
async def test_create_and_get_restaurant(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    service = RestaurantService(fake_supabase)
    created = await service.create(owner_id, RestaurantCreate(name="Test Diner"))
    assert created["name"] == "Test Diner"
    assert created["owner_id"] == str(owner_id)

    fetched = await service.get(uuid.UUID(created["id"]))
    assert fetched["name"] == "Test Diner"


@pytest.mark.asyncio
async def test_get_missing_restaurant_raises_not_found(fake_supabase: FakeSupabaseClient):
    with pytest.raises(NotFoundError):
        await RestaurantService(fake_supabase).get(uuid.uuid4())


@pytest.mark.asyncio
async def test_list_by_owner(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    service = RestaurantService(fake_supabase)
    await service.create(owner_id, RestaurantCreate(name="Mine"))
    await service.create(other_id, RestaurantCreate(name="Not mine"))

    mine = await service.list_by_owner(owner_id)
    assert [r["name"] for r in mine] == ["Mine"]


@pytest.mark.asyncio
async def test_update_by_owner_succeeds(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    service = RestaurantService(fake_supabase)
    created = await service.create(owner_id, RestaurantCreate(name="Old Name"))

    updated = await service.update(
        uuid.UUID(created["id"]), owner_id, RestaurantUpdate(name="New Name")
    )
    assert updated["name"] == "New Name"


@pytest.mark.asyncio
async def test_update_by_non_owner_raises_forbidden(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    service = RestaurantService(fake_supabase)
    created = await service.create(owner_id, RestaurantCreate(name="Old Name"))

    with pytest.raises(ForbiddenError):
        await service.update(uuid.UUID(created["id"]), other_id, RestaurantUpdate(name="Hijacked"))


@pytest.mark.asyncio
async def test_delete_by_owner_removes_it(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    service = RestaurantService(fake_supabase)
    created = await service.create(owner_id, RestaurantCreate(name="Gone Soon"))

    await service.delete(uuid.UUID(created["id"]), owner_id)
    with pytest.raises(NotFoundError):
        await service.get(uuid.UUID(created["id"]))


@pytest.mark.asyncio
async def test_delete_by_non_owner_raises_forbidden(fake_supabase: FakeSupabaseClient):
    owner_id = uuid.uuid4()
    other_id = uuid.uuid4()
    service = RestaurantService(fake_supabase)
    created = await service.create(owner_id, RestaurantCreate(name="Stays"))

    with pytest.raises(ForbiddenError):
        await service.delete(uuid.UUID(created["id"]), other_id)
