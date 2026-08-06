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


@router.get("/debug/env", summary="Check which env vars are set (values masked)")
async def debug_env() -> dict:
    """
    Shows SET / MISSING for every critical env var — values are never exposed.
    Use this to diagnose missing secrets on Render / HF Spaces.
    """
    import os

    def _status(val: str) -> str:
        if not val:
            return "MISSING ❌"
        masked = val[:8] + "..." + val[-4:] if len(val) > 12 else "***"
        return f"SET ✅ ({masked})"

    settings = get_settings()

    return {
        "supabase_url":              _status(settings.supabase_url),
        "supabase_service_role_key": _status(settings.supabase_service_role_key),
        "supabase_anon_key":         _status(settings.supabase_anon_key),
        "supabase_jwt_secret":       _status(settings.supabase_jwt_secret),
        "qdrant_url":                _status(settings.qdrant_url),
        "qdrant_api_key":            _status(settings.qdrant_api_key),
        "groq_api_key":              _status(settings.groq_api_key),
        "openrouter_api_key":        _status(settings.openrouter_api_key),
        "jina_api_key":              _status(settings.jina_api_key),
        # Raw env var names (what Render might have set)
        "_raw_SUPABASE_SERVICE_KEY":      _status(os.environ.get("SUPABASE_SERVICE_KEY", "")),
        "_raw_SUPABASE_SERVICE_ROLE_KEY": _status(os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")),
        "_raw_SUPABASE_URL":              _status(os.environ.get("SUPABASE_URL", "")),
    }


@router.get("/debug/llm-test", summary="Test Groq LLM connection with a real API call")
async def debug_llm_test() -> dict:
    """
    Makes a real (minimal) call to the configured LLM providers and reports
    exactly which ones succeeded and which failed, with full error messages.
    Use this to diagnose 'All providers exhausted' issues on Render.
    """
    import asyncio as _asyncio
    from app.services.llm_router import get_async_llm_cascade, _GROQ_AVAILABLE, _INSTRUCTOR_AVAILABLE
    from app.config import get_settings

    settings = get_settings()

    results = {
        "instructor_available": _INSTRUCTOR_AVAILABLE,
        "groq_sdk_available": _GROQ_AVAILABLE,
        "groq_key_set": bool(settings.groq_api_key),
        "openrouter_key_set": bool(settings.openrouter_api_key),
        "providers_tested": [],
    }

    cascade = get_async_llm_cascade()
    results["cascade_length"] = len(cascade)
    results["cascade_providers"] = [c.provider for c in cascade]

    if not cascade:
        results["verdict"] = "FAIL — cascade is empty (no API keys or SDK missing)"
        return results

    # Test each provider with a tiny prompt
    for llm in cascade:
        entry: dict = {"provider": llm.provider, "model": llm.model}
        try:
            from pydantic import BaseModel
            class _Ping(BaseModel):
                reply: str

            resp = await _asyncio.wait_for(
                llm.client.chat.completions.create(
                    model=llm.model,
                    response_model=_Ping,
                    max_tokens=30,
                    messages=[{"role": "user", "content": "Reply with the word OK."}],
                ),
                timeout=15.0,
            )
            entry["status"] = "OK"
            entry["reply"] = resp.reply
        except _asyncio.TimeoutError:
            entry["status"] = "TIMEOUT (>15s)"
        except Exception as e:
            entry["status"] = f"ERROR: {type(e).__name__}: {str(e)[:400]}"

        results["providers_tested"].append(entry)

    successes = [e for e in results["providers_tested"] if e.get("status") == "OK"]
    results["verdict"] = (
        f"OK — {len(successes)}/{len(cascade)} providers working"
        if successes else
        "FAIL — all providers returned errors (see providers_tested for details)"
    )
    return results
