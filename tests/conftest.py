"""
Shared pytest fixtures for unit and integration tests.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.db.supabase import get_anon_client, get_service_client
from app.main import app
from tests.fake_supabase import FakeSupabaseClient


@pytest.fixture
def fake_supabase() -> FakeSupabaseClient:
    """In-memory stand-in for both Supabase clients — every endpoint in
    this app runs against this instead of a real project in tests."""
    return FakeSupabaseClient()


@pytest_asyncio.fixture
async def client(fake_supabase: FakeSupabaseClient):
    app.dependency_overrides[get_anon_client] = lambda: fake_supabase
    app.dependency_overrides[get_service_client] = lambda: fake_supabase
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
