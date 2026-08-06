"""
Sententia.ai — Intake Pydantic Schemas

Three groups:
  1. Document extraction schemas  — UBOInfo, EquityStake, ControlRights
  2. Scenario intake schema       — ScenarioCreate (FR-1.1), ScenarioResponse
  3. API response wrappers        — DocumentExtractionResult, IntakeError
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated
from pydantic import BaseModel, Field, field_validator


# ══════════════════════════════════════════════════════════════════════════════
# 1.  DOCUMENT EXTRACTION SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class EntityType(str, Enum):
    INDIVIDUAL  = "individual"
    COMPANY     = "company"
    TRUST       = "trust"
    FUND        = "fund"
    PARTNERSHIP = "partnership"
    OTHER       = "other"


class UBOEntity(BaseModel):
    """A single node in the ultimate beneficial ownership chain."""
    name: str = Field(..., description="Legal name of the entity or person")
    jurisdiction: str = Field(..., description="Jurisdiction of incorporation or residence")
    entity_type: EntityType = Field(..., description="Type of entity")
    ownership_pct: Annotated[float, Field(ge=0.0, le=100.0)] = Field(
        ..., description="Direct ownership percentage in the immediate downstream entity"
    )
    is_ubo: bool = Field(
        default=False,
        description="True if this entity is an ultimate beneficial owner (natural person or opaque trust at the top of the chain)"
    )


class UBOInfo(BaseModel):
    """Full UBO chain extracted from a document."""
    ultimate_beneficial_owners: list[UBOEntity] = Field(
        default_factory=list,
        description="List of UBO entities identified in the document"
    )
    ownership_chain_summary: str = Field(
        default="",
        description="Human-readable description of the full ownership chain, e.g. 'Zhang Wei (CN, 100%) → HoldCo SG (100%) → India OpCo'"
    )
    total_foreign_ownership_pct: float | None = Field(
        default=None,
        description="Aggregate foreign ownership percentage in the target entity, if determinable"
    )
    ubo_disclosure_required: bool = Field(
        default=False,
        description="Whether SBO/UBO disclosure is triggered based on thresholds visible in the document"
    )


class EquityStake(BaseModel):
    """One row in a cap table — a single shareholder's holding."""
    entity_name: str = Field(..., description="Name of the shareholder entity")
    entity_type: EntityType = Field(..., description="Type of entity")
    jurisdiction: str = Field(..., description="Jurisdiction of the shareholder entity")
    ownership_pct: Annotated[float, Field(ge=0.0, le=100.0)] = Field(
        ..., description="Percentage ownership in the company"
    )
    share_class: str | None = Field(
        default=None,
        description="Share class, e.g. 'Series A Preferred', 'Ordinary', 'Class B'"
    )
    num_shares: int | None = Field(
        default=None,
        description="Number of shares held, if stated"
    )
    voting_rights_pct: float | None = Field(
        default=None,
        description="Voting rights as a percentage, if different from economic ownership"
    )
    par_value_usd: float | None = Field(
        default=None,
        description="Par value per share in USD, if stated"
    )


class BoardSeat(BaseModel):
    """A single board seat appointment right."""
    appointing_party: str = Field(..., description="Entity entitled to appoint this director")
    num_seats: int = Field(default=1, description="Number of seats the party may appoint")
    seat_type: str = Field(
        default="director",
        description="Type of seat, e.g. 'director', 'observer', 'independent director'"
    )


class ControlRights(BaseModel):
    """Governance and control rights extracted from a shareholders' agreement."""
    board_seats: list[BoardSeat] = Field(
        default_factory=list,
        description="Board seat appointment rights per party"
    )
    veto_rights: list[str] = Field(
        default_factory=list,
        description="Matters requiring unanimous or special approval, e.g. 'new share issuance', 'change of business'"
    )
    protective_provisions: list[str] = Field(
        default_factory=list,
        description="Minority protective provisions, e.g. 'anti-dilution', 'liquidation preference'"
    )
    drag_along: bool = Field(default=False, description="Drag-along right present")
    tag_along: bool = Field(default=False, description="Tag-along / co-sale right present")
    right_of_first_refusal: bool = Field(default=False, description="ROFR present")
    anti_dilution_type: str | None = Field(
        default=None,
        description="Anti-dilution mechanism: 'full_ratchet', 'broad_based_weighted_average', 'narrow_based_weighted_average', or null"
    )
    lock_in_period_months: int | None = Field(
        default=None,
        description="Lock-in / lock-up period in months, if stated"
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2.  SCENARIO INTAKE SCHEMA  (FR-1.1 / FR-1.2)
# ══════════════════════════════════════════════════════════════════════════════

class InvestmentStructureType(str, Enum):
    DIRECT_FDI      = "direct_fdi"
    SPV_LAYERED     = "spv_layered"
    JOINT_VENTURE   = "joint_venture"
    ACQUISITION     = "acquisition"
    DEBT            = "debt"
    CONVERTIBLE     = "convertible"
    OTHER           = "other"


class InvestorProfile(str, Enum):
    STRATEGIC        = "strategic"
    FINANCIAL        = "financial_investor"
    FAMILY_OFFICE    = "family_office"
    SOVEREIGN_WEALTH = "sovereign_wealth_fund"
    PE_VC            = "pe_vc_fund"
    CORPORATE        = "corporate"
    OTHER            = "other"


class ScenarioCreate(BaseModel):
    """
    Scenario intake fields — PRD FR-1.1.
    Required fields per FR-1.2: capital_origin, target_jurisdiction, sector,
    investment_amount_usd, investment_structure_type.
    """

    # ── Required (FR-1.2) ──────────────────────────────────────────────────
    capital_origin: str = Field(
        ...,
        min_length=2,
        description="Country / jurisdiction of capital origin, e.g. 'China', 'United States'"
    )
    target_jurisdiction: str = Field(
        ...,
        min_length=2,
        description="Target investment jurisdiction, e.g. 'India', 'Germany'"
    )
    sector: str = Field(
        ...,
        min_length=2,
        description="Sector / industry, e.g. 'Technology', 'Infrastructure', 'Financial Services'"
    )
    investment_amount_usd: Annotated[float, Field(gt=0)] = Field(
        ...,
        description="Proposed investment amount in USD"
    )
    investment_structure_type: InvestmentStructureType = Field(
        ...,
        description="Proposed investment structure type"
    )

    # ── Optional (FR-1.1) ─────────────────────────────────────────────────
    spv_jurisdiction: str | None = Field(
        default=None,
        description="Intermediate SPV jurisdiction if known, e.g. 'Singapore', 'Mauritius'"
    )
    equity_pct: Annotated[float, Field(ge=0.0, le=100.0)] | None = Field(
        default=None,
        description="Proposed equity stake percentage in the target entity"
    )
    control_rights_requested: list[str] = Field(
        default_factory=list,
        description="Specific control rights required, e.g. ['board_seat', 'veto_new_shares']"
    )
    regulatory_constraints: list[str] = Field(
        default_factory=list,
        description="Known regulatory constraints or flags, e.g. ['press_note_3_applicable', 'cfius_review_possible']"
    )
    investor_profile: InvestorProfile = Field(
        default=InvestorProfile.OTHER,
        description="Investor classification"
    )
    notes: str | None = Field(
        default=None,
        max_length=2000,
        description="Free-text notes from the analyst"
    )
    uploaded_doc_url: str | None = Field(
        default=None,
        description="Supabase Storage URL of any uploaded document linked to this scenario"
    )

    @field_validator("capital_origin", "target_jurisdiction", "sector", mode="before")
    @classmethod
    def strip_and_title(cls, v: str) -> str:
        return v.strip()


class ScenarioResponse(BaseModel):
    """Response returned after creating a scenario."""
    scenario_id: str
    status: str = "created"
    capital_origin: str
    target_jurisdiction: str
    sector: str
    investment_amount_usd: float
    investment_structure_type: str
    spv_jurisdiction: str | None
    equity_pct: float | None
    investor_profile: str


# ══════════════════════════════════════════════════════════════════════════════
# 3.  DOCUMENT EXTRACTION RESULT WRAPPER
# ══════════════════════════════════════════════════════════════════════════════

class ExtractionMethod(str, Enum):
    DOCLING       = "docling"
    PYPDF_FALLBACK = "pypdf_fallback"
    TEXT_PLAIN    = "text_plain"


class DocumentExtractionResult(BaseModel):
    """Full result from POST /api/intake/document."""
    filename: str
    file_size_bytes: int
    extraction_method: ExtractionMethod
    extracted_text_preview: str = Field(
        description="First 500 chars of extracted text (for UI preview)"
    )
    extracted_text_length: int
    ubo_info: UBOInfo | None = None
    equity_stakes: list[EquityStake] = Field(default_factory=list)
    control_rights: ControlRights | None = None
    llm_model_used: str | None = None
    llm_structured: bool = Field(
        default=False,
        description="Whether LLM structuring was applied (false if no API key set)"
    )
    warnings: list[str] = Field(default_factory=list)
