"""
Sententia.ai — Supabase client singleton.
Use get_supabase_client() everywhere — never instantiate directly.
"""

from __future__ import annotations
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

try:
    from supabase import create_client, Client as SupabaseClient
    _SUPABASE_AVAILABLE = True
except ImportError:
    _SUPABASE_AVAILABLE = False
    SupabaseClient = object  # type: ignore
    logger.warning("supabase package not installed — Supabase features disabled")

from app.config import get_settings


@lru_cache
def get_supabase_client() -> SupabaseClient:
    """
    Returns a cached Supabase client using the service-role key.
    The service-role key bypasses RLS — use ONLY in backend/server contexts.
    """
    if not _SUPABASE_AVAILABLE:
        raise RuntimeError("supabase package not installed")
    settings = get_settings()
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_role_key,
    )


async def ping_supabase() -> bool:
    """
    Lightweight connectivity check — tries 3 strategies in order.
    Logs the actual exception so it appears in Render logs.
    """
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_service_role_key:
        logger.error(
            "Supabase ping skipped — SUPABASE_URL or SUPABASE_SERVICE_KEY not set. "
            f"url={'SET' if settings.supabase_url else 'MISSING'} "
            f"key={'SET' if settings.supabase_service_role_key else 'MISSING'}"
        )
        return False

    # Strategy 1: firm_workspaces table query
    try:
        client = get_supabase_client()
        client.table("firm_workspaces").select("id").limit(1).execute()
        logger.info("Supabase ping OK via firm_workspaces query")
        return True
    except Exception as e1:
        logger.warning(f"Supabase firm_workspaces ping failed: {type(e1).__name__}: {e1}")

    # Strategy 2: users table query
    try:
        client = get_supabase_client()
        client.table("users").select("id").limit(1).execute()
        logger.info("Supabase ping OK via users query")
        return True
    except Exception as e2:
        logger.warning(f"Supabase users ping failed: {type(e2).__name__}: {e2}")

    # Strategy 3: HTTP REST API reachability (no table needed)
    try:
        import httpx
        url = settings.supabase_url.rstrip("/") + "/rest/v1/"
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }
        async with httpx.AsyncClient(timeout=10) as http:
            r = await http.get(url, headers=headers)
        if r.status_code < 500:
            logger.info(f"Supabase REST reachable (HTTP {r.status_code}) — tables may not exist yet")
            return True
        logger.error(f"Supabase REST returned HTTP {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e3:
        logger.error(f"Supabase HTTP ping failed: {type(e3).__name__}: {e3}")
        return False
