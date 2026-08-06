"""
Sententia.ai — LLM Router

Provider cascade (gpt-oss-120b primary, per user preference):
  1. Groq OpenAI-compat — openai/gpt-oss-120b     (primary  — user selected)
  2. Groq OpenAI-compat — openai/gpt-oss-20b      (secondary)
  3. Groq TOOLS         — llama-3.3-70b-versatile  (confirmed working fallback)
  4. Groq TOOLS         — llama-3.1-8b-instant     (small fast fallback)

Client strategy per model type:
  - Models that support function-calling (llama-3.x):
      instructor.from_groq(AsyncGroq(...), mode=TOOLS)
  - Models that DON'T support function-calling (gpt-oss-*):
      instructor.from_openai(AsyncOpenAI(base_url=GROQ_OPENAI_BASE), mode=JSON)
      Groq exposes an OpenAI-compatible endpoint at https://api.groq.com/openai/v1
      that handles all models. JSON mode works for non-tool-use models.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Import flags ───────────────────────────────────────────────────────────────
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
    logger.warning("groq SDK not installed — Groq TOOLS providers unavailable")

# ── Endpoints ──────────────────────────────────────────────────────────────────
_GROQ_OPENAI_BASE   = "https://api.groq.com/openai/v1"   # OpenAI-compat endpoint
_OPENROUTER_BASE    = "https://openrouter.ai/api/v1"
_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://sententia.ai",
    "X-Title":      "Sententia.ai",
}

# ── Provider definitions ───────────────────────────────────────────────────────
# client_type:
#   "groq_openai"  → AsyncOpenAI pointed at Groq's OpenAI-compat endpoint (JSON mode)
#                    Use for: gpt-oss-* and any model without tool-use support
#   "groq"         → instructor.from_groq(AsyncGroq) with TOOLS mode
#                    Use for: llama-3.x models with native function-calling
#   "openai"       → AsyncOpenAI pointed at OpenRouter
_PROVIDERS = [
    {"name": "groq_llama33_70b",           "model": "llama-3.3-70b-versatile",              "client_type": "groq_openai"},
    {"name": "openrouter_nemotron_3_super", "model": "nvidia/nemotron-3-super-120b-a12b:free", "client_type": "openai"},
    {"name": "openrouter_gemma_4_31b",     "model": "google/gemma-4-31b-it:free",          "client_type": "openai"},
    {"name": "groq_llama31_8b",            "model": "llama-3.1-8b-instant",                "client_type": "groq_openai"},
]


@dataclass
class LLMClient:
    """Instructor-patched LLM client (sync or async) + metadata."""
    client: object
    model:    str
    provider: str
    is_async: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# Client factories
# ══════════════════════════════════════════════════════════════════════════════

def _make_groq_openai_sync(api_key: str) -> object:
    """Sync: Groq OpenAI-compat endpoint → instructor JSON mode."""
    raw = openai.OpenAI(base_url=_GROQ_OPENAI_BASE, api_key=api_key)
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def _make_groq_openai_async(api_key: str) -> object:
    """Async: Groq OpenAI-compat endpoint → instructor JSON mode."""
    raw = openai.AsyncOpenAI(base_url=_GROQ_OPENAI_BASE, api_key=api_key)
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def _make_groq_tools_sync(api_key: str) -> object:
    """Sync: Groq native SDK → instructor TOOLS mode (function-calling)."""
    raw = groq_sdk.Groq(api_key=api_key)
    return instructor.from_groq(raw, mode=instructor.Mode.TOOLS)


def _make_groq_tools_async(api_key: str) -> object:
    """Async: Groq native SDK → instructor TOOLS mode (function-calling)."""
    raw = groq_sdk.AsyncGroq(api_key=api_key)
    return instructor.from_groq(raw, mode=instructor.Mode.TOOLS)


def _make_openrouter_sync(api_key: str) -> object:
    raw = openai.OpenAI(
        base_url=_OPENROUTER_BASE,
        api_key=api_key,
        default_headers=_OPENROUTER_HEADERS,
    )
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def _make_openrouter_async(api_key: str) -> object:
    raw = openai.AsyncOpenAI(
        base_url=_OPENROUTER_BASE,
        api_key=api_key,
        default_headers=_OPENROUTER_HEADERS,
    )
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


# ══════════════════════════════════════════════════════════════════════════════
# SYNC — instructor_service (document intake)
# ══════════════════════════════════════════════════════════════════════════════

def get_llm_client() -> LLMClient | None:
    """Returns the first available sync Instructor client."""
    if not _INSTRUCTOR_AVAILABLE:
        return None

    from app.config import get_settings
    settings = get_settings()

    logger.info(
        f"Sync LLM init: groq_key={'SET' if settings.groq_api_key else 'MISSING'} "
        f"groq_sdk={'OK' if _GROQ_AVAILABLE else 'NOT INSTALLED'}"
    )

    for p in _PROVIDERS:
        try:
            ct = p["client_type"]
            if ct == "groq_openai" and settings.groq_api_key:
                client = _make_groq_openai_sync(settings.groq_api_key)
                logger.info(f"Sync LLM: {p['name']} / {p['model']} (groq openai-compat)")
                return LLMClient(client=client, model=p["model"], provider=p["name"])
            elif ct == "groq" and _GROQ_AVAILABLE and settings.groq_api_key:
                client = _make_groq_tools_sync(settings.groq_api_key)
                logger.info(f"Sync LLM: {p['name']} / {p['model']} (groq tools)")
                return LLMClient(client=client, model=p["model"], provider=p["name"])
            elif ct == "openai" and settings.openrouter_api_key:
                client = _make_openrouter_sync(settings.openrouter_api_key)
                logger.info(f"Sync LLM: {p['name']} / {p['model']} (openrouter)")
                return LLMClient(client=client, model=p["model"], provider=p["name"])
        except Exception as e:
            logger.warning(f"Sync provider {p['name']} init failed: {type(e).__name__}: {e}")
            continue

    logger.error("No sync LLM providers available — set GROQ_API_KEY or OPENROUTER_API_KEY in environment")
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ASYNC — structure_service (generation engine)
# ══════════════════════════════════════════════════════════════════════════════

def get_async_llm_cascade() -> list[LLMClient]:
    """
    Returns ALL available async Instructor clients in cascade priority order.

    gpt-oss-120b is primary (user preference). Each client is built with the
    correct backend for its model type. Returns empty list if no keys configured.
    """
    if not _INSTRUCTOR_AVAILABLE:
        logger.error("instructor not installed — async cascade empty")
        return []

    from app.config import get_settings
    settings = get_settings()

    groq_key  = settings.groq_api_key
    or_key    = settings.openrouter_api_key

    logger.info(
        "Async LLM cascade init: "
        f"groq_key={'SET' if groq_key else '*** MISSING ***'} | "
        f"groq_sdk={'OK' if _GROQ_AVAILABLE else '*** NOT INSTALLED ***'} | "
        f"openrouter_key={'SET' if or_key else 'MISSING'}"
    )

    cascade: list[LLMClient] = []

    for p in _PROVIDERS:
        ct = p["client_type"]
        try:
            if ct == "groq_openai" and groq_key:
                # Use Groq's OpenAI-compatible endpoint — works for gpt-oss models
                cascade.append(LLMClient(
                    client=_make_groq_openai_async(groq_key),
                    model=p["model"], provider=p["name"], is_async=True,
                ))
                logger.info(f"Cascade +{p['name']} ({p['model']}, groq-openai-compat/JSON)")

            elif ct == "groq" and _GROQ_AVAILABLE and groq_key:
                # Native Groq SDK with TOOLS mode (function-calling)
                cascade.append(LLMClient(
                    client=_make_groq_tools_async(groq_key),
                    model=p["model"], provider=p["name"], is_async=True,
                ))
                logger.info(f"Cascade +{p['name']} ({p['model']}, groq-native/TOOLS)")

            elif ct == "openai" and or_key:
                cascade.append(LLMClient(
                    client=_make_openrouter_async(or_key),
                    model=p["model"], provider=p["name"], is_async=True,
                ))
                logger.info(f"Cascade +{p['name']} ({p['model']}, openrouter/JSON)")

        except Exception as e:
            logger.warning(f"Async provider {p['name']} init failed: {type(e).__name__}: {e}")

    if not cascade:
        logger.error(
            "CRITICAL: Async cascade EMPTY — structure generation will fail! "
            f"groq_key={'SET' if groq_key else '*** MISSING ***'}, "
            f"groq_sdk={'OK' if _GROQ_AVAILABLE else '*** NOT INSTALLED ***'}. "
            "ACTION: Verify GROQ_API_KEY in Render environment variables."
        )
    else:
        logger.info(f"Async cascade ready ({len(cascade)}): {[c.provider for c in cascade]}")

    return cascade
