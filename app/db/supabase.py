"""
Supabase client — two flavours:
  • anon_client  : respects Row Level Security (use for user-scoped operations)
  • service_client: bypasses RLS (use only in trusted server-side logic)
"""
from functools import lru_cache
from supabase import AsyncClient, acreate_client
from app.core.config import settings


@lru_cache
async def get_anon_client() -> AsyncClient:
    return await acreate_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)


@lru_cache
async def get_service_client() -> AsyncClient:
    return await acreate_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
