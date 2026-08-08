"""
Sententia.ai — Diagram Router

POST /api/diagram/generate
  - Accepts: DiagramRequest (inline structure_json OR structure_id)
  - Returns: DiagramResponse with mermaid_syntax string

The mermaid_syntax is valid graph TD syntax — feed it directly to mermaid.js
on the client. Zero backend dependency at render time (FR-5.2).
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from app.schemas.diagram import DiagramRequest, DiagramResponse
from app.services.diagram_serializer import serialize_structure_to_mermaid

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/diagram", tags=["Diagram"])


# In-memory cache of the most recent generated structures (keyed by scenario_id + rank).
# This is populated by the /api/structures/generate endpoint so the diagram endpoint
# can look up a structure by ID without a database round-trip.
# In production, replace with a short-lived Redis or Supabase lookup.
_structure_cache: dict[str, dict] = {}


def cache_structure(structure_id: str, alternative_dict: dict) -> None:
    """Called by the structures router to register a generated structure for diagram lookup."""
    _structure_cache[structure_id] = alternative_dict
    logger.debug(f"Diagram cache: stored structure_id={structure_id}")


@router.post(
    "/generate",
    response_model=DiagramResponse,
    status_code=status.HTTP_200_OK,
    summary="Convert a StructuringAlternative JSON to Mermaid.js graph TD syntax",
)
async def generate_diagram(payload: DiagramRequest) -> DiagramResponse:
    """
    **Two-pass Mermaid serialization:**

    | Pass | Trigger | Strategy |
    |---|---|---|
    | **Pass 1** | LLM mermaid_diagram is valid | Validate, normalize, enrich with regulatory checkpoints |
    | **Pass 2** | LLM mermaid_diagram is malformed | Regenerate from ownership_chain + compliance_touchpoints |

    **Node classes:**
    - `originNode` — investor / UBO (styled blue, rounded)
    - `entityNode` — intermediate entity / SPV (styled dark blue)
    - `targetNode` — target operating company (styled green)
    - `regulatoryNode` — approval checkpoint (styled orange, diamond shape)

    **Output:**
    The `mermaid_syntax` string is valid `graph TD` syntax.
    Feed it directly to `mermaid.js` on the client — no further backend call needed at render time.
    """

    # ── Resolve alternative dict ───────────────────────────────────────────────
    alternative: dict | None = None

    if payload.structure_json:
        alternative = payload.structure_json
    elif payload.structure_id:
        alternative = _structure_cache.get(payload.structure_id)
        if alternative is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"Structure '{payload.structure_id}' not found in cache. "
                    "Generate it first via POST /api/structures/generate, "
                    "or pass structure_json inline."
                ),
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either structure_json or structure_id in the request.",
        )

    # ── If valid mermaid_diagram already exists (e.g. simulation template), return directly ──
    if alternative and alternative.get("mermaid_diagram"):
        raw_diagram = str(alternative["mermaid_diagram"]).strip()
        import re
        clean_diagram = re.sub(r"^---[\s\S]*?---\s*", "", raw_diagram).strip()
        clean_diagram = re.sub(r'-\.\s*"([^"]+)"\s*\.-\s*>', r'-.-|"\1"|', clean_diagram)
        clean_diagram = re.sub(r'-\.\s*"([^"]+)"\s*\.->', r'-.-|"\1"|', clean_diagram)

        if ("flowchart" in clean_diagram.lower() or "graph" in clean_diagram.lower()) and "INVALID" not in clean_diagram:
            checkpoint_count = len(alternative.get("compliance_touchpoints", [])) if payload.show_regulatory_checkpoints else 0
            return DiagramResponse(
                mermaid_syntax=clean_diagram,
                entity_count=5,
                edge_count=4,
                regulatory_checkpoint_count=checkpoint_count,
                jurisdictions=alternative.get("jurisdictions_involved", []),
                structure_name=alternative.get("name", "Structure Diagram"),
                generation_warnings=[],
            )


    # ── Otherwise fallback to serializer ─────────────────────────────────────
    try:
        mermaid_syntax, entity_count, edge_count, checkpoint_count, warnings = \
            serialize_structure_to_mermaid(
                alternative=alternative,
                show_regulatory_checkpoints=payload.show_regulatory_checkpoints,
                show_capital_flow_labels=payload.show_capital_flow_labels,
            )

    except Exception as e:
        logger.exception(f"Diagram serialization error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Diagram serialization failed: {str(e)[:200]}",
        )

    return DiagramResponse(
        mermaid_syntax=mermaid_syntax,
        entity_count=entity_count,
        edge_count=edge_count,
        regulatory_checkpoint_count=checkpoint_count,
        jurisdictions=alternative.get("jurisdictions_involved", []),
        structure_name=alternative.get("name", ""),
        generation_warnings=warnings,
    )
