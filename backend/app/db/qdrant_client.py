"""
Sententia.ai — Qdrant client singleton.
Use get_qdrant_client() everywhere — never instantiate directly.
"""

from functools import lru_cache
from qdrant_client import QdrantClient
from qdrant_client.http.exceptions import UnexpectedResponse
from app.config import get_settings

# The single collection used for the regulatory/legal corpus
LEGAL_CORPUS_COLLECTION = "sententia_legal_corpus"


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """
    Returns a cached Qdrant client connected to Qdrant Cloud.
    Falls back to in-memory mode if no URL is configured (useful for local dev).
    """
    settings = get_settings()

    if not settings.qdrant_url:
        # Local / in-memory fallback for development without a cloud cluster
        return QdrantClient(":memory:")

    return QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key,
    )


import asyncio


def _sync_ping_qdrant() -> bool:
    """Synchronous network check — executed in background thread."""
    try:
        client = get_qdrant_client()
        client.get_collections()
        return True
    except Exception:
        return False


async def ping_qdrant() -> bool:
    """Non-blocking Qdrant ping — times out after 2.5s max to avoid blocking Uvicorn."""
    try:
        return await asyncio.wait_for(asyncio.to_thread(_sync_ping_qdrant), timeout=2.5)
    except Exception:
        return False
