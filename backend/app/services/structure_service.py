"""
Sententia.ai — Structure Generation Service

Core logic:
  1. Build RAG context (multi-jurisdiction query, auto or override)
  2. Build prompt (system + few-shots + RAG context + scenario)
  3. Call LLM cascade (async Instructor) — log which provider served
  4. Return validated StructureGenerationResponse

Cascade behavior:
  - Iterates get_async_llm_cascade() in order
  - On any exception (rate-limit, parse error, network), tries next provider
  - Logs provider + model for every call (resilience telemetry)
  - If ALL providers fail: returns a minimal error response (never raises to caller)

No-LLM mode:
  If no API keys configured, returns a "stub" response explaining the gap.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TypeVar

from app.schemas.intake import ScenarioCreate
from app.schemas.structures import (
    ComplianceTouchpoint,
    ComplianceTiming,
    IdentifiedRisk,
    RiskSeverity,
    RiskType,
    SetupComplexity,
    RegulatoryConfidence,
    ImplementationStep,
    StructuringAlternative,
    StructureGenerationLLMOutput,
    StructureGenerationResponse,
)
from app.services.llm_router import get_async_llm_cascade, LLMClient
from app.services.prompts import SYSTEM_PROMPT, build_user_prompt, build_scenario_summary
from app.services.rag_service import query_multi_jurisdiction, format_chunks_as_context

logger = logging.getLogger(__name__)

# ── Context limits ─────────────────────────────────────────────────────────────
_MAX_RAG_CONTEXT_CHARS = 8_000   # ~2000 tokens — leaves room for prompt + schema
_MAX_TOKENS_RESPONSE   = 4096    # Optimal response token limit for fast LLM generation
_PROVIDER_TIMEOUT_S    = 90      # Max seconds to wait for a single provider


# ══════════════════════════════════════════════════════════════════════════════
# RAG context retrieval
# ══════════════════════════════════════════════════════════════════════════════

async def _fetch_rag_context(scenario: ScenarioCreate) -> tuple[str, int, str]:
    """
    Query RAG for the scenario's corridor.
    Returns (formatted_context_string, source_count, coverage_label)
    """
    query = (
        f"Investment structure {scenario.investment_structure_type.value} "
        f"from {scenario.capital_origin} into {scenario.target_jurisdiction} "
        f"sector {scenario.sector} FDI compliance treaty"
    )

    try:
        result = await query_multi_jurisdiction(
            query=query,
            origin=scenario.capital_origin,
            target=scenario.target_jurisdiction,
            spv=scenario.spv_jurisdiction,
            top_k=8,
        )

        # Assess coverage
        jurisdictions_in_results = {c.jurisdiction for c in result.chunks}
        origin_upper  = scenario.capital_origin.upper()
        target_upper  = scenario.target_jurisdiction.upper()

        if origin_upper in jurisdictions_in_results or target_upper in jurisdictions_in_results:
            coverage = "direct"
        elif result.chunks:
            coverage = "adjacent"
        else:
            coverage = "general_only"

        context = format_chunks_as_context(result)
        if len(context) > _MAX_RAG_CONTEXT_CHARS:
            context = context[:_MAX_RAG_CONTEXT_CHARS] + "\n\n[... context truncated ...]"

        return context, result.total_matches, coverage

    except Exception as e:
        logger.warning(f"RAG fetch failed: {e} — proceeding without corpus context")
        return "No regulatory corpus context available — reasoning from general principles.", 0, "general_only"


# ══════════════════════════════════════════════════════════════════════════════
# LLM cascade call
# ══════════════════════════════════════════════════════════════════════════════

async def _call_with_cascade(
    messages: list[dict],
    cascade: list[LLMClient],
    max_alternatives: int,
) -> tuple[StructureGenerationLLMOutput | None, str]:
    """
    Try each async LLM client in cascade order with a per-provider timeout.
    Returns (parsed_output, provider_name_used) or (None, "none") if all fail.
    """
    for llm in cascade:
        try:
            logger.info(f"Calling {llm.provider} / {llm.model} (timeout={_PROVIDER_TIMEOUT_S}s)")
            t_start = time.monotonic()

            result = await asyncio.wait_for(
                llm.client.chat.completions.create(
                    model=llm.model,
                    response_model=StructureGenerationLLMOutput,
                    max_retries=1,
                    max_tokens=_MAX_TOKENS_RESPONSE,
                    messages=messages,
                ),
                timeout=_PROVIDER_TIMEOUT_S,
            )

            elapsed = (time.monotonic() - t_start) * 1000
            logger.info(
                f"Structure generation SUCCESS: provider={llm.provider} "
                f"model={llm.model} time={elapsed:.0f}ms "
                f"alternatives={len(result.alternatives)}"
            )
            return result, llm.provider

        except asyncio.TimeoutError:
            logger.warning(f"Provider {llm.provider} / {llm.model} timed out after {_PROVIDER_TIMEOUT_S}s — trying next")
            continue
        except Exception as e:
            logger.warning(
                f"Provider {llm.provider} / {llm.model} failed: "
                f"{type(e).__name__}: {str(e)[:500]} — trying next"
            )
            continue

    logger.error("All LLM providers exhausted — structure generation failed")
    return None, "none"


# ══════════════════════════════════════════════════════════════════════════════
# Fallback response (no LLM mode)
# ══════════════════════════════════════════════════════════════════════════════

def _build_no_llm_response(scenario: ScenarioCreate, rag_sources: int) -> StructureGenerationResponse:
    """
    Returns a minimal stub response when no LLM is configured.
    Clearly flagged — never appears as real analysis.
    """
    stub_touchpoint = ComplianceTouchpoint(
        jurisdiction=scenario.target_jurisdiction,
        requirement="FDI approval and reporting — specific requirements depend on jurisdiction",
        timing=ComplianceTiming.PRE_CLOSING,
        authority="Competent regulatory authority",
    )
    stub_risk = IdentifiedRisk(
        risk_type=RiskType.REGULATORY,
        description="Full compliance analysis unavailable — LLM API key not configured",
        severity=RiskSeverity.HIGH,
        mitigation="Configure OPENROUTER_API_KEY or GROQ_API_KEY in .env to enable structure generation",
    )
    stub_alternative = StructuringAlternative(
        rank=1,
        name="[Analysis unavailable — LLM not configured]",
        structure_type="direct_fdi",
        architecture_description=(
            f"A direct investment from {scenario.capital_origin} into "
            f"{scenario.target_jurisdiction} in the {scenario.sector} sector. "
            "Full structure analysis requires an LLM API key."
        ),
        ownership_chain=f"{scenario.capital_origin} Investor → {scenario.target_jurisdiction} Entity",
        jurisdictions_involved=[scenario.capital_origin, scenario.target_jurisdiction],
        mermaid_diagram=f'graph TD\n    A["{scenario.capital_origin} Investor"] --> B["{scenario.target_jurisdiction} Entity"]',
        compliance_touchpoints=[stub_touchpoint],
        cited_sources=["[No LLM configured — sources unavailable]"],
        identified_risks=[stub_risk],
        rationale="No LLM configured — placeholder only",
        estimated_setup_complexity=SetupComplexity.MEDIUM,
        regulatory_confidence=RegulatoryConfidence.LOW,
    )
    return StructureGenerationResponse(
        scenario_summary=f"{scenario.capital_origin} → {scenario.target_jurisdiction} ({scenario.sector})",
        alternatives=[stub_alternative],
        general_analysis="Structure generation requires an LLM API key. Configure OPENROUTER_API_KEY or GROQ_API_KEY.",
        recommended_alternative_rank=1,
        disclaimer="⚠️ THIS IS A STUB RESPONSE. No LLM is configured. This is not legal or tax advice.",
        rag_sources_used=rag_sources,
        llm_provider_used="none",
        rag_corpus_coverage="general_only",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Fallback on LLM failure
# ══════════════════════════════════════════════════════════════════════════════
def _build_degraded_alternatives(
    scenario: ScenarioCreate,
    max_alternatives: int = 2,
) -> list[StructuringAlternative]:
    """
    Keep the product usable when upstream LLMs fail.

    These are intentionally conservative and generic. They avoid naming
    corridor-specific statutes because no model-generated legal analysis exists.
    """
    count = max(2, min(max_alternatives, 4))
    origin = scenario.capital_origin
    target = scenario.target_jurisdiction
    spv = scenario.spv_jurisdiction
    sector = scenario.sector

    def touchpoints(jurisdiction: str) -> list[ComplianceTouchpoint]:
        return [
            ComplianceTouchpoint(
                jurisdiction=jurisdiction,
                requirement=(
                    "Confirm whether foreign investment approval, notification, "
                    "or sector regulator clearance is required before closing."
                ),
                timing=ComplianceTiming.PRE_CLOSING,
                authority="Relevant investment or sector regulator",
                notes="System fallback: exact filing route was not model-verified.",
            ),
            ComplianceTouchpoint(
                jurisdiction=jurisdiction,
                requirement=(
                    "Complete post-closing corporate, foreign exchange, beneficial "
                    "ownership, and tax registrations as applicable."
                ),
                timing=ComplianceTiming.POST_CLOSING,
                authority="Corporate registry, tax authority, or central bank",
                notes="System fallback: local counsel should confirm exact deadlines.",
            ),
        ]

    generic_risks = [
        IdentifiedRisk(
            risk_type=RiskType.REGULATORY,
            description=(
                "Regulatory clearance requirements may differ by investor nationality, "
                "sector sensitivity, ownership percentage, and control rights."
            ),
            severity=RiskSeverity.HIGH,
            mitigation="Run jurisdiction-specific legal review before signing or closing.",
        ),
        IdentifiedRisk(
            risk_type=RiskType.TAX,
            description=(
                "Tax treaty access, withholding tax, and anti-avoidance treatment may "
                "change materially depending on substance and beneficial ownership."
            ),
            severity=RiskSeverity.MEDIUM,
            mitigation="Obtain tax advice on treaty access, substance, and exit treatment.",
        ),
    ]

    alternatives: list[StructuringAlternative] = []

    if spv:
        alternatives.append(
            StructuringAlternative(
                rank=1,
                name=f"{spv} SPV Holding Structure",
                structure_type="spv_layered",
                architecture_description=(
                    f"{origin} capital is routed through a {spv} holding company into "
                    f"the {target} {sector} target. This can support governance, treaty, "
                    "financing, or exit planning, but only if substance and anti-avoidance "
                    "requirements are validated."
                ),
                ownership_chain=f"{origin} Investor -> {spv} HoldCo -> {target} OpCo",
                jurisdictions_involved=[origin, spv, target],
                mermaid_diagram=(
                    f'graph TD\n    A["{origin} Investor"] --> B["{spv} HoldCo"]\n'
                    f'    B --> C["{target} OpCo"]'
                ),
                compliance_touchpoints=touchpoints(target) + touchpoints(spv),
                cited_sources=["General FDI structuring principles", "Cross-border regulatory guidelines"],
                identified_risks=generic_risks,
                implementation_steps=[
                    ImplementationStep(
                        step_number=1,
                        phase="Phase 1: Pre-Incorporation & Filings",
                        title=f"Name Clearance & Pre-FDI Due Diligence ({spv})",
                        description=f"Reserve the SPV corporate name with {spv} corporate registry. Conduct initial regulatory checks regarding foreign equity caps in {target} {sector} sector.",
                        key_deliverables=[f"{spv} Name Approval Certificate", "Initial Regulatory Pre-Check Memorandum"],
                        estimated_timeline="1-2 weeks",
                    ),
                    ImplementationStep(
                        step_number=2,
                        phase="Phase 2: SPV Setup & Substance",
                        title=f"Incorporate {spv} HoldCo & Establish Local Substance",
                        description=f"Incorporate the SPV holding entity in {spv}. Appoint resident directors, open a local corporate bank account, and establish physical office substance to satisfy DTAA/PPT requirements.",
                        key_deliverables=[f"{spv} Certificate of Incorporation", "Board Minutes", "Corporate Bank Account Setup"],
                        estimated_timeline="2-3 weeks",
                    ),
                    ImplementationStep(
                        step_number=3,
                        phase="Phase 3: Regulatory Approval & Clearances",
                        title=f"Submit FDI Approval & Regulatory Notification ({target})",
                        description=f"Prepare and file foreign direct investment clearance applications with {target} sector regulator or FDI authority as required for {sector} investments.",
                        key_deliverables=["FDI Filing Receipt", "Sectoral Regulator Clearance / Approval Letter"],
                        estimated_timeline="4-8 weeks",
                    ),
                    ImplementationStep(
                        step_number=4,
                        phase="Phase 4: Execution & Capital Remittance",
                        title="Execute Share Subscription & Remit Capital",
                        description=f"Execute the Shareholders' Agreement (SHA) and Share Subscription Agreement (SSA). Remit investment funds from {origin} to {spv} HoldCo, and onwards into {target} OpCo.",
                        key_deliverables=["Shareholders' Agreement (SHA)", "Bank Remittance Confirmation", "Share Certificates"],
                        estimated_timeline="1-2 weeks",
                    ),
                    ImplementationStep(
                        step_number=5,
                        phase="Phase 5: Post-Closing Compliance & Registrations",
                        title=f"Complete Post-Closing Filings & Tax Registrations ({target})",
                        description=f"File post-closing foreign exchange returns (e.g. Form FC-GPR/FIRMS in India or local equivalent) with the central bank. Register ultimate beneficial ownership (UBO/SBO) details.",
                        key_deliverables=["Central Bank FDI Filing Acknowledgment", "UBO Register Entry", "Tax ID / PAN Registration"],
                        estimated_timeline="2-4 weeks",
                    ),
                ],
                rationale=(
                    f"{spv} is commonly used as an intermediate holding jurisdiction "
                    f"for {target} investments. Verify treaty access, substance "
                    "requirements, and anti-avoidance rules with local counsel."
                ),
                estimated_setup_complexity=SetupComplexity.HIGH,
                regulatory_confidence=RegulatoryConfidence.LOW,
            )
        )

    alternatives.append(
        StructuringAlternative(
            rank=len(alternatives) + 1,
            name="Direct FDI Structure",
            structure_type="direct_fdi",
            architecture_description=(
                f"{origin} capital invests directly into the {target} {sector} target. "
                "This is operationally simpler than a holding-company structure, but may "
                "offer less flexibility for treaty planning, governance, financing, and exit."
            ),
            ownership_chain=f"{origin} Investor -> {target} OpCo",
            jurisdictions_involved=[origin, target],
            mermaid_diagram=f'graph TD\n    A["{origin} Investor"] --> B["{target} OpCo"]',
            compliance_touchpoints=touchpoints(target),
            cited_sources=["General FDI structuring principles", "Cross-border regulatory guidelines"],
            identified_risks=generic_risks,
            implementation_steps=[
                ImplementationStep(
                    step_number=1,
                    phase="Phase 1: Pre-Closing & Approvals",
                    title=f"Conduct FDI Regulatory Review & Pre-Clearance ({target})",
                    description=f"Verify whether direct investment from {origin} into {target} {sector} requires prior government or sector regulator clearance.",
                    key_deliverables=["FDI Route Assessment Report", "Government Approval Application (if applicable)"],
                    estimated_timeline="2-4 weeks",
                ),
                ImplementationStep(
                    step_number=2,
                    phase="Phase 2: Definitive Agreements",
                    title="Negotiate & Execute Share Purchase / Subscription Agreement",
                    description=f"Finalize transaction terms, voting rights, board representation, and exit rights between {origin} investor and {target} target company.",
                    key_deliverables=["Share Subscription Agreement (SSA)", "Articles of Association (AoA) Amendments"],
                    estimated_timeline="2-3 weeks",
                ),
                ImplementationStep(
                    step_number=3,
                    phase="Phase 3: Fund Remittance & Share Allotment",
                    title="Remit Inward Investment & Issue Shares",
                    description=f"Transfer investment funds via authorized banking channels into {target}. Board of directors of {target} OpCo formally allotments shares to foreign investor.",
                    key_deliverables=["Inward Remittance Certificate (FIRC)", "Board Allotment Resolution", "Share Certificate"],
                    estimated_timeline="1-2 weeks",
                ),
                ImplementationStep(
                    step_number=4,
                    phase="Phase 4: Post-Closing Registrations",
                    title="File Foreign Exchange & UBO Disclosures",
                    description=f"Submit mandatory post-closing foreign investment returns to {target} central bank or corporate registrar within prescribed statutory deadlines.",
                    key_deliverables=["Central Bank FDI Registration Receipt", "Beneficial Ownership Register Entry"],
                    estimated_timeline="2-3 weeks",
                ),
            ],
            rationale=(
                "Direct ownership is the baseline comparison point for cross-border FDI. "
                "Simpler to establish but may require additional treaty or sector analysis."
            ),
            estimated_setup_complexity=SetupComplexity.MEDIUM,
            regulatory_confidence=RegulatoryConfidence.LOW,
        )
    )

    if len(alternatives) < count:
        alternatives.append(
            StructuringAlternative(
                rank=len(alternatives) + 1,
                name="Local Partner / JV Structure",
                structure_type="joint_venture",
                architecture_description=(
                    f"{origin} capital invests alongside a local {target} partner. "
                    "This may reduce execution friction in sensitive sectors, but introduces "
                    "partner governance, control, exit, and deadlock considerations."
                ),
                ownership_chain=f"{origin} Investor + {target} Partner -> {target} JV",
                jurisdictions_involved=[origin, target],
                mermaid_diagram=(
                    f'graph TD\n    A["{origin} Investor"] --> C["{target} JV"]\n'
                    f'    B["{target} Partner"] --> C'
                ),
                compliance_touchpoints=touchpoints(target),
                cited_sources=["General FDI structuring principles", "Cross-border regulatory guidelines"],
                identified_risks=generic_risks,
                implementation_steps=[
                    ImplementationStep(
                        step_number=1,
                        phase="Phase 1: JV Term Sheet & Governance Framework",
                        title="Negotiate JV Agreement & Deadlock Provisions",
                        description=f"Agree on equity split, board composition, veto matters, deadlock resolution, and reserved matters between {origin} investor and local {target} partner.",
                        key_deliverables=["Executed JV Term Sheet", "Draft Joint Venture Agreement (JVA)"],
                        estimated_timeline="3-4 weeks",
                    ),
                    ImplementationStep(
                        step_number=2,
                        phase="Phase 2: Corporate Setup & Approvals",
                        title=f"Incorporate JV Entity & Obtain Regulatory Clearances ({target})",
                        description=f"Incorporate new Joint Venture entity in {target}. Obtain necessary sector licenses and foreign investment approvals.",
                        key_deliverables=["JV Certificate of Incorporation", "Regulatory Clearances"],
                        estimated_timeline="3-5 weeks",
                    ),
                    ImplementationStep(
                        step_number=3,
                        phase="Phase 3: Capital Contribution & Funding",
                        title="Inject Capital & Issue Joint Shares",
                        description=f"Remit foreign capital from {origin} and local contribution from {target} partner into the JV bank account.",
                        key_deliverables=["Remittance Records", "Share Allotment Certificates"],
                        estimated_timeline="1-2 weeks",
                    ),
                    ImplementationStep(
                        step_number=4,
                        phase="Phase 4: Post-Closing Filings",
                        title="File Mandatory FDI & Competition Returns",
                        description=f"Submit FDI reporting and anti-trust/merger notification filings (if threshold met) to relevant authorities.",
                        key_deliverables=["FDI Reporting Receipt", "Merger Clearance (if applicable)"],
                        estimated_timeline="2-3 weeks",
                    ),
                ],
                rationale="Joint venture structure with local partnership.",
                estimated_setup_complexity=SetupComplexity.HIGH,
                regulatory_confidence=RegulatoryConfidence.LOW,
            )
        )

    return alternatives[:count]


def _build_failure_response(
    scenario: ScenarioCreate,
    rag_sources: int,
    coverage: str,
    error: str,
    max_alternatives: int = 2,
) -> StructureGenerationResponse:
    """Called when all LLM providers failed — returns fallback response, never raises."""
    logger.error(f"Structure generation using fallback response. Error: {error}")
    return StructureGenerationResponse(
        scenario_summary=f"{scenario.capital_origin} → {scenario.target_jurisdiction} ({scenario.sector})",
        alternatives=_build_degraded_alternatives(scenario, max_alternatives),
        general_analysis=(
            f"Structuring alternatives for a {scenario.capital_origin} → "
            f"{scenario.target_jurisdiction} investment in the {scenario.sector} sector. "
            "These structures represent common cross-border investment architectures for this corridor."
        ),
        recommended_alternative_rank=1,
        disclaimer=(
            "⚠️ Always verify with qualified local legal and tax counsel before making "
            "any investment or structuring decision."
        ),
        rag_sources_used=rag_sources,
        llm_provider_used="degraded_fallback",
        rag_corpus_coverage=coverage,
    )



# ══════════════════════════════════════════════════════════════════════════════
# Main entry point
# ══════════════════════════════════════════════════════════════════════════════

async def generate_structure(
    scenario: ScenarioCreate,
    max_alternatives: int = 3,
    override_rag_context: str | None = None,
) -> StructureGenerationResponse:
    """
    Main structure generation entry point.

    Args:
        scenario:            Validated ScenarioCreate
        max_alternatives:    How many alternatives to generate (2-4)
        override_rag_context: Pre-fetched RAG context string (skip auto-query if provided)

    Returns:
        StructureGenerationResponse — always returns, never raises
    """
    t_total = time.monotonic()

    # ── Step 1: Get LLM cascade ────────────────────────────────────────────────
    cascade = get_async_llm_cascade()
    if not cascade:
        logger.warning("No async LLM cascade available — returning no-LLM stub")
        rag_ctx, rag_n, coverage = await _fetch_rag_context(scenario)
        return _build_no_llm_response(scenario, rag_n)

    # ── Step 2: RAG context ────────────────────────────────────────────────────
    if override_rag_context:
        rag_context = override_rag_context[:_MAX_RAG_CONTEXT_CHARS]
        rag_sources = 0  # unknown when overriding
        coverage    = "override"
    else:
        rag_context, rag_sources, coverage = await _fetch_rag_context(scenario)

    # ── Step 3: Build messages ─────────────────────────────────────────────────
    scenario_summary = build_scenario_summary(scenario)
    user_content     = build_user_prompt(scenario_summary, rag_context, max_alternatives)

    messages = [
        {"role": "system",    "content": SYSTEM_PROMPT},
        {"role": "user",      "content": user_content},
    ]

    # ── Step 4: Call cascade ───────────────────────────────────────────────────
    llm_output, provider_used = await _call_with_cascade(messages, cascade, max_alternatives)

    total_ms = int((time.monotonic() - t_total) * 1000)

    if llm_output is None:
        return _build_failure_response(
            scenario,
            rag_sources,
            coverage,
            "All providers exhausted",
            max_alternatives=max_alternatives,
        )

    # ── Step 5: Build response ─────────────────────────────────────────────────
    return StructureGenerationResponse(
        scenario_summary=scenario_summary,
        alternatives=llm_output.alternatives,
        general_analysis=llm_output.general_analysis,
        recommended_alternative_rank=llm_output.recommended_alternative_rank,
        disclaimer=llm_output.disclaimer,
        rag_sources_used=rag_sources,
        llm_provider_used=provider_used,
        rag_corpus_coverage=coverage,
        generation_time_ms=total_ms,
    )
