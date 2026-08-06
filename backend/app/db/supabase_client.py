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


import asyncio


def _sync_ping_supabase() -> bool:
    """Synchronous network check — executed in background thread."""
    settings = get_settings()

    if not settings.supabase_url or not settings.supabase_service_role_key:
        return False

    # Strategy 1: firm_workspaces table query
    try:
        client = get_supabase_client()
        client.table("firm_workspaces").select("id").limit(1).execute()
        return True
    except Exception:
        pass

    # Strategy 2: users table query
    try:
        client = get_supabase_client()
        client.table("users").select("id").limit(1).execute()
        return True
    except Exception:
        pass

    # Strategy 3: HTTP REST API reachability
    try:
        import httpx
        url = settings.supabase_url.rstrip("/") + "/rest/v1/"
        headers = {
            "apikey": settings.supabase_service_role_key,
            "Authorization": f"Bearer {settings.supabase_service_role_key}",
        }
        r = httpx.get(url, headers=headers, timeout=2.0)
        return r.status_code < 500
    except Exception:
        return False


async def ping_supabase() -> bool:
    """Non-blocking Supabase ping — times out after 2.5s max to avoid blocking Uvicorn."""
    try:
        return await asyncio.wait_for(asyncio.to_thread(_sync_ping_supabase), timeout=2.5)
    except Exception:
        return False
