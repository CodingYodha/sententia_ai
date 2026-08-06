"""
Sententia.ai — Compliance Gatekeeper Router

Endpoints:
  POST /api/compliance/evaluate  — Main compliance check
  GET  /api/compliance/corridors — List all pre-validated corridors
  GET  /api/compliance/corridors/{corridor_id} — Corridor detail

Routing logic for POST /api/compliance/evaluate:

  CORRIDOR MATCH   → Deterministic OPA/Rego evaluation
                     result.is_rule_validated = True
                     fallback_result = None

  NO CORRIDOR MATCH → LLM general-principles fallback (this module)
                     result = None
                     fallback_result.is_rule_validated = False
                     fallback_result.ui_banner ALWAYS present
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from app.schemas.compliance import (
    ComplianceEvaluateRequest,
    ComplianceResponse,
)
from app.services.corridor_registry import match_corridor, list_all_corridors
from app.services.opa_service import evaluate_compliance

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/compliance", tags=["Compliance"])


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT LOG WRITERS (FR-4.3)
# ══════════════════════════════════════════════════════════════════════════════

async def _write_audit_log(result, compliance_input, corridor_id: str) -> str | None:
    """
    Write a deterministic OPA evaluation to audit_log.
    Falls back gracefully — audit log failure never fails the API response.
    """
    audit_id = str(uuid.uuid4())
    try:
        from app.db.supabase_client import get_supabase_client
        sb = get_supabase_client()
        if sb is None:
            logger.warning("Supabase not configured — audit log skipped")
            return None

        entry = {
            "id":                 audit_id,
            "created_at":         datetime.now(timezone.utc).isoformat(),
            "corridor_id":        corridor_id,
            "policy_package":     result.policy_package,
            "evaluation_mode":    result.evaluation_mode,
            "scenario_id":        compliance_input.scenario_id,
            "structure_rank":     compliance_input.structure_rank,
            "input_data":         compliance_input.model_dump(mode="json"),
            "violations":         [v.model_dump() for v in result.violations],
            "warnings":           [w.model_dump() for w in result.warnings],
            "required_approvals": result.required_approvals,
            "is_allowed":         result.is_allowed,
            "is_rule_validated":  result.is_rule_validated,
            "blocking_count":     result.blocking_count,
            "warning_count":      result.warning_count,
        }

        sb.table("audit_log").insert(entry).execute()
        logger.info(f"Audit log written: id={audit_id} corridor={corridor_id}")
        return audit_id

    except Exception as e:
        logger.warning(f"Audit log write failed (non-fatal): {type(e).__name__}: {str(e)[:200]}")
        return None


async def _write_fallback_audit_log(
    fallback_result,
    compliance_input,
) -> str | None:
    """
    Write a fallback (LLM-based) evaluation to audit_log.
    Uses corridor_id='llm_fallback' and policy_package='sententia.fallback'.
    """
    audit_id = str(uuid.uuid4())
    try:
        from app.db.supabase_client import get_supabase_client
        sb = get_supabase_client()
        if sb is None:
            logger.warning("Supabase not configured — fallback audit log skipped")
            return None

        entry = {
            "id":                    audit_id,
            "created_at":            datetime.now(timezone.utc).isoformat(),
            "corridor_id":           "llm_fallback",
            "policy_package":        "sententia.fallback",
            "evaluation_mode":       fallback_result.evaluation_mode,
            "scenario_id":           compliance_input.scenario_id,
            "structure_rank":        compliance_input.structure_rank,
            "input_data":            compliance_input.model_dump(mode="json"),
            "is_allowed":            None,          # Cannot determine
            "is_rule_validated":     False,
            "llm_provider_used":     fallback_result.llm_provider_used,
            "rag_sources_used":      fallback_result.rag_sources_used,
            "ui_banner_type":        fallback_result.ui_banner.type,
            "general_analysis_len":  len(fallback_result.general_analysis),
            "risks_count":           len(fallback_result.illustrative_risks),
            "touchpoints_count":     len(fallback_result.illustrative_touchpoints),
        }

        sb.table("audit_log").insert(entry).execute()
        logger.info(f"Fallback audit log written: id={audit_id}")
        return audit_id

    except Exception as e:
        logger.warning(f"Fallback audit log write failed (non-fatal): {type(e).__name__}: {str(e)[:200]}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/evaluate",
    response_model=ComplianceResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate a cross-border investment structure — OPA for validated corridors, LLM fallback for novel ones",
)
async def evaluate(payload: ComplianceEvaluateRequest) -> ComplianceResponse:
    """
    **Dual-path compliance evaluation:**

    | Path | Trigger | Output |
    |---|---|---|
    | **Deterministic (OPA)** | Corridor in `corridors.yaml` | `is_rule_validated: true`, statutory blocking/warning violations |
    | **LLM Fallback** | No corridor match | `is_rule_validated: false`, `ui_banner`, illustrative risks and touchpoints |

    **LLM Fallback behavior:**
    - Queries the RAG corpus for general jurisdictional context
    - Calls LLM cascade (OpenRouter → Groq → fallback models) with anti-hallucination prompt
    - Returns 2-8 illustrative risks and 2-4 touchpoints from general principles
    - **Never** cites specific statute numbers or form references for unvalidated corridors
    - Always includes a `ui_banner` labeled "Illustrative — Not Yet Rule-Validated"

    **Audit:** Both paths log to `audit_log` table (FR-4.3).
    """
    ci = payload.compliance_input

    # ── Step 1: Match corridor ────────────────────────────────────────────────
    corridor = match_corridor(
        origin=ci.origin_jurisdiction,
        target=ci.target_jurisdiction,
        spv=ci.spv_jurisdiction,
    )

    # ═══════════════════════════════════════════════════════════════════════════
    # PATH A: No corridor match → LLM general-principles fallback
    # ═══════════════════════════════════════════════════════════════════════════
    if corridor is None:
        logger.info(
            f"No corridor match — routing to LLM fallback: "
            f"{ci.origin_jurisdiction} → {ci.spv_jurisdiction or 'direct'} → {ci.target_jurisdiction}"
        )

        try:
            from app.services.compliance_fallback_service import run_llm_fallback
            fallback_result = await run_llm_fallback(compliance_input=ci)
        except Exception as e:
            # This should never happen since run_llm_fallback never raises,
            # but belt-and-suspenders just in case.
            logger.exception(f"Unexpected fallback error: {e}")
            from app.schemas.compliance import UIBanner, FallbackComplianceResult
            fallback_result = FallbackComplianceResult(
                is_rule_validated=False,
                general_analysis=(
                    f"Unexpected error during fallback analysis for "
                    f"{ci.origin_jurisdiction} → {ci.target_jurisdiction}. "
                    f"Engage local qualified counsel."
                ),
                uncertainty_summary="System error during analysis — all requirements unverified.",
                ui_banner=UIBanner(
                    type="WARNING",
                    label="Illustrative — Not Yet Rule-Validated",
                    message=(
                        f"Analysis failed due to a system error. "
                        f"This corridor has no pre-validated policy. "
                        f"Engage local qualified counsel."
                    ),
                ),
            )

        # Audit log the fallback call
        audit_id = await _write_fallback_audit_log(fallback_result, ci)

        logger.info(
            f"Fallback complete: {ci.origin_jurisdiction} → {ci.target_jurisdiction} | "
            f"mode={fallback_result.evaluation_mode} | "
            f"risks={len(fallback_result.illustrative_risks)} | "
            f"provider={fallback_result.llm_provider_used}"
        )

        return ComplianceResponse(
            corridor_matched=False,
            result=None,
            fallback_result=fallback_result,
            audit_log_id=audit_id,
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # PATH B: Corridor matched → Deterministic OPA evaluation
    # ═══════════════════════════════════════════════════════════════════════════
    try:
        result = await evaluate_compliance(compliance_input=ci, corridor=corridor)
    except Exception as e:
        logger.exception(f"Policy evaluation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Policy evaluation failed: {str(e)[:200]}",
        )

    # Audit log the OPA evaluation
    audit_id = await _write_audit_log(result, ci, corridor.id)

    # Optional RAG context attachment
    rag_context: str | None = None
    if payload.include_rag_context:
        try:
            from app.services.rag_service import query_multi_jurisdiction, format_chunks_as_context
            query = (
                f"FDI compliance {ci.origin_jurisdiction} {ci.target_jurisdiction} "
                f"{ci.spv_jurisdiction or ''} {ci.sector}"
            )
            rag_result = await query_multi_jurisdiction(
                query=query,
                origin=ci.origin_jurisdiction,
                target=ci.target_jurisdiction,
                spv=ci.spv_jurisdiction,
                top_k=5,
            )
            rag_context = format_chunks_as_context(rag_result)
        except Exception as e:
            logger.warning(f"RAG context fetch failed (non-fatal): {e}")

    logger.info(
        f"OPA evaluation complete: corridor={corridor.id} "
        f"allowed={result.is_allowed} blocking={result.blocking_count} "
        f"warnings={result.warning_count} mode={result.evaluation_mode}"
    )

    return ComplianceResponse(
        corridor_matched=True,
        result=result,
        fallback_result=None,
        audit_log_id=audit_id,
        rag_context=rag_context,
    )


@router.get(
    "/corridors",
    summary="List all pre-validated corridors",
    status_code=status.HTTP_200_OK,
)
async def get_corridors() -> dict:
    """Return all active corridors from corridors.yaml."""
    corridors = list_all_corridors()
    return {
        "corridors": corridors,
        "count": len(corridors),
    }


@router.get(
    "/corridors/{corridor_id}",
    summary="Get details for a specific pre-validated corridor",
    status_code=status.HTTP_200_OK,
)
async def get_corridor(corridor_id: str) -> dict:
    """Return details for a single corridor by ID."""
    corridors = list_all_corridors()
    for c in corridors:
        if c["id"] == corridor_id:
            return c
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Corridor '{corridor_id}' not found",
    )
