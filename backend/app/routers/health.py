"""
Sententia.ai — /health router
Returns service status including Supabase + Qdrant connectivity.
"""

import asyncio
from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel
from app.config import get_settings
from app.db.supabase_client import ping_supabase
from app.db.qdrant_client import ping_qdrant


router = APIRouter(tags=["Health"])


class ServiceStatus(BaseModel):
    status: str          # "ok" | "error"
    latency_ms: float | None = None


class HealthResponse(BaseModel):
    status: str          # "ok" | "degraded"
    version: str
    timestamp: str
    services: dict[str, ServiceStatus]


@router.get("/health", response_model=HealthResponse, summary="Health check")
async def health_check() -> HealthResponse:
    """
    Returns the operational status of Sententia.ai and its upstream services.

    - **status**: `ok` if all services reachable, `degraded` if any are down.
    - **services.supabase**: connectivity to the Supabase Postgres instance.
    - **services.qdrant**: connectivity to the Qdrant vector DB cluster.
    """
    settings = get_settings()

    # Run both pings concurrently
    t0 = asyncio.get_event_loop().time()
    supabase_ok, qdrant_ok = await asyncio.gather(
        ping_supabase(),
        ping_qdrant(),
    )
    elapsed = (asyncio.get_event_loop().time() - t0) * 1000  # ms

    overall = "ok" if (supabase_ok and qdrant_ok) else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.app_version,
        timestamp=datetime.now(timezone.utc).isoformat(),
        services={
            "supabase": ServiceStatus(
                status="ok" if supabase_ok else "error",
                latency_ms=round(elapsed, 2),
            ),
            "qdrant": ServiceStatus(
                status="ok" if qdrant_ok else "error",
                latency_ms=round(elapsed, 2),
            ),
        },
    )
