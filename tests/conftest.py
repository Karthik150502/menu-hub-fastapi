"""
Shared pytest fixtures for unit and integration tests.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base, get_db
from app.db.supabase import get_anon_client, get_service_client
from app.main import app
from tests.fake_supabase import FakeSupabaseClient

# ── In-memory SQLite — still backs the SQLAlchemy-based endpoints (restaurants) ─
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def session():
    async with TestSessionLocal() as s:
        yield s
        await s.rollback()


@pytest.fixture
def fake_supabase() -> FakeSupabaseClient:
    """In-memory stand-in for both Supabase clients — auth-backed endpoints
    (register/login/me/users) run against this instead of a real project."""
    return FakeSupabaseClient()


@pytest_asyncio.fixture
async def client(session: AsyncSession, fake_supabase: FakeSupabaseClient):
    async def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_anon_client] = lambda: fake_supabase
    app.dependency_overrides[get_service_client] = lambda: fake_supabase
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
