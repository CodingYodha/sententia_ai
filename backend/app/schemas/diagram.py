"""
Sententia.ai — Diagram Schemas

DiagramRequest:  Input to POST /api/diagram/generate
DiagramResponse: Mermaid syntax string + metadata
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DiagramRequest(BaseModel):
    """
    Request body for POST /api/diagram/generate.
    Provide EITHER structure_json (inline) OR a structure_id to look up.
    """
    # Inline JSON path: pass the StructuringAlternative dict directly
    structure_json: dict | None = Field(
        None,
        description=(
            "Inline StructuringAlternative JSON. "
            "Takes precedence over structure_id if both are supplied."
        ),
    )
    # ID path: look up a previously generated structure from cache/DB
    structure_id: str | None = Field(
        None,
        description="ID of a previously generated structure (currently resolved from request cache).",
    )
    # Optional overrides for diagram rendering
    show_regulatory_checkpoints: bool = Field(
        True,
        description="Include regulatory-approval checkpoint nodes (styled distinctly).",
    )
    show_capital_flow_labels: bool = Field(
        True,
        description="Annotate capital-flow edges with ownership percentages and flow type.",
    )
    theme: str = Field(
        "default",
        description="Mermaid theme: default | dark | forest | neutral",
    )


class DiagramResponse(BaseModel):
    """Response from POST /api/diagram/generate."""

    mermaid_syntax: str = Field(
        ...,
        description="Valid Mermaid graph TD syntax string — can be fed directly to mermaid.js",
    )
    entity_count: int = Field(..., description="Number of entity nodes in the diagram")
    edge_count: int = Field(..., description="Number of directional edges")
    regulatory_checkpoint_count: int = Field(
        ...,
        description="Number of regulatory-approval checkpoint nodes added",
    )
    jurisdictions: list[str] = Field(default_factory=list)
    structure_name: str = Field(default="", description="Name of the structure alternative")
    generation_warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Non-fatal warnings from the serializer, e.g. 'Mermaid fallback used — "
            "LLM diagram was malformed'."
        ),
    )
