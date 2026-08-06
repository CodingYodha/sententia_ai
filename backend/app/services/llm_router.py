"""
Sententia.ai — LLM Router

Provider cascade for all LLM calls (Groq-first for reliability):
  1. Groq        — llama-3.3-70b-versatile  (primary  — fast, confirmed working)
  2. OpenRouter  — openai/gpt-oss-120b      (secondary — high quality)
  3. OpenRouter  — openai/gpt-oss-20b       (tertiary  — lighter fallback)
  4. Groq        — llama-3.1-8b-instant     (last Groq fallback — tiny but fast)
  5. Groq        — deepseek-r1-distill-llama-70b (reasoning fallback)

Key design decisions:
  - Groq async uses instructor.from_groq with TOOLS mode (not MD_JSON).
    MD_JSON mode depends on markdown parsing which is unreliable.
  - OpenRouter uses AsyncOpenAI with JSON mode.
  - All client construction is deferred to runtime (avoids startup crashes).

Two modes:
  - Sync  (get_llm_client)       — instructor_service (document intake)
  - Async (get_async_llm_cascade) — structure_service (generation engine)
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
    logger.warning("groq SDK not installed — Groq providers unavailable")

# ── Provider definitions ───────────────────────────────────────────────────────
_OPENROUTER_BASE = "https://openrouter.ai/api/v1"
_OPENROUTER_HEADERS = {
    "HTTP-Referer": "https://sententia.ai",
    "X-Title": "Sententia.ai",
}

_PROVIDERS = [
    # ── Groq TOOLS-mode models (support function calling) ────────────────────
    {"name": "groq_llama33_70b",   "model": "llama-3.3-70b-versatile",  "client_type": "groq", "mode": "TOOLS"},
    {"name": "groq_llama31_70b",   "model": "llama-3.1-70b-versatile",  "client_type": "groq", "mode": "TOOLS"},
    {"name": "groq_llama31_8b",    "model": "llama-3.1-8b-instant",     "client_type": "groq", "mode": "TOOLS"},
    # ── Groq MD_JSON-mode models (no function calling, text JSON output) ─────
    {"name": "groq_gpt_oss_120b",  "model": "openai/gpt-oss-120b",      "client_type": "groq", "mode": "MD_JSON"},
    {"name": "groq_gpt_oss_20b",   "model": "openai/gpt-oss-20b",       "client_type": "groq", "mode": "MD_JSON"},
]


@dataclass
class LLMClient:
    """Instructor-patched LLM client (sync or async) + metadata."""
    client: object
    model: str
    provider: str
    is_async: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# SYNC CLIENTS — instructor_service (document intake)
# ══════════════════════════════════════════════════════════════════════════════

def _make_sync_groq(api_key: str, mode: str = "TOOLS") -> object:
    """
    Sync Groq instructor client.
    TOOLS mode  — uses function-calling (reliable, default).
    MD_JSON mode — text JSON output (for models that don't support tool use).
    """
    raw = groq_sdk.Groq(api_key=api_key)
    instructor_mode = instructor.Mode.MD_JSON if mode == "MD_JSON" else instructor.Mode.TOOLS
    return instructor.from_groq(raw, mode=instructor_mode)


def _make_sync_openrouter(api_key: str) -> object:
    raw = openai.OpenAI(
        base_url=_OPENROUTER_BASE,
        api_key=api_key,
        default_headers=_OPENROUTER_HEADERS,
    )
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def get_llm_client() -> LLMClient | None:
    """
    Returns the first available sync Instructor client.
    Used by document intake pipeline (instructor_service).
    """
    if not _INSTRUCTOR_AVAILABLE:
        logger.warning("instructor not installed — sync LLM unavailable")
        return None

    from app.config import get_settings
    settings = get_settings()

    groq_key_set = bool(settings.groq_api_key)
    or_key_set   = bool(settings.openrouter_api_key)
    logger.info(
        f"Sync LLM keys: groq={'SET' if groq_key_set else 'MISSING'} "
        f"openrouter={'SET' if or_key_set else 'MISSING'} "
        f"groq_sdk={'OK' if _GROQ_AVAILABLE else 'NOT INSTALLED'}"
    )

    for p in _PROVIDERS:
        try:
            if p["client_type"] == "groq" and _GROQ_AVAILABLE and settings.groq_api_key:
                client = _make_sync_groq(settings.groq_api_key, mode=p.get("mode", "TOOLS"))
                logger.info(f"Sync LLM: using {p['name']} / {p['model']} ({p.get('mode', 'TOOLS')} mode)")
                return LLMClient(client=client, model=p["model"], provider=p["name"])
            elif p["client_type"] == "openai" and settings.openrouter_api_key:
                client = _make_sync_openrouter(settings.openrouter_api_key)
                logger.info(f"Sync LLM: using {p['name']} / {p['model']}")
                return LLMClient(client=client, model=p["model"], provider=p["name"])
        except Exception as e:
            logger.warning(f"Sync provider {p['name']} init failed: {type(e).__name__}: {e}")
            continue

    logger.error(
        "No sync LLM providers configured — "
        "set GROQ_API_KEY or OPENROUTER_API_KEY in environment"
    )
    return None


# ══════════════════════════════════════════════════════════════════════════════
# ASYNC CLIENTS — structure_service (generation engine)
# ══════════════════════════════════════════════════════════════════════════════

def _make_async_groq(api_key: str, mode: str = "TOOLS") -> object:
    """
    Async Groq instructor client.

    TOOLS mode  (default) — uses Groq's native function-calling API.
                            Reliable structured output. Use for models that
                            support tool use (llama-3.x, etc.).
    MD_JSON mode           — instructs model to output markdown-fenced JSON.
                            Use for models that don't support tool use
                            (e.g. openai/gpt-oss-120b on Groq).
    """
    raw = groq_sdk.AsyncGroq(api_key=api_key)
    instructor_mode = instructor.Mode.MD_JSON if mode == "MD_JSON" else instructor.Mode.TOOLS
    return instructor.from_groq(raw, mode=instructor_mode)


def _make_async_openrouter(api_key: str) -> object:
    """Async instructor client → OpenRouter (OpenAI-compatible)."""
    raw = openai.AsyncOpenAI(
        base_url=_OPENROUTER_BASE,
        api_key=api_key,
        default_headers=_OPENROUTER_HEADERS,
    )
    return instructor.from_openai(raw, mode=instructor.Mode.JSON)


def get_async_llm_cascade() -> list[LLMClient]:
    """
    Returns ALL available async Instructor clients in cascade priority order
    (Groq-first, then OpenRouter as last resort).

    The structure_service iterates this list; if a provider raises,
    the next is tried automatically.

    Returns empty list if no API keys are configured — caller must handle this.
    """
    if not _INSTRUCTOR_AVAILABLE:
        logger.error("instructor package not installed — async cascade is empty")
        return []

    from app.config import get_settings
    settings = get_settings()

    groq_key_set = bool(settings.groq_api_key)
    or_key_set   = bool(settings.openrouter_api_key)
    groq_sdk_ok  = _GROQ_AVAILABLE

    logger.info(
        "Async LLM cascade init: "
        f"groq_key={'SET' if groq_key_set else '*** MISSING ***'} | "
        f"groq_sdk={'OK' if groq_sdk_ok else '*** NOT INSTALLED ***'} | "
        f"openrouter_key={'SET' if or_key_set else 'MISSING'}"
    )

    cascade: list[LLMClient] = []

    for p in _PROVIDERS:
        try:
            if p["client_type"] == "groq" and groq_sdk_ok and settings.groq_api_key:
                cascade.append(LLMClient(
                    client=_make_async_groq(settings.groq_api_key, mode=p.get("mode", "TOOLS")),
                    model=p["model"], provider=p["name"], is_async=True,
                ))
                logger.debug(f"Cascade: added {p['name']} / {p['model']} ({p.get('mode', 'TOOLS')} mode)")
            elif p["client_type"] == "openai" and settings.openrouter_api_key:
                cascade.append(LLMClient(
                    client=_make_async_openrouter(settings.openrouter_api_key),
                    model=p["model"], provider=p["name"], is_async=True,
                ))
                logger.debug(f"Cascade: added {p['name']} / {p['model']}")
        except Exception as e:
            logger.warning(f"Async provider {p['name']} init failed: {type(e).__name__}: {e}")

    if not cascade:
        logger.error(
            "CRITICAL: Async LLM cascade is EMPTY — structure generation will fail! "
            f"groq_key={'SET' if groq_key_set else '*** MISSING ***'}, "
            f"groq_sdk={'OK' if groq_sdk_ok else '*** NOT INSTALLED ***'}, "
            f"openrouter_key={'SET' if or_key_set else 'MISSING'}. "
            "ACTION: Add GROQ_API_KEY to Render environment variables."
        )
    else:
        provider_names = [c.provider for c in cascade]
        logger.info(f"Async cascade ready ({len(cascade)} providers): {provider_names}")

    return cascade
