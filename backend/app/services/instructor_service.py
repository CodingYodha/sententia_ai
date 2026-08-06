"""
Sententia.ai — Instructor Structuring Service

Takes raw extracted document text and uses Instructor + LLM to produce
validated Pydantic schema instances (UBOInfo, list[EquityStake], ControlRights).

Design:
  - Each schema is extracted with a dedicated focused prompt
  - Max 3 retries per schema (Instructor's built-in validation retry)
  - If no LLM client available, returns None for all schemas (graceful no-LLM mode)
  - On LLM error, logs and returns None — never raises to the caller
"""

from __future__ import annotations

import logging
from typing import TypeVar

from app.schemas.intake import UBOInfo, EquityStake, ControlRights
from app.services.llm_router import get_llm_client, LLMClient

logger = logging.getLogger(__name__)

T = TypeVar("T")

# ── Max tokens for extraction calls ───────────────────────────────────────────
_MAX_TOKENS = 2048

# ── Truncate input text to avoid context overflow ─────────────────────────────
_MAX_INPUT_CHARS = 12_000   # ~3k tokens; enough for most legal docs


def _truncate(text: str) -> str:
    if len(text) > _MAX_INPUT_CHARS:
        return text[:_MAX_INPUT_CHARS] + "\n\n[... document truncated for extraction ...]"
    return text


def _extract_schema(
    llm: LLMClient,
    schema_class: type[T],
    system_prompt: str,
    user_prompt: str,
    max_retries: int = 3,
) -> T | None:
    """Generic Instructor extraction call with retry and error handling."""
    try:
        result = llm.client.chat.completions.create(
            model=llm.model,
            response_model=schema_class,
            max_retries=max_retries,
            max_tokens=_MAX_TOKENS,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ],
        )
        return result
    except Exception as e:
        logger.warning(f"Instructor extraction failed for {schema_class.__name__}: {e}")
        return None


# ── System prompts ─────────────────────────────────────────────────────────────

_SYSTEM_UBO = """You are a legal document analyst specializing in corporate ownership structures.
Extract the Ultimate Beneficial Ownership (UBO) chain from the provided document text.
Be precise about ownership percentages. If a percentage is not explicitly stated, omit the entity rather than guessing.
Only include entities that are clearly mentioned in the document."""

_SYSTEM_EQUITY = """You are a corporate lawyer analyzing cap tables and shareholder registers.
Extract each shareholder's equity stake from the document. 
Return one EquityStake per distinct shareholder.
If share class is not mentioned, use 'Ordinary'. Use 0.0 for unknown percentages only when total ownership structure is implied."""

_SYSTEM_CONTROL = """You are a corporate governance expert analyzing shareholders' agreements.
Extract all governance and control rights provisions from the document.
Be conservative — only include rights explicitly mentioned, not implied."""


def structure_document(
    extracted_text: str,
    filename: str = "",
) -> tuple[UBOInfo | None, list[EquityStake], ControlRights | None, str | None]:
    """
    Run Instructor structuring on extracted document text.

    Returns:
        (ubo_info, equity_stakes, control_rights, model_used)
        Any element can be None/empty if extraction fails or no LLM is configured.
    """
    llm = get_llm_client()

    if llm is None:
        logger.info("No LLM client — skipping structuring")
        return None, [], None, None

    doc_text = _truncate(extracted_text)
    logger.info(f"Structuring '{filename}' with {llm.provider}/{llm.model}")

    # ── 1. UBO Info ───────────────────────────────────────────────────────────
    ubo_info = _extract_schema(
        llm=llm,
        schema_class=UBOInfo,
        system_prompt=_SYSTEM_UBO,
        user_prompt=(
            f"Extract the UBO chain from this document:\n\n{doc_text}"
        ),
    )

    # ── 2. Equity Stakes (cap table) ──────────────────────────────────────────
    # Instructor doesn't directly support list[T] at the top level cleanly —
    # wrap in a container and unwrap
    from pydantic import BaseModel

    class EquityStakeList(BaseModel):
        equity_stakes: list[EquityStake]

    equity_result = _extract_schema(
        llm=llm,
        schema_class=EquityStakeList,
        system_prompt=_SYSTEM_EQUITY,
        user_prompt=(
            f"Extract all equity stakes / cap table entries from this document:\n\n{doc_text}"
        ),
    )
    equity_stakes = equity_result.equity_stakes if equity_result else []

    # ── 3. Control Rights ─────────────────────────────────────────────────────
    control_rights = _extract_schema(
        llm=llm,
        schema_class=ControlRights,
        system_prompt=_SYSTEM_CONTROL,
        user_prompt=(
            f"Extract all governance and control rights from this document:\n\n{doc_text}"
        ),
    )

    return ubo_info, equity_stakes, control_rights, f"{llm.provider}/{llm.model}"
