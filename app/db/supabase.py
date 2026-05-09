"""
Supabase singleton clients — two flavours:
  • anon_client    : respects Row Level Security (use for user-scoped operations)
  • service_client : bypasses RLS (use only in trusted server-side logic)

Clients are initialized once at app startup via init_supabase_clients()
and torn down via close_supabase_clients() — both wired into the lifespan.

Usage in route handlers:
    from app.api.deps import AnonSupabase, ServiceSupabase

    async def my_route(db: AnonSupabase): ...
"""
from supabase import AsyncClient, acreate_client

from app.core.config import settings

_anon_client: AsyncClient | None = None
_service_client: AsyncClient | None = None


async def init_supabase_clients() -> None:
    global _anon_client, _service_client
    _anon_client = await acreate_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    _service_client = await acreate_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)


async def close_supabase_clients() -> None:
    global _anon_client, _service_client
    _anon_client = None
    _service_client = None


def get_anon_client() -> AsyncClient:
    if _anon_client is None:
        raise RuntimeError("Supabase anon client not initialized — call init_supabase_clients() first.")
    return _anon_client


def get_service_client() -> AsyncClient:
    if _service_client is None:
        raise RuntimeError("Supabase service client not initialized — call init_supabase_clients() first.")
    return _service_client
