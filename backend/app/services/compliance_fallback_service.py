"""
Sententia.ai — Compliance Fallback Service

Entry point: run_llm_fallback(compliance_input) → FallbackComplianceResult

Execution flow:
  1. Query RAG corpus for general jurisdictional context (non-fatal)
  2. Build general-principles prompt using fallback_prompts.py
  3. Call LLM cascade (same provider chain as structure generation)
     using Instructor for schema-enforced FallbackLLMOutput
  4. Build and return FallbackComplianceResult with UIBanner

Degradation strategy:
  - If RAG fails → proceed with empty context (warn, don't crash)
  - If all LLM providers fail → return a minimal FallbackComplianceResult with
    a clear banner and a message explaining the system degraded gracefully
  - NEVER raises — always returns a FallbackComplianceResult
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import AsyncIterator

from app.schemas.compliance import (
    ComplianceInput,
    FallbackComplianceResult,
    FallbackLLMOutput,
    IllustrativeRiskItem,
    IllustrativeTouchpointItem,
    UIBanner,
)
from app.services.fallback_prompts import (
    FALLBACK_SYSTEM_PROMPT,
    build_fallback_user_prompt,
    build_banner_message,
)

logger = logging.getLogger(__name__)

# Minimum text length to include a RAG chunk — too-short chunks add noise
_MIN_CHUNK_LENGTH = 80


# ══════════════════════════════════════════════════════════════════════════════
# RAG CONTEXT FETCH
# ══════════════════════════════════════════════════════════════════════════════

async def _fetch_fallback_rag_context(ci: ComplianceInput) -> tuple[str, int]:
    """
    Query the RAG corpus for general context on the input corridor.
    Returns (formatted_context_string, num_chunks_used).
    Never raises — returns ("", 0) on any failure.
    """
    try:
        from app.services.rag_service import query_multi_jurisdiction, format_chunks_as_context

        # Build a query covering all three jurisdictions + sector
        jurisdictions = list(filter(None, [
            ci.origin_jurisdiction, ci.spv_jurisdiction, ci.target_jurisdiction
        ]))
        query = (
            f"FDI investment regulatory screening {' '.join(jurisdictions)} "
            f"{ci.sector} bilateral investment treaty general principles"
        )

        results = await query_multi_jurisdiction(
            query=query,
            origin=ci.origin_jurisdiction,
            target=ci.target_jurisdiction,
            spv=ci.spv_jurisdiction,
            top_k=6,  # Limit for fallback — keep prompt size manageable
        )

        if not results:
            # Fallback: try a general cross-jurisdiction query
            from app.services.rag_service import search_similar_chunks
            results = await search_similar_chunks(
                query=query,
                jurisdiction=None,
                top_k=4,
            )

        if results:
            context = format_chunks_as_context(results)
            # Trim to prevent token overflow
            if len(context) > 4000:
                context = context[:4000] + "\n[... context trimmed for token limit ...]"
            return context, len(results)

        return "", 0

    except Exception as e:
        logger.warning(f"RAG context fetch failed in fallback (non-fatal): {type(e).__name__}: {str(e)[:100]}")
        return "", 0


# ══════════════════════════════════════════════════════════════════════════════
# LLM CASCADE CALL
# ══════════════════════════════════════════════════════════════════════════════

async def _call_fallback_cascade(
    messages: list[dict],
) -> tuple[FallbackLLMOutput | None, str]:
    """
    Call the LLM cascade and parse output as FallbackLLMOutput via Instructor.
    Returns (parsed_output, provider_name) or (None, "none") if all fail.
    """
    try:
        from app.services.llm_router import get_async_llm_cascade
        import instructor

        cascade = get_async_llm_cascade()
        if not cascade:
            logger.warning("LLM cascade returned empty list — no API keys configured")
            return None, "none"

        for provider_config in cascade:
            provider_name = provider_config.get("provider", "unknown")
            try:
                import openai

                # Build async client — same pattern as structure_service.py
                base_url = provider_config.get("base_url")
                api_key  = provider_config.get("api_key")
                model    = provider_config.get("model")

                raw_client = openai.AsyncOpenAI(
                    base_url=base_url,
                    api_key=api_key,
                )
                client = instructor.from_openai(raw_client)

                result: FallbackLLMOutput = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    response_model=FallbackLLMOutput,
                    max_retries=2,
                    max_tokens=2048,     # Shorter than structure generation
                    temperature=0.2,     # Lower temperature for factual restraint
                )

                logger.info(f"Fallback LLM served by provider: {provider_name}")
                return result, provider_name

            except Exception as e:
                logger.warning(
                    f"Fallback cascade provider {provider_name} failed: "
                    f"{type(e).__name__}: {str(e)[:120]}"
                )
                continue

        logger.error("All fallback LLM providers failed")
        return None, "none"

    except Exception as e:
        logger.error(f"Fallback cascade call failed: {type(e).__name__}: {e}")
        return None, "none"


# ══════════════════════════════════════════════════════════════════════════════
# DEGRADED FALLBACK BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def _degraded_banner(ci: ComplianceInput, reason: str) -> UIBanner:
    """Build a banner for when the LLM fallback itself degrades."""
    spv_part = f" via {ci.spv_jurisdiction}" if ci.spv_jurisdiction else ""
    return UIBanner(
        type="WARNING",
        label="Illustrative — Not Yet Rule-Validated",
        message=(
            f"The corridor {ci.origin_jurisdiction}{spv_part} → {ci.target_jurisdiction} "
            f"has no pre-validated compliance policy, and the AI analysis service is currently "
            f"unavailable ({reason}). This response is a system placeholder. "
            f"Engage qualified local counsel in each jurisdiction before proceeding."
        ),
    )


def _build_no_llm_result(ci: ComplianceInput) -> FallbackComplianceResult:
    """Return when no LLM API keys are configured at all."""
    return FallbackComplianceResult(
        is_rule_validated=False,
        illustrative_risks=[
            IllustrativeRiskItem(
                category="regulatory",
                description="Regulatory screening may be required in the target jurisdiction.",
                typical_pattern="Most FDI frameworks require some form of pre-investment notification or approval.",
                uncertainty_flag="No AI-based analysis is available. Exact requirements for this corridor are unknown.",
            )
        ],
        illustrative_touchpoints=[
            IllustrativeTouchpointItem(
                jurisdiction=ci.target_jurisdiction,
                typical_requirement="Typically requires foreign investment registration and may require prior approval for sectors above certain ownership thresholds.",
                typical_authority="Investment promotion authority / central bank / sector regulator",
                uncertainty_flag="No AI-based analysis is available. Engage local counsel.",
            )
        ],
        general_analysis=(
            f"This is a placeholder general-principles analysis for {ci.origin_jurisdiction} → "
            f"{ci.target_jurisdiction}. No AI language model is configured (no API keys). "
            f"Please configure at least one LLM provider (OpenRouter or Groq) or engage qualified "
            f"local counsel for this corridor."
        ),
        general_principles_applied=[
            "Most FDI frameworks require pre-investment notification or registration",
            "Sector-specific approval may be required for strategic industries",
        ],
        uncertainty_summary=(
            f"No AI-based analysis is available for this corridor. "
            f"All regulatory requirements for {ci.origin_jurisdiction} → {ci.target_jurisdiction} are unverified."
        ),
        ui_banner=_degraded_banner(ci, "no LLM providers configured"),
        rag_sources_used=0,
        llm_provider_used="none",
        evaluation_mode="llm_fallback_degraded",
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )


def _build_error_result(
    ci: ComplianceInput,
    rag_sources: int,
) -> FallbackComplianceResult:
    """Return when LLM providers are configured but all failed (rate limits, timeouts, etc.)."""
    return FallbackComplianceResult(
        is_rule_validated=False,
        illustrative_risks=[
            IllustrativeRiskItem(
                category="regulatory",
                description=(
                    f"Investment from {ci.origin_jurisdiction} into {ci.target_jurisdiction} "
                    f"may require regulatory approval or notification. Without an AI-generated analysis, "
                    f"specific risks cannot be identified."
                ),
                typical_pattern=(
                    "Most FDI frameworks require some form of pre-investment notification, "
                    "registration, or approval, particularly in strategic sectors."
                ),
                uncertainty_flag=(
                    "AI analysis service temporarily unavailable. "
                    "All specific requirements for this corridor are unverified."
                ),
            )
        ],
        illustrative_touchpoints=[
            IllustrativeTouchpointItem(
                jurisdiction=ci.target_jurisdiction,
                typical_requirement=(
                    "Typically requires foreign investment registration and sector-specific "
                    "approval for ownership stakes above standard thresholds."
                ),
                typical_authority="Investment promotion authority / central bank / sector regulator",
                uncertainty_flag="AI service unavailable. Engage local qualified counsel.",
            )
        ],
        general_analysis=(
            f"This is a degraded placeholder response for {ci.origin_jurisdiction} → "
            f"{ci.target_jurisdiction}. All AI language model providers are temporarily unavailable. "
            f"This corridor has no pre-validated compliance policy. "
            f"Engage qualified local counsel in each jurisdiction immediately."
        ),
        general_principles_applied=[
            "FDI screening requirements vary significantly by jurisdiction and sector",
            "Tax treaty benefits depend on economic substance in intermediate SPV jurisdictions",
        ],
        uncertainty_summary=(
            f"AI analysis service temporarily unavailable. Specific requirements for "
            f"{ci.origin_jurisdiction} → {ci.target_jurisdiction} cannot be assessed at this time."
        ),
        ui_banner=_degraded_banner(ci, "AI analysis service temporarily unavailable"),
        rag_sources_used=rag_sources,
        llm_provider_used="none",
        evaluation_mode="llm_fallback_degraded",
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

async def run_llm_fallback(
    compliance_input: ComplianceInput,
    max_risks: int = 4,
) -> FallbackComplianceResult:
    """
    Run the LLM fallback for a corridor with no pre-validated Rego policy.

    Always returns a FallbackComplianceResult — never raises.
    Degradation modes:
      - No LLM keys          → llm_fallback_degraded (minimal placeholder)
      - All providers fail   → llm_fallback_degraded (minimal placeholder)
      - RAG fails            → proceeds without RAG context
    """
    # ── Step 1: RAG context (non-fatal) ──────────────────────────────────────
    rag_context, rag_sources = await _fetch_fallback_rag_context(compliance_input)
    logger.info(
        f"Fallback RAG: {rag_sources} chunks retrieved for "
        f"{compliance_input.origin_jurisdiction} → {compliance_input.target_jurisdiction}"
    )

    # ── Step 2: Check if LLM is available at all ──────────────────────────────
    try:
        from app.services.llm_router import get_async_llm_cascade
        cascade = get_async_llm_cascade()
        if not cascade:
            logger.warning("No LLM providers available for fallback path")
            return _build_no_llm_result(compliance_input)
    except Exception as e:
        logger.error(f"LLM cascade check failed: {e}")
        return _build_no_llm_result(compliance_input)

    # ── Step 3: Build messages ────────────────────────────────────────────────
    user_prompt = build_fallback_user_prompt(
        ci=compliance_input,
        rag_context=rag_context,
        max_risks=max_risks,
    )
    messages = [
        {"role": "system", "content": FALLBACK_SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ]

    # ── Step 4: Call LLM cascade ──────────────────────────────────────────────
    llm_output, provider_used = await _call_fallback_cascade(messages)

    if llm_output is None:
        logger.warning("All fallback LLM providers failed — returning degraded result")
        return _build_error_result(compliance_input, rag_sources)

    # ── Step 5: Build UIBanner ────────────────────────────────────────────────
    banner_message = build_banner_message(
        ci=compliance_input,
        uncertainty_summary=llm_output.uncertainty_summary,
    )
    banner = UIBanner(
        type="WARNING",
        label="Illustrative — Not Yet Rule-Validated",
        message=banner_message,
    )

    # ── Step 6: Assemble result ───────────────────────────────────────────────
    result = FallbackComplianceResult(
        is_rule_validated=False,
        illustrative_risks=llm_output.illustrative_risks,
        illustrative_touchpoints=llm_output.illustrative_touchpoints,
        general_analysis=llm_output.general_analysis,
        general_principles_applied=llm_output.general_principles_applied,
        uncertainty_summary=llm_output.uncertainty_summary,
        ui_banner=banner,
        rag_sources_used=rag_sources,
        llm_provider_used=provider_used,
        evaluation_mode="llm_fallback",
        evaluated_at=datetime.now(timezone.utc).isoformat(),
    )

    logger.info(
        f"Fallback complete: {compliance_input.origin_jurisdiction} → "
        f"{compliance_input.target_jurisdiction} | provider={provider_used} | "
        f"risks={len(result.illustrative_risks)} | rag_sources={rag_sources}"
    )
    return result
