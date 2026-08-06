"""
Sententia.ai — Structure Generation Schemas

The shape of a single LLM-generated structuring analysis:
  StructuringAlternative  ← one ranked option (2-4 per response)
    ComplianceTouchpoint  ← a specific regulatory obligation
    IdentifiedRisk        ← a flagged risk with mitigation
  StructureGenerationResponse ← full response wrapping 2-4 alternatives
  StructureGenerateRequest    ← API request body
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.schemas.intake import ScenarioCreate


# ══════════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════════

class RiskSeverity(str, Enum):
    HIGH   = "high"
    MEDIUM = "medium"
    LOW    = "low"


class RiskType(str, Enum):
    REGULATORY  = "regulatory"
    TAX         = "tax"
    OPERATIONAL = "operational"
    POLITICAL   = "political"
    LEGAL       = "legal"


class ComplianceTiming(str, Enum):
    PRE_SIGNING  = "pre-signing"
    PRE_CLOSING  = "pre-closing"
    AT_CLOSING   = "at-closing"
    POST_CLOSING = "post-closing"
    ONGOING      = "ongoing"


class SetupComplexity(str, Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


class RegulatoryConfidence(str, Enum):
    HIGH   = "high"    # direct corpus sources found for this corridor
    MEDIUM = "medium"  # related/adjacent sources found
    LOW    = "low"     # reasoning from general principles only


# ══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE TOUCHPOINT
# ══════════════════════════════════════════════════════════════════════════════

class ComplianceTouchpoint(BaseModel):
    """A specific regulatory obligation arising from the structure."""
    jurisdiction: str = Field(..., description="Jurisdiction where obligation arises, e.g. 'India'")
    requirement: str = Field(..., description="Description of the regulatory requirement")
    timing: ComplianceTiming = Field(..., description="When this obligation must be fulfilled")
    authority: str = Field(..., description="Regulatory authority responsible, e.g. 'DPIIT', 'RBI', 'IRAS'")
    notes: str | None = Field(default=None, description="Additional context or filing details")

    @field_validator("timing", mode="before")
    @classmethod
    def _normalize_timing(cls, v: object) -> str:
        if isinstance(v, str):
            v_norm = v.lower().strip().replace("_", "-").replace(" ", "-")
            for member in ComplianceTiming:
                if member.value == v_norm or member.name.lower() == v_norm.replace("-", "_"):
                    return member.value
        return ComplianceTiming.PRE_CLOSING.value


# ══════════════════════════════════════════════════════════════════════════════
# IDENTIFIED RISK
# ══════════════════════════════════════════════════════════════════════════════

class IdentifiedRisk(BaseModel):
    """A flagged risk with mitigation strategy."""
    risk_type: RiskType = Field(..., description="Category of risk")
    description: str = Field(..., description="Clear description of the risk")
    severity: RiskSeverity = Field(..., description="Assessed severity: high / medium / low")
    mitigation: str = Field(..., description="Recommended mitigation or next step")

    @field_validator("risk_type", mode="before")
    @classmethod
    def _normalize_risk_type(cls, v: object) -> str:
        if isinstance(v, str):
            v_norm = v.lower().strip()
            for member in RiskType:
                if member.value == v_norm:
                    return member.value
        return RiskType.REGULATORY.value

    @field_validator("severity", mode="before")
    @classmethod
    def _normalize_severity(cls, v: object) -> str:
        if isinstance(v, str):
            v_norm = v.lower().strip()
            for member in RiskSeverity:
                if member.value == v_norm:
                    return member.value
        return RiskSeverity.MEDIUM.value


# ══════════════════════════════════════════════════════════════════════════════
# IMPLEMENTATION STEP
# ══════════════════════════════════════════════════════════════════════════════

class ImplementationStep(BaseModel):
    """A detailed step in executing the proposed investment structure."""
    step_number: Annotated[int, Field(ge=1)] = Field(
        ..., description="Sequential step number starting from 1"
    )
    phase: str = Field(
        ..., description="Execution phase name, e.g. 'Phase 1: Pre-Incorporation & Filings'"
    )
    title: str = Field(
        ..., description="Short action title, e.g. 'Incorporate SPV & Open Bank Account'"
    )
    description: str = Field(
        ..., description="Detailed explanation of regulatory filings, legal actions, and responsible parties"
    )
    key_deliverables: list[str] = Field(
        default_factory=list, description="Documents, filings, or approvals produced in this step"
    )
    estimated_timeline: str = Field(
        ..., description="Estimated completion duration, e.g. '2-3 weeks'"
    )

    @field_validator("step_number", mode="before")
    @classmethod
    def _clamp_step_number(cls, v: object) -> int:
        try:
            return max(1, int(v)) # type: ignore
        except (ValueError, TypeError):
            return 1


# ══════════════════════════════════════════════════════════════════════════════
# STRUCTURING ALTERNATIVE
# ══════════════════════════════════════════════════════════════════════════════

class StructuringAlternative(BaseModel):
    """A single ranked structuring alternative."""
    rank: Annotated[int, Field(ge=1, le=4)] = Field(
        ..., description="Rank 1 = most recommended; up to 4 alternatives"
    )
    name: str = Field(
        ...,
        description="Short descriptive name, e.g. 'Singapore SPV — DTAA Optimized'"
    )
    structure_type: str = Field(
        ...,
        description="One of: spv_layered, direct_fdi, joint_venture, acquisition, debt, convertible"
    )
    architecture_description: str = Field(
        ...,
        description="Detailed narrative description of the structure — entities, ownership, rationale"
    )
    ownership_chain: str = Field(
        ...,
        description="Linear ownership chain, e.g. 'PRC Fund (100%) → Singapore HoldCo (74%) → India OpCo'"
    )
    jurisdictions_involved: list[str] = Field(
        ...,
        description="All jurisdictions in the structure"
    )
    mermaid_diagram: str = Field(
        ...,
        description="Valid Mermaid graph TD flowchart showing the ownership and capital flow"
    )
    compliance_touchpoints: list[ComplianceTouchpoint] = Field(
        ...,
        description="All regulatory obligations — at least one per jurisdiction involved"
    )
    cited_sources: list[str] = Field(
        ...,
        description="Source document titles cited from the provided regulatory context"
    )
    identified_risks: list[IdentifiedRisk] = Field(
        ...,
        description="All material risks — at least one per structure"
    )
    implementation_steps: list[ImplementationStep] = Field(
        default_factory=list,
        description="Detailed step-by-step execution roadmap for implementing this proposed structure"
    )
    rationale: str = Field(
        ...,
        description="Why this alternative was ranked at this position relative to others"
    )
    estimated_setup_complexity: SetupComplexity
    regulatory_confidence: RegulatoryConfidence = Field(
        ...,
        description="Confidence level based on corpus source coverage for this corridor"
    )

    @field_validator("name", mode="before")
    @classmethod
    def _truncate_name(cls, v: object) -> str:
        return str(v)[:120] if v else "Structuring Alternative"

    @field_validator("rank", mode="before")
    @classmethod
    def _validate_rank(cls, v: object) -> int:
        r = int(v) # type: ignore
        if r < 1 or r > 4:
            raise ValueError("rank must be between 1 and 4")
        return r

    @field_validator("jurisdictions_involved", mode="before")
    @classmethod
    def _validate_jurisdictions(cls, v: object) -> list[str]:
        if isinstance(v, list) and len(v) < 2:
            raise ValueError("at least 2 jurisdictions involved required")
        if not isinstance(v, list):
            return ["Origin", "Target"]
        return [str(x) for x in v]

    @field_validator("compliance_touchpoints", mode="before")
    @classmethod
    def _validate_touchpoints(cls, v: object) -> list:
        if isinstance(v, list) and len(v) == 0:
            raise ValueError("at least 1 compliance touchpoint required")
        if not isinstance(v, list):
            return [{
                "jurisdiction": "Target",
                "requirement": "Verify local FDI regulatory compliance",
                "timing": "pre-closing",
                "authority": "Competent regulatory authority"
            }]
        return v

    @field_validator("cited_sources", mode="before")
    @classmethod
    def _ensure_sources(cls, v: object) -> list:
        if not isinstance(v, list) or not v:
            return ["General FDI legal guidelines"]
        return [str(x) for x in v]

    @field_validator("identified_risks", mode="before")
    @classmethod
    def _ensure_risks(cls, v: object) -> list:
        if not isinstance(v, list) or not v:
            return [{
                "risk_type": "regulatory",
                "description": "General cross-border regulatory compliance risks",
                "severity": "medium",
                "mitigation": "Consult qualified local legal counsel before closing"
            }]
        return v

    @field_validator("estimated_setup_complexity", mode="before")
    @classmethod
    def _normalize_complexity(cls, v: object) -> str:
        if isinstance(v, str):
            v_norm = v.lower().strip()
            for member in SetupComplexity:
                if member.value == v_norm:
                    return member.value
        return SetupComplexity.MEDIUM.value

    @field_validator("regulatory_confidence", mode="before")
    @classmethod
    def _normalize_confidence(cls, v: object) -> str:
        if isinstance(v, str):
            v_norm = v.lower().strip()
            for member in RegulatoryConfidence:
                if member.value == v_norm:
                    return member.value
        return RegulatoryConfidence.MEDIUM.value


# ══════════════════════════════════════════════════════════════════════════════
# FULL GENERATION RESPONSE (Instructor schema)
# ══════════════════════════════════════════════════════════════════════════════

class StructureGenerationLLMOutput(BaseModel):
    """
    The direct Instructor-enforced schema.
    Validated by LLM via Instructor — must always be parseable.
    """
    alternatives: Annotated[list[StructuringAlternative], Field(min_length=2, max_length=4)]
    general_analysis: str = Field(
        ...,
        description="Overall assessment of the scenario — corridor characteristics, key tension points, and recommendation summary"
    )
    recommended_alternative_rank: Annotated[int, Field(ge=1, le=4)] = Field(
        ..., description="Rank of the most recommended alternative"
    )
    disclaimer: str = Field(
        ...,
        description="Must warn that this is analytical output only, not legal or tax advice. Flag any gaps in corpus coverage."
    )

    @field_validator("recommended_alternative_rank", mode="before")
    @classmethod
    def _clamp_recommended_rank(cls, v: object) -> int:
        try:
            return max(1, min(int(v), 4)) # type: ignore
        except (ValueError, TypeError):
            return 1


# ══════════════════════════════════════════════════════════════════════════════
# API REQUEST / RESPONSE
# ══════════════════════════════════════════════════════════════════════════════

class StructureGenerateRequest(BaseModel):
    """Request body for POST /api/structures/generate."""
    scenario: ScenarioCreate = Field(
        ..., description="Validated scenario — use the same fields as POST /api/intake/scenario"
    )
    max_alternatives: Annotated[int, Field(ge=2, le=4)] = Field(
        default=3,
        description="Number of structuring alternatives to generate (2-4)"
    )
    override_rag_context: str | None = Field(
        default=None,
        description="Optional: pre-fetched RAG context string. If omitted, the endpoint runs RAG automatically."
    )


class StructureGenerationResponse(BaseModel):
    """Full API response from POST /api/structures/generate."""
    scenario_summary: str
    alternatives: list[StructuringAlternative]
    general_analysis: str
    recommended_alternative_rank: int
    disclaimer: str
    rag_sources_used: int
    llm_provider_used: str
    rag_corpus_coverage: str  # "direct" | "adjacent" | "general_only"
    generation_time_ms: int | None = None
