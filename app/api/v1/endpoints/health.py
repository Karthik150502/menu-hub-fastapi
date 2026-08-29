"""
Health & readiness endpoints — used by load balancers and k8s probes.
"""
from datetime import datetime

from fastapi import APIRouter

from app.api.deps import ServiceSupabase

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
async def liveness() -> dict:
    now = datetime.now()
    """Liveness probe — always returns 200 if the process is up."""
    return {"status": "ok","time": now.strftime("%S-%M-%H:%d-%m-%Y")}


@router.get("/health/ready", include_in_schema=False)
async def readiness(client: ServiceSupabase) -> dict:
    """Readiness probe — checks Supabase connectivity."""
    try:
        await client.table("currencies").select("code").limit(1).execute()
        db_ok = True
    except Exception:
        db_ok = False

    status = "ready" if db_ok else "degraded"
    return {"status": status, "db": "ok" if db_ok else "error"}
