"""
Sententia.ai — Embedding Service

Provider cascade:
  1. Jina Embeddings v3 (primary)  — 768-dim via Matryoshka truncation
  2. Google text-embedding-004 (fallback) — 768-dim natively

Both produce 768-dim vectors so the same Qdrant collection is used throughout.

Jina v3 supports task-specific embeddings:
  - "retrieval.passage" for document ingestion
  - "retrieval.query" for query-time embedding

Rate limits handled via exponential backoff.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Literal

import httpx

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────────────────
VECTOR_DIM = 768            # standardized across Jina (Matryoshka) and Google
_JINA_URL  = "https://api.jina.ai/v1/embeddings"
_GOOGLE_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"

_MAX_BATCH_SIZE = 32        # Jina: max 2048 tokens per item, up to 1M tokens/request
_MAX_RETRIES    = 3
_BACKOFF_BASE   = 1.5       # seconds


# ── Retry helper ───────────────────────────────────────────────────────────────

async def _with_retry(coro_factory, max_retries: int = _MAX_RETRIES):
    """
    Execute an async coroutine with exponential backoff.
    coro_factory is a callable that returns a fresh coroutine on each call.
    """
    last_exc = None
    for attempt in range(max_retries):
        try:
            return await coro_factory()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                wait = _BACKOFF_BASE ** (attempt + 1)
                logger.warning(f"Rate limited — waiting {wait:.1f}s (attempt {attempt+1}/{max_retries})")
                await asyncio.sleep(wait)
                last_exc = e
            else:
                raise
        except (httpx.ConnectError, httpx.TimeoutException) as e:
            wait = _BACKOFF_BASE ** (attempt + 1)
            logger.warning(f"Connection error — waiting {wait:.1f}s (attempt {attempt+1}/{max_retries}): {e}")
            await asyncio.sleep(wait)
            last_exc = e
    raise RuntimeError(f"All {max_retries} attempts failed") from last_exc


# ── Jina Embeddings v3 ─────────────────────────────────────────────────────────

async def _embed_jina_batch(
    texts: list[str],
    api_key: str,
    task: Literal["retrieval.passage", "retrieval.query"] = "retrieval.passage",
    client: httpx.AsyncClient | None = None,
) -> list[list[float]]:
    """Embed a single batch via Jina API."""
    async def _call():
        async with (client or httpx.AsyncClient(timeout=60.0)) as c:
            response = await c.post(
                _JINA_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "jina-embeddings-v3",
                    "input": texts,
                    "dimensions": VECTOR_DIM,
                    "task": task,
                    "late_chunking": False,
                },
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    return await _with_retry(_call)


async def embed_jina(
    texts: list[str],
    api_key: str,
    task: Literal["retrieval.passage", "retrieval.query"] = "retrieval.passage",
) -> list[list[float]]:
    """
    Embed texts using Jina v3, batching in groups of _MAX_BATCH_SIZE.
    Returns list of 768-dim float vectors in the same order as input.
    """
    if not texts:
        return []

    results: list[list[float]] = []
    async with httpx.AsyncClient(timeout=60.0) as client:
        for i in range(0, len(texts), _MAX_BATCH_SIZE):
            batch = texts[i : i + _MAX_BATCH_SIZE]
            batch_embeddings = await _embed_jina_batch(batch, api_key, task, client)
            results.extend(batch_embeddings)
            if i + _MAX_BATCH_SIZE < len(texts):
                await asyncio.sleep(0.1)  # polite pacing

    return results


# ── Google text-embedding-004 ──────────────────────────────────────────────────

async def _embed_google_single(text: str, api_key: str) -> list[float]:
    """Embed a single text via Google text-embedding-004 REST API."""
    async def _call():
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                _GOOGLE_URL,
                params={"key": api_key},
                json={
                    "model": "models/text-embedding-004",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": VECTOR_DIM,
                },
            )
            response.raise_for_status()
            return response.json()["embedding"]["values"]

    return await _with_retry(_call)


async def embed_google(
    texts: list[str],
    api_key: str,
) -> list[list[float]]:
    """
    Embed texts using Google text-embedding-004.
    Google API processes one text per request — sequential with rate-limit pacing.
    """
    if not texts:
        return []

    results: list[list[float]] = []
    for i, text in enumerate(texts):
        vec = await _embed_google_single(text, api_key)
        results.append(vec)
        if i < len(texts) - 1:
            await asyncio.sleep(0.05)  # ~20 req/s pacing

    return results


# ── Unified embedding entry point ─────────────────────────────────────────────

async def embed_texts(
    texts: list[str],
    task: Literal["retrieval.passage", "retrieval.query"] = "retrieval.passage",
) -> tuple[list[list[float]], str]:
    """
    Embed texts using the provider cascade:
      1. Jina v3 (primary)
      2. Google text-embedding-004 (fallback)

    Returns:
        (vectors, provider_name)
        vectors: list of VECTOR_DIM-dimensional float lists
        provider_name: "jina" or "google"

    Raises:
        RuntimeError if both providers fail.
    """
    from app.config import get_settings
    settings = get_settings()

    # ── Try Jina ──────────────────────────────────────────────────────────────
    if settings.jina_api_key:
        try:
            logger.info(f"Embedding {len(texts)} texts via Jina v3 (task={task})")
            vectors = await embed_jina(texts, settings.jina_api_key, task)
            return vectors, "jina"
        except Exception as e:
            logger.warning(f"Jina embedding failed: {e} — falling back to Google")

    # ── Fallback: Google ──────────────────────────────────────────────────────
    if settings.google_api_key:
        try:
            logger.info(f"Embedding {len(texts)} texts via Google text-embedding-004")
            vectors = await embed_google(texts, settings.google_api_key)
            return vectors, "google"
        except Exception as e:
            logger.error(f"Google embedding fallback also failed: {e}")
            raise RuntimeError(f"All embedding providers failed. Last error: {e}") from e

    raise RuntimeError(
        "No embedding API keys configured. Set JINA_API_KEY or GOOGLE_API_KEY in .env"
    )


async def embed_query(query: str) -> tuple[list[float], str]:
    """
    Embed a single query string with retrieval.query task type.
    Optimized for asymmetric retrieval (query vs passage embeddings differ).
    """
    vectors, provider = await embed_texts([query], task="retrieval.query")
    return vectors[0], provider
