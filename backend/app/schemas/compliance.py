"""
Sententia.ai — Compliance Gatekeeper Schemas

ComplianceInput:          Input parameters for a corridor compliance check.
PolicyViolation:          Single OPA policy finding (blocking or warning).
ComplianceResult:         Deterministic OPA/policy evaluation result (is_rule_validated=True).
UIBanner:                 Warning banner attached to all non-validated responses.
Illustrative*:            Schemas for LLM fallback output (is_rule_validated=False).
FallbackLLMOutput:        Instructor-structured LLM output for the fallback path.
FallbackComplianceResult: Full fallback result — always is_rule_validated=False.
ComplianceResponse:       Full HTTP response — one of result or fallback_result is populated.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, model_validator


# ══════════════════════════════════════════════════════════════════════════════
# INPUT
# ══════════════════════════════════════════════════════════════════════════════

class ComplianceInput(BaseModel):
    """
    Policy-relevant facts for a compliance evaluation.
    Designed to be derivable from the Prompt-4 structure output plus
    the original scenario inputs.
    """

    # ── Corridor identification ────────────────────────────────────────────────
    origin_jurisdiction: str = Field(
        ...,
        description="Origin country in UPPER_SNAKE_CASE, e.g. CHINA, UNITED_STATES, SAUDI_ARABIA",
        examples=["CHINA"],
    )
    target_jurisdiction: str = Field(
        ...,
        description="Target country in UPPER_SNAKE_CASE, e.g. INDIA, FRANCE, GERMANY",
        examples=["INDIA"],
    )
    spv_jurisdiction: str | None = Field(
        None,
        description="Intermediate SPV country in UPPER_SNAKE_CASE (optional)",
        examples=["SINGAPORE"],
    )
    sector: str = Field(..., description="Business sector or industry of the target company")
    investment_amount_usd: float = Field(..., gt=0, description="Investment amount in USD")
    equity_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Equity stake sought (%) in the target entity",
    )

    # ── India corridor — Press Note 3 / Press Note 2 ───────────────────────────
    prior_govt_approval_obtained: bool = Field(
        False,
        description="DPIIT Government Approval already obtained (India PN3 corridors)",
    )
    is_prohibited_sector: bool = Field(
        False,
        description="Whether the sector is prohibited for FDI in the target jurisdiction",
    )

    # ── India corridor — Section 9(1)(i) indirect transfer ────────────────────
    spv_india_asset_value_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Percentage of SPV fair market value attributable to Indian assets (for §9(1)(i) test)",
    )

    # ── UBO chain (optional — for granular land-border UBO look-through) ────────
    ubo_chain: list[dict[str, Any]] | None = Field(
        None,
        description=(
            "List of UBO entries: [{nationality: 'CHINA', ownership_pct: 75.0}, ...]. "
            "Used for PN3 UBO look-through analysis."
        ),
    )

    # ── US corridor — FATCA / PFIC / Cayman substance ─────────────────────────
    has_us_persons_in_fund: bool = Field(
        False,
        description="Whether the investing fund/entity has US persons as investors/owners",
    )
    fatca_compliant: bool | None = Field(
        None,
        description="Whether FATCA compliance has been addressed (None = unknown)",
    )
    cayman_has_substance: bool | None = Field(
        None,
        description="Whether the Cayman SPV meets Economic Substance Act 2019 requirements (None = unknown)",
    )
    spv_passive_asset_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Percentage of SPV assets that are passive (for PFIC §1297 test)",
    )

    # ── EU corridor — French Golden Powers / EU FDI Screening / Luxembourg ATAD ─
    target_sector_is_sensitive: bool = Field(
        False,
        description="Whether the target company's sector is strategically sensitive (triggers French/EU screening)",
    )
    french_golden_powers_notified: bool | None = Field(
        None,
        description="Whether French IEF authorization has been filed (None = unknown/not applicable)",
    )
    eu_fdi_screening_notified: bool | None = Field(
        None,
        description="Whether EU FDI Screening cooperation mechanism has been triggered (None = unknown)",
    )
    luxembourg_has_substance: bool | None = Field(
        None,
        description="Whether the Luxembourg SPV has genuine economic substance (None = unknown)",
    )
    lux_effective_tax_rate_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Effective corporate tax rate of the Luxembourg SPV (for Pillar Two check)",
    )
    is_dual_use_technology: bool = Field(
        False,
        description="Whether the investment involves dual-use technology subject to export control",
    )

    # ── Linkage to Prompt-4 output ─────────────────────────────────────────────
    scenario_id: str | None = Field(
        None,
        description="UUID of the scenario (from intake endpoint) — for audit trail linkage",
    )
    structure_rank: int | None = Field(
        None,
        ge=1,
        le=4,
        description="Rank of the structure alternative being checked (from Prompt-4 output)",
    )

    @model_validator(mode="after")
    def normalize_jurisdictions(self) -> "ComplianceInput":
        """Normalize jurisdiction names to UPPER_SNAKE_CASE for consistent matching."""
        self.origin_jurisdiction = self.origin_jurisdiction.upper().replace(" ", "_").replace("-", "_")
        self.target_jurisdiction = self.target_jurisdiction.upper().replace(" ", "_").replace("-", "_")
        if self.spv_jurisdiction:
            self.spv_jurisdiction = self.spv_jurisdiction.upper().replace(" ", "_").replace("-", "_")
        return self


# ══════════════════════════════════════════════════════════════════════════════
# POLICY FINDING TYPES
# ══════════════════════════════════════════════════════════════════════════════

class PolicyViolation(BaseModel):
    """Single policy finding returned by OPA or the Python-native evaluator."""

    code: str = Field(..., description="Machine-readable rule violation code")
    rule: str = Field(..., description="Human-readable rule name and legal citation")
    description: str = Field(..., description="Detailed explanation of the finding")
    severity: str = Field(
        ...,
        pattern="^(blocking|warning)$",
        description="'blocking' = prevents investment; 'warning' = flag for attention",
    )
    source: str = Field(..., description="Primary legal source cited")


# ══════════════════════════════════════════════════════════════════════════════
# COMPLIANCE EVALUATION RESULT
# ══════════════════════════════════════════════════════════════════════════════

class ComplianceResult(BaseModel):
    """
    Complete compliance evaluation result for a single corridor.
    Returned by the OPA/Python evaluator and surfaced in the API response.
    """

    # Corridor matched
    corridor_id: str
    corridor_name: str
    policy_package: str

    # Core decision
    is_rule_validated: bool = Field(
        ...,
        description=(
            "True if a pre-validated corridor Rego policy was found and evaluated deterministically. "
            "False only if no matching corridor exists (falls back to LLM-only analysis)."
        ),
    )
    is_allowed: bool = Field(
        ...,
        description="True if no blocking violations found — investment structurally permissible",
    )

    # Findings
    violations: list[PolicyViolation] = Field(default_factory=list)
    warnings: list[PolicyViolation] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)

    # Evaluation metadata
    evaluation_mode: str = Field(
        ...,
        description="'opa_server' | 'opa_subprocess' | 'python_native'",
    )
    evaluated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    blocking_count: int = 0
    warning_count: int = 0


# ══════════════════════════════════════════════════════════════════════════════
# FALLBACK SCHEMAS — LLM general-principles path (is_rule_validated=False)
# ══════════════════════════════════════════════════════════════════════════════

class UIBanner(BaseModel):
    """
    Warning banner attached to every fallback (non-validated) response.
    Must always be rendered prominently in the UI.
    """
    type: Literal["WARNING"] = "WARNING"
    label: str = "Illustrative — Not Yet Rule-Validated"
    message: str = Field(
        ...,
        description="Human-readable explanation of why this output is illustrative and what the user should do",
    )


class IllustrativeRiskItem(BaseModel):
    """
    A single risk flag generated by the LLM from general principles.
    Must NOT contain specific statute citations.
    """
    category: str = Field(
        ...,
        description="Risk category: regulatory | tax | structural | political | other",
    )
    description: str = Field(
        ...,
        description="What the risk is — use general language, not specific statutory references",
    )
    typical_pattern: str = Field(
        ...,
        description="What typically applies in similar investment contexts — 'most jurisdictions require...' style",
    )
    uncertainty_flag: str = Field(
        ...,
        description="Explicit statement of what is specifically uncertain or unverifiable for this corridor",
    )


class IllustrativeTouchpointItem(BaseModel):
    """
    A typical compliance touchpoint generated from general principles.
    Must NOT name specific filing forms unless universally known (e.g., 'central bank notification').
    """
    jurisdiction: str
    typical_requirement: str = Field(
        ...,
        description="Use 'typically requires' / 'commonly requires' language — no specific form numbers",
    )
    typical_authority: str = Field(
        ...,
        description="Type of authority, not specific office unless certain (e.g., 'investment promotion authority')",
    )
    uncertainty_flag: str = Field(
        ...,
        description="What about this touchpoint is uncertain for this specific corridor",
    )


class FallbackLLMOutput(BaseModel):
    """
    Instructor-enforced output schema for the LLM fallback path.
    Deliberately excludes any 'cited_sources' field to prevent hallucinated citations.
    """
    illustrative_risks: list[IllustrativeRiskItem] = Field(
        ...,
        min_length=2,
        max_length=8,
        description="2-8 risk items — general principles only, no specific statute citations",
    )
    illustrative_touchpoints: list[IllustrativeTouchpointItem] = Field(
        ...,
        min_length=2,
        max_length=6,
        description="2-6 typical compliance touchpoints for this corridor type",
    )
    general_analysis: str = Field(
        ...,
        min_length=100,
        description="Overall analysis paragraph using 'typically', 'commonly', 'general practice' language",
    )
    general_principles_applied: list[str] = Field(
        ...,
        min_length=2,
        max_length=8,
        description="List of general investment law principles used (e.g., 'Most FDI frameworks require pre-investment notification...')",
    )
    uncertainty_summary: str = Field(
        ...,
        min_length=50,
        description="Brief summary of what is unknown or unverifiable about this specific corridor",
    )


class FallbackComplianceResult(BaseModel):
    """
    Full result for the LLM fallback path.
    is_rule_validated is always False — this is the invariant.
    is_allowed is always None — cannot be determined without pre-validated rules.
    """
    is_rule_validated: bool = False
    is_allowed: None = Field(
        None,
        description="Cannot be determined without pre-validated Rego rules — always null for fallback",
    )
    illustrative_risks: list[IllustrativeRiskItem] = Field(default_factory=list)
    illustrative_touchpoints: list[IllustrativeTouchpointItem] = Field(default_factory=list)
    general_analysis: str = ""
    general_principles_applied: list[str] = Field(default_factory=list)
    uncertainty_summary: str = ""
    ui_banner: UIBanner
    rag_sources_used: int = 0
    llm_provider_used: str = "none"
    evaluation_mode: str = "llm_fallback"
    evaluated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ══════════════════════════════════════════════════════════════════════════════
# HTTP REQUEST / RESPONSE
# ══════════════════════════════════════════════════════════════════════════════

class ComplianceEvaluateRequest(BaseModel):
    """Request body for POST /api/compliance/evaluate."""

    compliance_input: ComplianceInput
    include_rag_context: bool = Field(
        False,
        description="If true, also run a RAG query and attach relevant regulatory context to the response",
    )


class ComplianceResponse(BaseModel):
    """
    HTTP response from POST /api/compliance/evaluate.

    Exactly one of result or fallback_result is populated:
      - corridor_matched=True  → result is populated (OPA deterministic evaluation)
      - corridor_matched=False → fallback_result is populated (LLM general-principles fallback)
    """
    corridor_matched: bool

    # Deterministic path (OPA) — populated when corridor_matched=True
    result: ComplianceResult | None = None

    # LLM fallback path — populated when corridor_matched=False
    # Always has is_rule_validated=False and ui_banner
    fallback_result: FallbackComplianceResult | None = None

    audit_log_id: str | None = Field(
        None,
        description="UUID of the audit_log entry written for this check (FR-4.3)",
    )
    rag_context: str | None = Field(
        None,
        description="Regulatory corpus context if include_rag_context=true",
    )
