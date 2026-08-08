"""
Sententia.ai — Structures Router

Endpoints:
  POST /api/structures/generate — main structure generation endpoint
  GET  /api/structures/providers — list configured LLM providers in cascade
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies.auth import UserContext, get_optional_user
from app.schemas.structures import StructureGenerateRequest, StructureGenerationResponse
from app.services.audit_service import audit_structure_generated
from app.services.review_queue_service import auto_enqueue
from app.config import get_settings
from app.services.simulation_service import generate_simulated_structure, is_simulation_triggered
from app.services.structure_service import generate_structure
from app.services.llm_router import get_async_llm_cascade


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/structures", tags=["Structures"])


@router.post(
    "/generate",
    response_model=StructureGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate ranked cross-border investment structure alternatives",
)
async def generate(
    payload: StructureGenerateRequest,
    current_user: UserContext | None = Depends(get_optional_user),
) -> StructureGenerationResponse:
    """
    Accepts a validated investment scenario and returns 2–4 ranked structuring alternatives.
    """
    try:
        settings = get_settings()
        if is_simulation_triggered(payload.scenario, settings.simulation_mode):
            logger.info("Simulation Mode active — generating structure from simulation templates")
            result = await generate_simulated_structure(payload.scenario, delay_seconds=6.5)
        else:
            result = await generate_structure(
                scenario=payload.scenario,
                max_alternatives=payload.max_alternatives,
                override_rag_context=payload.override_rag_context,
            )


        # FR-7.3: audit the generation event
        scenario_id = str(payload.scenario.model_dump().get("investor_name", "unknown"))
        audit_structure_generated(
            scenario_id=scenario_id,
            num_alternatives=len(result.alternatives),
            provider=result.llm_provider_used,
            user=current_user,
        )

        # FR-6.1: auto-enqueue every alternative as 'pending' (unvalidated by default)
        for alt in result.alternatives:
            await auto_enqueue(
                structure_id=f"{scenario_id}-rank{alt.rank}",
                scenario_id=scenario_id,
                structure_name=alt.name,
                structure_rank=alt.rank,
                structure_json=alt.model_dump(),
                compliance_result=None,
                generated_by=current_user,
            )

        return result
    except Exception as e:
        logger.exception(f"Unexpected error in structure generation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Structure generation failed: {str(e)[:200]}",
        )


@router.get(
    "/providers",
    summary="List configured LLM providers in cascade order",
    status_code=status.HTTP_200_OK,
)
async def list_providers() -> dict:
    """
    Returns the configured LLM provider cascade — useful for health checks
    and resilience debugging.
    """
    cascade = get_async_llm_cascade()
    return {
        "providers": [
            {"provider": llm.provider, "model": llm.model}
            for llm in cascade
        ],
        "count": len(cascade),
        "status": "ready" if cascade else "no_providers_configured",
    }
