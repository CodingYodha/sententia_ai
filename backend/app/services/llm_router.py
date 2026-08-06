"""
Sententia.ai — LLM Router

Provider cascade for all LLM calls (Groq-first for reliability):
  1. Groq  — llama-3.3-70b-versatile      (primary  — fastest, free tier)
  2. Groq  — llama3-70b-8192             (secondary — fallback Groq model)
  3. Groq  — mixtral-8x7b-32768          (tertiary  — broad context)
  4. OpenRouter — nvidia/llama-3.1-nemotron-ultra-253b-v1:free (last resort)
  5. OpenRouter — nvidia/llama-3.3-nemotron-super-49b-v1:free  (last resort)

Two modes:
  - Sync  (get_llm_client)      — used by instructor_service (document intake)
  - Async (get_async_llm_cascade) — used by structure_service (generation engine)
    Returns ALL available async clients in cascade order so the caller
    can iterate and log which provider actually served the request.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Import flags ──────────────────────────────────────────────────────────────
try:
    import instructor
    import openai
    _INSTRUCTOR_AVAILABLE = True
except ImportError:
    _INSTRUCTOR_AVAILABLE = False
    logger.warning("instructor/openai not available — LLM structuring disabled")

try:
    import groq as groq_sdk
    _GROQ_AVAILABLE = True
except ImportError:
    _GROQ_AVAILABLE = False

# ── Provider definitions ───────────────────────────────────────────────────────
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://sententia.ai",
    "X-Title": "Sententia.ai",
}

_PROVIDERS = [
    # ── Groq first — reliable free tier, low latency ─────────────────────────
    {"name": "groq_llama33_70b",       "model": "llama-3.3-70b-versatile",  "client_type": "groq"},
    {"name": "groq_llama3_70b",        "model": "llama3-70b-8192",          "client_type": "groq"},
    {"name": "groq_mixtral",           "model": "mixtral-8x7b-32768",       "client_type": "groq"},
    # ── OpenRouter as last resort (free models can be slow / unavailable) ────
    {"name": "openrouter_nemotron_ultra", "model": "nvidia/llama-3.1-nemotron-ultra-253b-v1:free", "client_type": "openai"},
    {"name": "openrouter_nemotron_super", "model": "nvidia/llama-3.3-nemotron-super-49b-v1:free",  "client_type": "openai"},
]


@dataclass
class LLMClient:
    """Instructor-patched LLM client (sync or async) + metadata."""
    client: object
    model: str
    provider: str
    is_async: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# SYNC CLIENTS — used by instructor_service (document intake)
# ══════════════════════════════════════════════════════════════════════════════

def _make_sync_openrouter(api_key: str) -> object:
    raw = openai.OpenAI(
        base_url=_OPENROUTER_BASE,
        api_key=api_key,
        default_headers=_OPENROUTER_HEADERS,
    )
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def _make_sync_groq(api_key: str) -> object:
    raw = groq_sdk.Groq(api_key=api_key)
    return instructor.from_groq(raw, mode=instructor.Mode.MD_JSON)


def get_llm_client() -> LLMClient | None:
    """
    Returns the first available sync Instructor client.
    Used by document intake pipeline (instructor_service).
    """
    if not _INSTRUCTOR_AVAILABLE:
        return None

    from app.config import get_settings
    settings = get_settings()

    groq_key_set = bool(settings.groq_api_key)
    or_key_set   = bool(settings.openrouter_api_key)
    logger.info(f"Sync LLM keys: groq={'SET' if groq_key_set else 'MISSING'} openrouter={'SET' if or_key_set else 'MISSING'}")

    for p in _PROVIDERS:
        try:
            if p["client_type"] == "groq" and _GROQ_AVAILABLE and settings.groq_api_key:
                return LLMClient(
                    client=_make_sync_groq(settings.groq_api_key),
                    model=p["model"], provider=p["name"],
                )
            elif p["client_type"] == "openai" and settings.openrouter_api_key:
                return LLMClient(
                    client=_make_sync_openrouter(settings.openrouter_api_key),
                    model=p["model"], provider=p["name"],
                )
        except Exception as e:
            logger.warning(f"Sync provider {p['name']} init failed: {e}")
            continue

    logger.warning("No sync LLM providers configured — check GROQ_API_KEY / OPENROUTER_API_KEY env vars")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ASYNC CLIENTS — used by structure_service (generation engine)
# ══════════════════════════════════════════════════════════════════════════════

def _make_async_openrouter(api_key: str) -> object:
    """Async Instructor client backed by AsyncOpenAI → OpenRouter."""
    raw = openai.AsyncOpenAI(
        base_url=_OPENROUTER_BASE,
        api_key=api_key,
        default_headers=_OPENROUTER_HEADERS,
    )
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def _make_async_groq(api_key: str) -> object:
    """Async Instructor client backed by AsyncGroq."""
    raw = groq_sdk.AsyncGroq(api_key=api_key)
    return instructor.from_groq(raw, mode=instructor.Mode.MD_JSON)


def get_async_llm_cascade() -> list[LLMClient]:
    """
    Returns ALL available async Instructor clients in cascade priority order
    (Groq first, then OpenRouter as last resort).

    The structure_service iterates this list and logs which provider served
    each call. If a provider raises, the next is tried automatically.

    Returns empty list if no API keys are configured.
    """
    if not _INSTRUCTOR_AVAILABLE:
        logger.warning("instructor not available — async cascade empty")
        return []

    from app.config import get_settings
    settings = get_settings()

    groq_key_set = bool(settings.groq_api_key)
    or_key_set   = bool(settings.openrouter_api_key)
    groq_sdk_ok  = _GROQ_AVAILABLE
    logger.info(
        f"Async LLM cascade init: "
        f"groq_key={'SET' if groq_key_set else 'MISSING'} "
        f"groq_sdk={'OK' if groq_sdk_ok else 'NOT INSTALLED'} "
        f"openrouter_key={'SET' if or_key_set else 'MISSING'}"
    )

    cascade: list[LLMClient] = []

    for p in _PROVIDERS:
        try:
            if p["client_type"] == "groq" and groq_sdk_ok and settings.groq_api_key:
                cascade.append(LLMClient(
                    client=_make_async_groq(settings.groq_api_key),
                    model=p["model"], provider=p["name"], is_async=True,
                ))
            elif p["client_type"] == "openai" and settings.openrouter_api_key:
                cascade.append(LLMClient(
                    client=_make_async_openrouter(settings.openrouter_api_key),
                    model=p["model"], provider=p["name"], is_async=True,
                ))
        except Exception as e:
            logger.warning(f"Async provider {p['name']} init failed: {e}")

    if not cascade:
        logger.error(
            "CRITICAL: No async LLM providers available! "
            f"groq_key={'SET' if groq_key_set else 'MISSING'}, "
            f"groq_sdk={'OK' if groq_sdk_ok else 'NOT INSTALLED'}, "
            f"openrouter_key={'SET' if or_key_set else 'MISSING'}. "
            "Set GROQ_API_KEY in Render environment variables."
        )
    else:
        logger.info(f"Async cascade ready: {[c.provider for c in cascade]}")

    return cascade
