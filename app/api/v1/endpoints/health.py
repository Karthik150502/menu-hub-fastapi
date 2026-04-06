"""
Health & readiness endpoints — used by load balancers and k8s probes.
"""
from fastapi import APIRouter
from sqlalchemy import text

from app.db.session import AsyncSessionLocal

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
async def liveness() -> dict:
    """Liveness probe — always returns 200 if the process is up."""
    return {"status": "ok"}


@router.get("/health/ready", include_in_schema=False)
async def readiness() -> dict:
    """Readiness probe — checks DB connectivity."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    status = "ready" if db_ok else "degraded"
    return {"status": status, "db": "ok" if db_ok else "error"}
