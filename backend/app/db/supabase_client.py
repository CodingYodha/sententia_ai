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
    For client-facing operations, use the anon key.
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
    Lightweight connectivity check — queries the users table count.
    Returns True if reachable, False otherwise.
    """
    try:
        client = get_supabase_client()
        # A simple count query — fast and non-destructive
        client.table("users").select("id", count="exact").limit(1).execute()
        return True
    except Exception:
        return False
