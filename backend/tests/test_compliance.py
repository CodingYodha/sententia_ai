"""
Sententia.ai — Compliance Gatekeeper Tests

Coverage:
  TestCorridorRegistry      — YAML loading, matching logic, edge cases
  TestIndiaCorridor         — All Rego rule mirrors (PN3, §9(1)(i), SBO, POEM/PPT)
  TestUSCaymanIndiaCorridor — FATCA, substance, PFIC, §9(1)(i)
  TestGulfEUCorridor        — French Golden Powers, EU FDI Screening, ATAD, Pillar Two
  TestComplianceSchemas     — Pydantic validation
  TestComplianceEndpoint    — HTTP endpoint with audit log mock
  TestNoMatchResponse       — Unknown corridor returns correct no-match response

Run (no OPA server needed):
  conda run -n iitr pytest tests/test_compliance.py -v -m "not integration"

Run with OPA server (integration):
  conda run -n iitr pytest tests/test_compliance.py -v -m integration
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.compliance import (
    ComplianceInput,
    ComplianceEvaluateRequest,
    FallbackComplianceResult,
    FallbackLLMOutput,
    IllustrativeRiskItem,
    IllustrativeTouchpointItem,
    UIBanner,
)
from app.services.corridor_registry import (
    CorridorConfig,
    match_corridor,
    load_corridors,
    list_all_corridors,
)
from app.services.policy_evaluator import (
    IndiaCorridor,
    USCaymanIndia,
    GulfEU,
    get_evaluator,
    list_registered_packages,
)

client = TestClient(app)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def india_input(**kwargs) -> dict:
    defaults = {
        "origin_jurisdiction": "CHINA",
        "target_jurisdiction": "INDIA",
        "spv_jurisdiction": "SINGAPORE",
        "sector": "Technology",
        "investment_amount_usd": 50_000_000,
        "equity_pct": 49.0,
        "prior_govt_approval_obtained": False,
        "is_prohibited_sector": False,
        "spv_india_asset_value_pct": 30.0,
    }
    defaults.update(kwargs)
    return defaults


def us_cayman_input(**kwargs) -> dict:
    defaults = {
        "origin_jurisdiction": "UNITED_STATES",
        "target_jurisdiction": "INDIA",
        "spv_jurisdiction": "CAYMAN_ISLANDS",
        "sector": "SaaS",
        "investment_amount_usd": 20_000_000,
        "equity_pct": 25.0,
        "has_us_persons_in_fund": True,
        "fatca_compliant": True,
        "cayman_has_substance": True,
        "spv_india_asset_value_pct": 40.0,
        "spv_passive_asset_pct": 30.0,
    }
    defaults.update(kwargs)
    return defaults


def gulf_eu_input(**kwargs) -> dict:
    defaults = {
        "origin_jurisdiction": "SAUDI_ARABIA",
        "target_jurisdiction": "FRANCE",
        "spv_jurisdiction": "LUXEMBOURG",
        "sector": "Aerospace",
        "investment_amount_usd": 500_000_000,
        "equity_pct": 35.0,
        "target_sector_is_sensitive": True,
        "french_golden_powers_notified": True,
        "eu_fdi_screening_notified": True,
        "luxembourg_has_substance": True,
        "lux_effective_tax_rate_pct": 16.0,
    }
    defaults.update(kwargs)
    return defaults


def post_evaluate(compliance_input: dict, include_rag: bool = False) -> dict:
    """POST /api/compliance/evaluate with both audit log writers mocked."""
    with (
        patch("app.routers.compliance._write_audit_log", new_callable=AsyncMock,
              return_value="test-audit-uuid"),
        patch("app.routers.compliance._write_fallback_audit_log", new_callable=AsyncMock,
              return_value="test-audit-uuid"),
    ):
        resp = client.post(
            "/api/compliance/evaluate",
            json={"compliance_input": compliance_input, "include_rag_context": include_rag},
        )
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


def _make_fallback_llm_output(
    origin: str = "BRAZIL",
    target: str = "TURKEY",
    spv: str | None = "CAYMAN_ISLANDS",
) -> FallbackLLMOutput:
    """
    Build a realistic mock FallbackLLMOutput using CORRECT 'general-principles' language.
    Note: This mock intentionally uses 'typically', 'commonly', 'most jurisdictions' language
    and does NOT cite specific statute section/article numbers.
    """
    return FallbackLLMOutput(
        illustrative_risks=[
            IllustrativeRiskItem(
                category="regulatory",
                description=(
                    f"FDI into {target} may require notification to or approval from the "
                    "relevant investment screening authority, particularly for acquisitions "
                    "above a threshold ownership percentage."
                ),
                typical_pattern=(
                    "Most FDI frameworks in countries with active foreign investment regulation "
                    "require some form of pre-investment notification or sector-specific approval "
                    "for equity stakes above approximately 10-25% in strategic industries."
                ),
                uncertainty_flag=(
                    f"The specific threshold, applicable authority, and whether the "
                    f"{spv or 'direct'} SPV structure affects the characterization of "
                    f"the investment as {origin}-origin are not pre-validated for this corridor."
                ),
            ),
            IllustrativeRiskItem(
                category="tax",
                description=(
                    "The intermediate SPV jurisdiction may face treaty benefit scrutiny under "
                    "general anti-avoidance principles applicable in both the origin and target "
                    "jurisdictions."
                ),
                typical_pattern=(
                    "Most modern tax treaties and domestic anti-avoidance provisions subject "
                    "interposed holding companies to substance and principal purpose tests before "
                    "allowing reduced withholding rates on dividends or capital gains."
                ),
                uncertainty_flag=(
                    f"The specific treaty network between {origin}, {spv or 'N/A'}, and {target}, "
                    "the applicable substance requirements, and any GAAR provisions in force "
                    "are not pre-validated for this corridor."
                ),
            ),
        ],
        illustrative_touchpoints=[
            IllustrativeTouchpointItem(
                jurisdiction=target,
                typical_requirement=(
                    "Typically requires registration of foreign investment with the investment "
                    "promotion authority or central bank, and may require sector-specific "
                    "regulatory clearance for ownership above standard thresholds."
                ),
                typical_authority="Investment promotion authority / central bank / sector regulator",
                uncertainty_flag=(
                    f"Precise filing requirements, timelines, and applicable investment limits "
                    f"for {origin}-origin capital in {target} are not pre-validated in this system."
                ),
            ),
            IllustrativeTouchpointItem(
                jurisdiction=origin,
                typical_requirement=(
                    "Outbound capital typically requires notification to or approval from the "
                    "central bank or foreign exchange control authority in the origin jurisdiction."
                ),
                typical_authority="Central bank / foreign exchange control authority",
                uncertainty_flag=(
                    f"The specific outbound capital control requirements for {origin} investors "
                    "are not pre-validated and may vary depending on current exchange control regulations."
                ),
            ),
        ],
        general_analysis=(
            f"This is an illustrative general-principles analysis for a "
            f"{origin} → {spv or 'direct'} → {target} corridor that does not have a "
            f"pre-validated compliance policy in Sententia's rule engine. "
            f"This output is based on general international investment law principles "
            f"and typical FDI framework patterns. Local qualified counsel in each "
            f"jurisdiction must be engaged before relying on this analysis for any "
            f"legal or commercial decision. "
            f"The {target} regulatory environment for foreign investors should be "
            f"assessed in detail with reference to current applicable law."
        ),
        general_principles_applied=[
            "Most FDI frameworks require some form of pre-investment notification or registration with the relevant authority",
            "Intermediate SPV jurisdictions must typically satisfy economic substance tests to access treaty benefits",
            "Strategic sector investments typically attract additional regulatory scrutiny beyond standard FDI rules",
        ],
        uncertainty_summary=(
            f"This corridor ({origin} → {spv or 'direct'} → {target}) is not pre-validated. "
            f"Specific statutory requirements, applicable bilateral investment treaty provisions, "
            f"and current regulatory thresholds for this pairing are all unverified in this system."
        ),
    )


def post_evaluate_with_fallback_mock(
    compliance_input: dict,
    mock_output: FallbackLLMOutput | None = None,
) -> dict:
    """
    POST /api/compliance/evaluate for a novel (unvalidated) corridor,
    with the LLM fallback mocked to return a controlled FallbackLLMOutput.
    Also mocks the fallback audit log writer.
    """
    origin = compliance_input.get("origin_jurisdiction", "BRAZIL")
    target = compliance_input.get("target_jurisdiction", "TURKEY")
    spv    = compliance_input.get("spv_jurisdiction")

    if mock_output is None:
        mock_output = _make_fallback_llm_output(origin=origin, target=target, spv=spv)

    with (
        patch("app.routers.compliance._write_fallback_audit_log", new_callable=AsyncMock,
              return_value="test-fallback-audit-uuid"),
        patch(
            "app.services.compliance_fallback_service.run_llm_fallback",
            new_callable=AsyncMock,
        ) as mock_fallback,
    ):
        # Build the FallbackComplianceResult that run_llm_fallback would return
        from app.services.fallback_prompts import build_banner_message
        from app.schemas.compliance import ComplianceInput as CI
        ci = CI(**compliance_input)
        banner_msg = build_banner_message(ci, mock_output.uncertainty_summary)
        mock_fallback.return_value = FallbackComplianceResult(
            is_rule_validated=False,
            illustrative_risks=mock_output.illustrative_risks,
            illustrative_touchpoints=mock_output.illustrative_touchpoints,
            general_analysis=mock_output.general_analysis,
            general_principles_applied=mock_output.general_principles_applied,
            uncertainty_summary=mock_output.uncertainty_summary,
            ui_banner=UIBanner(
                type="WARNING",
                label="Illustrative \u2014 Not Yet Rule-Validated",
                message=banner_msg,
            ),
            rag_sources_used=3,
            llm_provider_used="openrouter",
            evaluation_mode="llm_fallback",
        )

        resp = client.post(
            "/api/compliance/evaluate",
            json={"compliance_input": compliance_input},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# 1. CORRIDOR REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

class TestCorridorRegistry:

    def test_corridors_yaml_loads(self):
        corridors = load_corridors()
        assert len(corridors) >= 3, "Expected at least 3 active corridors"

    def test_corridor_has_required_fields(self):
        for c in load_corridors():
            assert c.id
            assert c.name
            assert c.origin_jurisdictions
            assert c.target_jurisdictions
            assert c.policy_package
            assert c.rego_file

    def test_match_china_singapore_india(self):
        c = match_corridor("CHINA", "INDIA", "SINGAPORE")
        assert c is not None
        assert c.policy_package == "sententia.corridors.india"

    def test_match_china_direct_india(self):
        c = match_corridor("CHINA", "INDIA", None)
        assert c is not None
        assert c.policy_package == "sententia.corridors.india"

    def test_match_us_cayman_india(self):
        c = match_corridor("UNITED_STATES", "INDIA", "CAYMAN_ISLANDS")
        assert c is not None
        assert c.policy_package == "sententia.corridors.us_cayman_india"

    def test_match_saudi_luxembourg_france(self):
        c = match_corridor("SAUDI_ARABIA", "FRANCE", "LUXEMBOURG")
        assert c is not None
        assert c.policy_package == "sententia.corridors.gulf_eu"

    def test_match_uae_luxembourg_france(self):
        """Gulf states are listed — UAE should also match gulf_eu corridor."""
        c = match_corridor("UAE", "FRANCE", "LUXEMBOURG")
        assert c is not None
        assert c.policy_package == "sententia.corridors.gulf_eu"

    def test_no_match_unknown_corridor(self):
        c = match_corridor("JAPAN", "VIETNAM", "UNITED_KINGDOM")
        assert c is None

    def test_no_match_wrong_target(self):
        c = match_corridor("CHINA", "GERMANY", "SINGAPORE")
        assert c is None

    def test_match_case_insensitive(self):
        """Matching must work regardless of input casing."""
        c = match_corridor("china", "india", "singapore")
        assert c is not None

    def test_match_with_spaces(self):
        """'United States' should normalize to 'UNITED_STATES'."""
        c = match_corridor("United States", "India", "Cayman Islands")
        assert c is not None

    def test_list_all_corridors_returns_list(self):
        corridors = list_all_corridors()
        assert isinstance(corridors, list)
        assert len(corridors) >= 3

    def test_list_all_corridors_has_required_keys(self):
        for c in list_all_corridors():
            assert "id" in c
            assert "name" in c
            assert "policy_package" in c
            assert "status" in c


# ══════════════════════════════════════════════════════════════════════════════
# 2. INDIA CORRIDOR POLICY (Python-native evaluator)
# ══════════════════════════════════════════════════════════════════════════════

class TestIndiaCorridor:
    """Tests for IndiaCorridor Python evaluator — mirrors india_corridor.rego"""

    ev = IndiaCorridor()

    # ── PN3 rules ─────────────────────────────────────────────────────────────

    def test_pn3_blocks_unapproved_china_fdi(self):
        """PN3_NO_PRIOR_APPROVAL: China origin, no approval → BLOCKING."""
        result = self.ev.evaluate(india_input(
            prior_govt_approval_obtained=False
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PN3_NO_PRIOR_APPROVAL" in codes
        assert any(v["severity"] == "blocking" for v in result["violations"])
        assert result["allow"] is False

    def test_pn3_allows_approved_china_fdi(self):
        """PN3_APPROVAL_SCOPE_VERIFY: Approval obtained → WARNING (not blocking) → allowed."""
        result = self.ev.evaluate(india_input(
            prior_govt_approval_obtained=True,
            spv_india_asset_value_pct=30.0,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PN3_APPROVAL_SCOPE_VERIFY" in codes
        assert not any(v["severity"] == "blocking" for v in result["violations"])
        assert result["allow"] is True

    def test_pn3_non_land_border_not_blocked(self):
        """US origin: not a land-border country — no PN3 violation."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            prior_govt_approval_obtained=False,
            spv_india_asset_value_pct=30.0,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PN3_NO_PRIOR_APPROVAL" not in codes
        assert "PN3_UBO_LAND_BORDER" not in codes

    def test_pn3_ubo_look_through(self):
        """PN3_UBO_LAND_BORDER: US origin but PRC UBO in chain → BLOCKING."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            prior_govt_approval_obtained=False,
            ubo_chain=[
                {"nationality": "CHINA", "ownership_pct": 60.0},
            ],
            spv_india_asset_value_pct=30.0,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PN3_UBO_LAND_BORDER" in codes
        assert result["allow"] is False

    def test_pn3_other_land_border_countries(self):
        """Pakistan is also a land-border country — PN3 applies."""
        for country in ["PAKISTAN", "BANGLADESH", "NEPAL"]:
            result = self.ev.evaluate(india_input(
                origin_jurisdiction=country,
                prior_govt_approval_obtained=False,
            ))
            codes = [v["code"] for v in result["violations"]]
            assert "PN3_NO_PRIOR_APPROVAL" in codes, f"Expected PN3 for {country}"

    # ── Section 9(1)(i) rules ─────────────────────────────────────────────────

    def test_s9_indirect_transfer_warning_at_51_pct(self):
        """S9_INDIRECT_TRANSFER_RISK: SPV >50% India assets → WARNING."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            prior_govt_approval_obtained=False,
            spv_india_asset_value_pct=75.0,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "S9_INDIRECT_TRANSFER_RISK" in codes
        # Should be warning, not blocking
        risk = next(v for v in result["violations"] if v["code"] == "S9_INDIRECT_TRANSFER_RISK")
        assert risk["severity"] == "warning"

    def test_s9_no_warning_at_50_pct_or_below(self):
        """S9: Exactly 50% is NOT above the threshold — no warning."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            prior_govt_approval_obtained=False,
            spv_india_asset_value_pct=50.0,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "S9_INDIRECT_TRANSFER_RISK" not in codes

    def test_s9_form_3ct_added_when_triggered(self):
        """Form 3CT is added to required_approvals when §9(1)(i) is triggered."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            spv_india_asset_value_pct=80.0,
        ))
        assert any("3CT" in a for a in result["required_approvals"])

    # ── SBO / Companies Act §90 rules ─────────────────────────────────────────

    def test_sbo_ben1_required_at_10_pct(self):
        """BEN-1 and BEN-2 required when equity ≥10%."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            equity_pct=10.0,
        ))
        assert any("BEN-1" in a for a in result["required_approvals"])
        assert any("BEN-2" in a for a in result["required_approvals"])

    def test_sbo_not_required_below_10_pct(self):
        """BEN-1/BEN-2 not required below 10% equity."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            equity_pct=9.0,
        ))
        assert not any("BEN-1" in a for a in result["required_approvals"])

    def test_fcgpr_always_required(self):
        """FC-GPR is always required for India target."""
        result = self.ev.evaluate(india_input(origin_jurisdiction="UNITED_STATES"))
        assert any("FC-GPR" in a for a in result["required_approvals"])

    # ── Prohibited sector ──────────────────────────────────────────────────────

    def test_prohibited_sector_blocks(self):
        """PROHIBITED_SECTOR: blocking regardless of other approvals."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            is_prohibited_sector=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PROHIBITED_SECTOR" in codes
        assert result["allow"] is False

    # ── Singapore SPV POEM/PPT ────────────────────────────────────────────────

    def test_singapore_spv_poem_ppt_warning(self):
        """SINGAPORE_SPV_POEM_PPT_RISK: always warn when SPV is Singapore."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            spv_jurisdiction="SINGAPORE",
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "SINGAPORE_SPV_POEM_PPT_RISK" in codes

    def test_no_poem_warning_for_other_spvs(self):
        """POEM/PPT warning only for Singapore, not for other SPVs."""
        result = self.ev.evaluate(india_input(
            origin_jurisdiction="UNITED_STATES",
            spv_jurisdiction="MAURITIUS",
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "SINGAPORE_SPV_POEM_PPT_RISK" not in codes

    # ── Sources ────────────────────────────────────────────────────────────────

    def test_violations_have_source_citations(self):
        """All violations must include a source citation."""
        result = self.ev.evaluate(india_input(
            prior_govt_approval_obtained=False,
            spv_india_asset_value_pct=80.0,
        ))
        for v in result["violations"]:
            assert v.get("source") and len(v["source"]) > 5, f"Missing source on: {v['code']}"


# ══════════════════════════════════════════════════════════════════════════════
# 3. US → CAYMAN → INDIA CORRIDOR (Python-native evaluator)
# ══════════════════════════════════════════════════════════════════════════════

class TestUSCaymanIndiaCorridor:
    """Tests for USCaymanIndia Python evaluator — mirrors us_cayman_india.rego"""

    ev = USCaymanIndia()

    def test_fatca_non_compliant_is_blocking(self):
        """FATCA_NON_COMPLIANCE: US persons + fatca_compliant=False → BLOCKING."""
        result = self.ev.evaluate(us_cayman_input(
            fatca_compliant=False,
            cayman_has_substance=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "FATCA_NON_COMPLIANCE" in codes
        assert result["allow"] is False

    def test_fatca_compliant_no_blocking(self):
        """FATCA compliant → no FATCA blocking violation."""
        result = self.ev.evaluate(us_cayman_input(
            fatca_compliant=True,
            cayman_has_substance=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "FATCA_NON_COMPLIANCE" not in codes
        assert result["allow"] is True

    def test_fatca_status_unknown_is_warning(self):
        """FATCA_STATUS_UNVERIFIED: US persons + fatca_compliant=None → WARNING."""
        result = self.ev.evaluate(us_cayman_input(
            fatca_compliant=None,
            cayman_has_substance=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "FATCA_STATUS_UNVERIFIED" in codes
        warning = next(v for v in result["violations"] if v["code"] == "FATCA_STATUS_UNVERIFIED")
        assert warning["severity"] == "warning"
        # Warning does not block
        assert result["allow"] is True

    def test_no_fatca_without_us_persons(self):
        """No US persons in fund → no FATCA violation at all."""
        result = self.ev.evaluate(us_cayman_input(
            has_us_persons_in_fund=False,
            fatca_compliant=None,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "FATCA_NON_COMPLIANCE" not in codes
        assert "FATCA_STATUS_UNVERIFIED" not in codes

    def test_cayman_substance_deficient_warning(self):
        """CAYMAN_SUBSTANCE_DEFICIENT: cayman_has_substance=False → WARNING."""
        result = self.ev.evaluate(us_cayman_input(
            fatca_compliant=True,
            cayman_has_substance=False,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "CAYMAN_SUBSTANCE_DEFICIENT" in codes
        v = next(x for x in result["violations"] if x["code"] == "CAYMAN_SUBSTANCE_DEFICIENT")
        assert v["severity"] == "warning"
        assert result["allow"] is True  # Warning, not blocking

    def test_pfic_warning_at_50_pct_passive(self):
        """PFIC_PASSIVE_ASSET_RISK: ≥50% passive assets + US persons → WARNING."""
        result = self.ev.evaluate(us_cayman_input(
            fatca_compliant=True,
            cayman_has_substance=True,
            spv_passive_asset_pct=60.0,
            has_us_persons_in_fund=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PFIC_PASSIVE_ASSET_RISK" in codes

    def test_pfic_no_warning_below_50_pct(self):
        """PFIC: <50% passive assets → no warning."""
        result = self.ev.evaluate(us_cayman_input(
            fatca_compliant=True,
            cayman_has_substance=True,
            spv_passive_asset_pct=45.0,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PFIC_PASSIVE_ASSET_RISK" not in codes

    def test_pfic_no_warning_without_us_persons(self):
        """PFIC risk only applies when there are US persons in the fund."""
        result = self.ev.evaluate(us_cayman_input(
            has_us_persons_in_fund=False,
            spv_passive_asset_pct=80.0,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PFIC_PASSIVE_ASSET_RISK" not in codes

    def test_s9_indirect_transfer_warning(self):
        """S9_INDIRECT_TRANSFER_RISK: Cayman SPV >50% India assets → WARNING."""
        result = self.ev.evaluate(us_cayman_input(
            fatca_compliant=True,
            cayman_has_substance=True,
            spv_india_asset_value_pct=65.0,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "S9_INDIRECT_TRANSFER_RISK" in codes

    def test_us_not_pn3_restricted(self):
        """US origin: PN3 should NOT apply (US is not a land-border country)."""
        result = self.ev.evaluate(us_cayman_input())
        codes = [v["code"] for v in result["violations"]]
        assert "PN3_NO_PRIOR_APPROVAL" not in codes

    def test_fcgpr_always_required(self):
        """FC-GPR is always required for India target."""
        result = self.ev.evaluate(us_cayman_input())
        assert any("FC-GPR" in a for a in result["required_approvals"])

    def test_fatca_filing_required_with_us_persons(self):
        """FATCA compliance listed in required_approvals when US persons in fund."""
        result = self.ev.evaluate(us_cayman_input(has_us_persons_in_fund=True))
        assert any("FATCA" in a or "Form 8621" in a for a in result["required_approvals"])

    def test_clean_us_cayman_india_allowed(self):
        """Fully compliant US-Cayman-India structure → allowed with warnings."""
        result = self.ev.evaluate(us_cayman_input(
            fatca_compliant=True,
            cayman_has_substance=True,
            spv_india_asset_value_pct=30.0,
            spv_passive_asset_pct=30.0,
            is_prohibited_sector=False,
        ))
        assert result["allow"] is True


# ══════════════════════════════════════════════════════════════════════════════
# 4. GULF → LUXEMBOURG → FRANCE CORRIDOR (Python-native evaluator)
# ══════════════════════════════════════════════════════════════════════════════

class TestGulfEUCorridor:
    """Tests for GulfEU Python evaluator — mirrors gulf_eu.rego"""

    ev = GulfEU()

    def test_french_golden_powers_blocks_unapproved_sensitive_sector(self):
        """FRENCH_GOLDEN_POWERS_REQUIRED: sensitive sector, not notified → BLOCKING."""
        result = self.ev.evaluate(gulf_eu_input(
            target_sector_is_sensitive=True,
            french_golden_powers_notified=False,
            eu_fdi_screening_notified=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "FRENCH_GOLDEN_POWERS_REQUIRED" in codes
        assert result["allow"] is False

    def test_french_golden_powers_allows_when_notified(self):
        """Golden Powers authorized → no blocking."""
        result = self.ev.evaluate(gulf_eu_input(
            target_sector_is_sensitive=True,
            french_golden_powers_notified=True,
            eu_fdi_screening_notified=True,
            luxembourg_has_substance=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "FRENCH_GOLDEN_POWERS_REQUIRED" not in codes
        assert result["allow"] is True

    def test_golden_powers_sector_verify_warning_for_unclear_sector(self):
        """FRENCH_GOLDEN_POWERS_SECTOR_VERIFY: non-sensitive sector → WARNING."""
        result = self.ev.evaluate(gulf_eu_input(
            sector="Hospitality",
            target_sector_is_sensitive=False,
            french_golden_powers_notified=None,
            eu_fdi_screening_notified=True,
            luxembourg_has_substance=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "FRENCH_GOLDEN_POWERS_SECTOR_VERIFY" in codes
        v = next(x for x in result["violations"] if x["code"] == "FRENCH_GOLDEN_POWERS_SECTOR_VERIFY")
        assert v["severity"] == "warning"

    def test_sensitive_sectors_trigger_golden_powers(self):
        """All listed sensitive sectors trigger Golden Powers."""
        for sector in ["Aerospace", "Defense", "Artificial_Intelligence", "Semiconductors"]:
            result = self.ev.evaluate(gulf_eu_input(
                sector=sector,
                target_sector_is_sensitive=False,
                french_golden_powers_notified=False,
                eu_fdi_screening_notified=True,
            ))
            codes = [v["code"] for v in result["violations"]]
            assert "FRENCH_GOLDEN_POWERS_REQUIRED" in codes, f"Expected Golden Powers for {sector}"

    def test_eu_fdi_screening_blocks_when_not_notified(self):
        """EU_FDI_SCREENING_REQUIRED: French target, not notified → BLOCKING."""
        result = self.ev.evaluate(gulf_eu_input(
            eu_fdi_screening_notified=False,
            french_golden_powers_notified=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "EU_FDI_SCREENING_REQUIRED" in codes
        assert result["allow"] is False

    def test_eu_fdi_screening_status_unknown_warning(self):
        """EU_FDI_SCREENING_STATUS_UNKNOWN: not notified, status unknown → WARNING."""
        result = self.ev.evaluate(gulf_eu_input(
            eu_fdi_screening_notified=None,
            french_golden_powers_notified=True,
            luxembourg_has_substance=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "EU_FDI_SCREENING_STATUS_UNKNOWN" in codes
        v = next(x for x in result["violations"] if x["code"] == "EU_FDI_SCREENING_STATUS_UNKNOWN")
        assert v["severity"] == "warning"

    def test_luxembourg_atad_substance_warning(self):
        """LUX_ATAD_SUBSTANCE_RISK: Luxembourg SPV, no substance → WARNING."""
        result = self.ev.evaluate(gulf_eu_input(
            luxembourg_has_substance=False,
            french_golden_powers_notified=True,
            eu_fdi_screening_notified=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "LUX_ATAD_SUBSTANCE_RISK" in codes
        v = next(x for x in result["violations"] if x["code"] == "LUX_ATAD_SUBSTANCE_RISK")
        assert v["severity"] == "warning"
        # Warning should not block
        assert result["allow"] is True

    def test_pillar_two_warning_below_15_pct(self):
        """PILLAR_TWO_BELOW_MINIMUM_RATE: effective rate < 15% → WARNING."""
        result = self.ev.evaluate(gulf_eu_input(
            lux_effective_tax_rate_pct=9.0,
            french_golden_powers_notified=True,
            eu_fdi_screening_notified=True,
            luxembourg_has_substance=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PILLAR_TWO_BELOW_MINIMUM_RATE" in codes

    def test_pillar_two_no_warning_at_15_pct(self):
        """Pillar Two: exactly 15% → no warning."""
        result = self.ev.evaluate(gulf_eu_input(
            lux_effective_tax_rate_pct=15.0,
            french_golden_powers_notified=True,
            eu_fdi_screening_notified=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "PILLAR_TWO_BELOW_MINIMUM_RATE" not in codes

    def test_dac6_warning_for_gulf_lux_france_structure(self):
        """DAC6_MANDATORY_DISCLOSURE: Gulf → Luxembourg → France → WARNING."""
        result = self.ev.evaluate(gulf_eu_input(
            french_golden_powers_notified=True,
            eu_fdi_screening_notified=True,
        ))
        codes = [v["code"] for v in result["violations"]]
        assert "DAC6_MANDATORY_DISCLOSURE" in codes

    def test_ief_authorization_in_required_approvals_when_blocking(self):
        """French IEF authorization listed in required_approvals when Golden Powers triggered."""
        result = self.ev.evaluate(gulf_eu_input(
            target_sector_is_sensitive=True,
            french_golden_powers_notified=False,
            eu_fdi_screening_notified=True,
        ))
        assert any("IEF" in a or "Investissements Étrangers" in a for a in result["required_approvals"])

    def test_eu_fdi_notification_in_required_approvals(self):
        """EU FDI Screening notification always in required_approvals for France target."""
        result = self.ev.evaluate(gulf_eu_input(
            french_golden_powers_notified=False,
            eu_fdi_screening_notified=False,
        ))
        assert any("FDI Screening" in a or "2019/452" in a for a in result["required_approvals"])

    def test_fully_compliant_gulf_eu_allowed(self):
        """Fully compliant Gulf-EU structure → allowed (warnings remain)."""
        result = self.ev.evaluate(gulf_eu_input(
            target_sector_is_sensitive=True,
            french_golden_powers_notified=True,
            eu_fdi_screening_notified=True,
            luxembourg_has_substance=True,
            lux_effective_tax_rate_pct=16.0,
        ))
        assert result["allow"] is True

    def test_gulf_states_all_match(self):
        """All Gulf states listed in corridors.yaml should match the gulf_eu corridor."""
        for origin in ["SAUDI_ARABIA", "UAE", "QATAR", "KUWAIT", "BAHRAIN", "OMAN"]:
            c = match_corridor(origin, "FRANCE", "LUXEMBOURG")
            assert c is not None, f"Expected match for {origin}"
            assert c.policy_package == "sententia.corridors.gulf_eu"


# ══════════════════════════════════════════════════════════════════════════════
# 5. COMPLIANCE SCHEMAS
# ══════════════════════════════════════════════════════════════════════════════

class TestComplianceSchemas:

    def test_compliance_input_normalizes_jurisdictions(self):
        """origin/target/spv are normalized to UPPER_SNAKE_CASE."""
        ci = ComplianceInput(
            origin_jurisdiction="china",
            target_jurisdiction="India",
            spv_jurisdiction="Singapore",
            sector="Tech",
            investment_amount_usd=1e6,
        )
        assert ci.origin_jurisdiction == "CHINA"
        assert ci.target_jurisdiction == "INDIA"
        assert ci.spv_jurisdiction == "SINGAPORE"

    def test_compliance_input_normalizes_dashes_and_spaces(self):
        """'United States' and 'Cayman-Islands' should normalize correctly."""
        ci = ComplianceInput(
            origin_jurisdiction="United States",
            target_jurisdiction="India",
            spv_jurisdiction="Cayman-Islands",
            sector="Tech",
            investment_amount_usd=1e6,
        )
        assert ci.origin_jurisdiction == "UNITED_STATES"
        assert ci.spv_jurisdiction == "CAYMAN_ISLANDS"

    def test_compliance_input_equity_pct_range(self):
        """equity_pct must be 0-100."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ComplianceInput(
                origin_jurisdiction="CHINA",
                target_jurisdiction="INDIA",
                sector="Tech",
                investment_amount_usd=1e6,
                equity_pct=110.0,  # out of range
            )

    def test_compliance_input_investment_amount_gt_zero(self):
        """investment_amount_usd must be > 0."""
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ComplianceInput(
                origin_jurisdiction="CHINA",
                target_jurisdiction="INDIA",
                sector="Tech",
                investment_amount_usd=0,  # not > 0
            )

    def test_compliance_evaluate_request_valid(self):
        ci = ComplianceInput(**india_input())
        req = ComplianceEvaluateRequest(compliance_input=ci)
        assert req.include_rag_context is False


# ══════════════════════════════════════════════════════════════════════════════
# 6. COMPLIANCE ENDPOINT (HTTP)
# ══════════════════════════════════════════════════════════════════════════════

class TestComplianceEndpoint:

    def test_india_corridor_returns_200(self):
        data = post_evaluate(india_input())
        assert data is not None

    def test_india_corridor_matched(self):
        data = post_evaluate(india_input())
        assert data["corridor_matched"] is True

    def test_india_corridor_is_rule_validated(self):
        data = post_evaluate(india_input())
        assert data["result"]["is_rule_validated"] is True

    def test_india_blocking_without_approval(self):
        data = post_evaluate(india_input(prior_govt_approval_obtained=False))
        assert data["result"]["is_allowed"] is False
        assert len(data["result"]["violations"]) > 0

    def test_india_allowed_with_approval(self):
        data = post_evaluate(india_input(
            prior_govt_approval_obtained=True,
            spv_india_asset_value_pct=30.0,
        ))
        assert data["result"]["is_allowed"] is True

    def test_india_has_required_approvals(self):
        data = post_evaluate(india_input())
        assert len(data["result"]["required_approvals"]) > 0

    def test_india_has_evaluation_mode(self):
        data = post_evaluate(india_input())
        assert data["result"]["evaluation_mode"] in ["opa_server", "opa_subprocess", "python_native"]

    def test_india_has_evaluated_at(self):
        data = post_evaluate(india_input())
        assert data["result"]["evaluated_at"]

    def test_india_has_blocking_and_warning_counts(self):
        data = post_evaluate(india_input(prior_govt_approval_obtained=False))
        assert data["result"]["blocking_count"] >= 1
        assert isinstance(data["result"]["warning_count"], int)

    def test_us_cayman_india_corridor_matched(self):
        data = post_evaluate(us_cayman_input())
        assert data["corridor_matched"] is True
        assert data["result"]["policy_package"] == "sententia.corridors.us_cayman_india"

    def test_gulf_eu_corridor_matched(self):
        data = post_evaluate(gulf_eu_input())
        assert data["corridor_matched"] is True
        assert data["result"]["policy_package"] == "sententia.corridors.gulf_eu"

    def test_gulf_eu_blocking_without_golden_powers(self):
        data = post_evaluate(gulf_eu_input(
            target_sector_is_sensitive=True,
            french_golden_powers_notified=False,
        ))
        assert data["result"]["is_allowed"] is False

    def test_violations_have_required_fields(self):
        """Each violation in HTTP response has code, rule, description, severity, source."""
        data = post_evaluate(india_input(prior_govt_approval_obtained=False))
        for v in data["result"]["violations"]:
            assert v["code"]
            assert v["rule"]
            assert v["description"]
            assert v["severity"] in ["blocking", "warning"]
            assert v["source"]

    def test_audit_log_id_returned(self):
        """Audit log ID is returned in the response when audit write succeeds."""
        data = post_evaluate(india_input())
        assert data["audit_log_id"] == "test-audit-uuid"

    def test_missing_required_field_returns_422(self):
        """Missing 'sector' → 422 Unprocessable Entity."""
        resp = client.post(
            "/api/compliance/evaluate",
            json={
                "compliance_input": {
                    "origin_jurisdiction": "CHINA",
                    "target_jurisdiction": "INDIA",
                    # sector missing
                    "investment_amount_usd": 50_000_000,
                }
            },
        )
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# 7. NO-MATCH RESPONSE
# ══════════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════════
# 7. LLM FALLBACK PATH — GENERAL STRUCTURAL TESTS
# (apply to ALL fallback responses regardless of corridor)
# ══════════════════════════════════════════════════════════════════════════════

_SAMPLE_NOVEL_INPUT = {
    "origin_jurisdiction": "BRAZIL",
    "target_jurisdiction": "TURKEY",
    "spv_jurisdiction": "CAYMAN_ISLANDS",
    "sector": "Infrastructure",
    "investment_amount_usd": 75_000_000,
    "equity_pct": 30.0,
}


class TestFallbackStructural:
    """Tests that verify the structural guarantees of the fallback path."""

    def test_fallback_returns_200(self):
        """Novel corridor always returns HTTP 200 — never a crash."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data is not None

    def test_fallback_corridor_matched_false(self):
        """Novel corridor: corridor_matched is always False."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["corridor_matched"] is False

    def test_fallback_result_field_is_null(self):
        """Deterministic OPA result is null for fallback path."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["result"] is None

    def test_fallback_result_present(self):
        """fallback_result is populated for novel corridors."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["fallback_result"] is not None

    def test_fallback_is_rule_validated_always_false(self):
        """INVARIANT: is_rule_validated must ALWAYS be False for fallback."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["fallback_result"]["is_rule_validated"] is False

    def test_fallback_is_allowed_always_null(self):
        """INVARIANT: is_allowed must ALWAYS be null for fallback (cannot determine without rules)."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["fallback_result"]["is_allowed"] is None

    def test_fallback_ui_banner_always_present(self):
        """INVARIANT: ui_banner MUST always be present in the fallback response."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["fallback_result"]["ui_banner"] is not None

    def test_fallback_ui_banner_type_is_warning(self):
        """ui_banner.type must always be 'WARNING'."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["fallback_result"]["ui_banner"]["type"] == "WARNING"

    def test_fallback_ui_banner_label_correct(self):
        """ui_banner.label must always be 'Illustrative \u2014 Not Yet Rule-Validated'."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["fallback_result"]["ui_banner"]["label"] == "Illustrative \u2014 Not Yet Rule-Validated"

    def test_fallback_ui_banner_message_not_empty(self):
        """ui_banner.message must be a non-empty string."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        msg = data["fallback_result"]["ui_banner"]["message"]
        assert isinstance(msg, str) and len(msg) > 20

    def test_fallback_has_illustrative_risks(self):
        """fallback_result must have at least one illustrative risk."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        risks = data["fallback_result"]["illustrative_risks"]
        assert isinstance(risks, list) and len(risks) >= 1

    def test_fallback_has_illustrative_touchpoints(self):
        """fallback_result must have at least one illustrative touchpoint."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        tps = data["fallback_result"]["illustrative_touchpoints"]
        assert isinstance(tps, list) and len(tps) >= 1

    def test_fallback_has_general_analysis(self):
        """general_analysis must be a non-empty string."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        analysis = data["fallback_result"]["general_analysis"]
        assert isinstance(analysis, str) and len(analysis) >= 50

    def test_fallback_has_general_principles(self):
        """general_principles_applied must be a list with at least one entry."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        principles = data["fallback_result"]["general_principles_applied"]
        assert isinstance(principles, list) and len(principles) >= 1

    def test_fallback_has_uncertainty_summary(self):
        """uncertainty_summary must be a non-empty string."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        summary = data["fallback_result"]["uncertainty_summary"]
        assert isinstance(summary, str) and len(summary) >= 20

    def test_fallback_has_evaluation_mode(self):
        """evaluation_mode must indicate llm_fallback."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        mode = data["fallback_result"]["evaluation_mode"]
        assert "fallback" in mode

    def test_fallback_risks_have_required_fields(self):
        """Each risk item must have category, description, typical_pattern, uncertainty_flag."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        for risk in data["fallback_result"]["illustrative_risks"]:
            assert risk["category"], f"Missing category: {risk}"
            assert risk["description"], f"Missing description: {risk}"
            assert risk["typical_pattern"], f"Missing typical_pattern: {risk}"
            assert risk["uncertainty_flag"], f"Missing uncertainty_flag: {risk}"

    def test_fallback_touchpoints_have_required_fields(self):
        """Each touchpoint must have jurisdiction, typical_requirement, typical_authority, uncertainty_flag."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        for tp in data["fallback_result"]["illustrative_touchpoints"]:
            assert tp["jurisdiction"]
            assert tp["typical_requirement"]
            assert tp["typical_authority"]
            assert tp["uncertainty_flag"]

    def test_fallback_audit_id_returned(self):
        """Fallback path also returns an audit_log_id."""
        data = post_evaluate_with_fallback_mock(_SAMPLE_NOVEL_INPUT)
        assert data["audit_log_id"] == "test-fallback-audit-uuid"

    def test_corridors_list_returns_200(self):
        resp = client.get("/api/compliance/corridors")
        assert resp.status_code == 200
        data = resp.json()
        assert "corridors" in data
        assert data["count"] >= 3

    def test_corridor_detail_returns_200(self):
        resp = client.get("/api/compliance/corridors/china_singapore_india")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == "china_singapore_india"

    def test_unknown_corridor_detail_returns_404(self):
        resp = client.get("/api/compliance/corridors/nonexistent_corridor")
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# 8. FOUR NOVEL CORRIDOR TESTS
# Each corridor is genuinely NOT in corridors.yaml.
# Tests verify: (a) structurally sane output, (b) banner fires, (c) no crash
# ══════════════════════════════════════════════════════════════════════════════


class TestNovelCorridors:
    """
    Four corridors that are deliberately NOT in PRE_VALIDATED_CORRIDORS.
    All should:
      (a) return is_rule_validated=False with structurally complete output
      (b) always fire the ui_banner with type=WARNING and correct label
      (c) never crash / return an unhandled error
      (d) demonstrate the 'general principles' language shape in mock output

    Mock verification also checks the output does NOT use specific-statute language
    (we verify the mock follows the anti-hallucination schema fields properly).
    """

    # ─── NOVEL CORRIDOR 1: Brazil → Cayman Islands → Turkey ─────────────────────
    # South American PE → MENA/EU border country — no pre-validated policy

    _BRAZIL_CAYMAN_TURKEY = {
        "origin_jurisdiction": "BRAZIL",
        "target_jurisdiction": "TURKEY",
        "spv_jurisdiction": "CAYMAN_ISLANDS",
        "sector": "Infrastructure",
        "investment_amount_usd": 75_000_000,
        "equity_pct": 30.0,
    }

    def test_brazil_cayman_turkey_is_not_in_registry(self):
        """Verify this corridor is genuinely absent from corridors.yaml."""
        c = match_corridor("BRAZIL", "TURKEY", "CAYMAN_ISLANDS")
        assert c is None, "Brazil→Turkey should NOT be in corridors.yaml"

    def test_brazil_cayman_turkey_corridor_matched_false(self):
        data = post_evaluate_with_fallback_mock(self._BRAZIL_CAYMAN_TURKEY)
        assert data["corridor_matched"] is False

    def test_brazil_cayman_turkey_banner_fires(self):
        """(b) banner always fires correctly."""
        data = post_evaluate_with_fallback_mock(self._BRAZIL_CAYMAN_TURKEY)
        banner = data["fallback_result"]["ui_banner"]
        assert banner["type"] == "WARNING"
        assert banner["label"] == "Illustrative \u2014 Not Yet Rule-Validated"
        assert "BRAZIL" in banner["message"] or "TURKEY" in banner["message"]

    def test_brazil_cayman_turkey_structurally_sane(self):
        """(a) output is structurally sane and complete."""
        data = post_evaluate_with_fallback_mock(self._BRAZIL_CAYMAN_TURKEY)
        fr = data["fallback_result"]
        assert fr["is_rule_validated"] is False
        assert fr["is_allowed"] is None
        assert len(fr["illustrative_risks"]) >= 1
        assert len(fr["illustrative_touchpoints"]) >= 1
        assert len(fr["general_analysis"]) >= 50
        assert len(fr["general_principles_applied"]) >= 1
        assert fr["uncertainty_summary"]

    def test_brazil_cayman_turkey_no_crash(self):
        """(c) endpoint returns 200 and does not crash."""
        resp_data = post_evaluate_with_fallback_mock(self._BRAZIL_CAYMAN_TURKEY)
        assert resp_data["fallback_result"] is not None

    def test_brazil_cayman_turkey_mock_uses_general_principles_language(self):
        """
        (a-extended) The mock output (which models correct LLM behavior) uses
        'typically', 'commonly', or 'most jurisdictions' language in risk items —
        NOT specific statute citations.
        """
        mock_output = _make_fallback_llm_output(
            origin="BRAZIL", target="TURKEY", spv="CAYMAN_ISLANDS"
        )
        for risk in mock_output.illustrative_risks:
            text = (
                risk.typical_pattern + " " + risk.description
            ).lower()
            # General-principles language present
            assert any(kw in text for kw in ["typically", "commonly", "most", "general", "standard"]), (
                f"Risk item lacks general-principles language: {risk.description[:80]}"
            )
            # No specific statute section citations (pattern: 'Section N' or 'Article N' or 'IRC §')
            import re
            bad_patterns = [r"section \d+", r"article \d+", r"irc §\d+", r"\u00a7 ?\d+"]
            for pat in bad_patterns:
                assert not re.search(pat, text, re.IGNORECASE), (
                    f"Risk item contains specific statute citation matching '{pat}': {text[:100]}"
                )

    def test_brazil_cayman_turkey_uncertainty_flags_present(self):
        """Every risk and touchpoint has a non-empty uncertainty_flag."""
        data = post_evaluate_with_fallback_mock(self._BRAZIL_CAYMAN_TURKEY)
        fr = data["fallback_result"]
        for risk in fr["illustrative_risks"]:
            assert risk["uncertainty_flag"] and len(risk["uncertainty_flag"]) > 10, (
                f"Empty uncertainty_flag on risk: {risk['code'] if 'code' in risk else risk['description'][:40]}"
            )
        for tp in fr["illustrative_touchpoints"]:
            assert tp["uncertainty_flag"] and len(tp["uncertainty_flag"]) > 10

    # ─── NOVEL CORRIDOR 2: Kazakhstan → Cyprus → Germany ────────────────────────
    # Central Asian → EU via Cyprus — no pre-validated policy

    _KAZAKHSTAN_CYPRUS_GERMANY = {
        "origin_jurisdiction": "KAZAKHSTAN",
        "target_jurisdiction": "GERMANY",
        "spv_jurisdiction": "CYPRUS",
        "sector": "Manufacturing",
        "investment_amount_usd": 120_000_000,
        "equity_pct": 51.0,
        "target_sector_is_sensitive": False,
    }

    def test_kazakhstan_cyprus_germany_is_not_in_registry(self):
        """Verify this corridor is genuinely absent from corridors.yaml."""
        c = match_corridor("KAZAKHSTAN", "GERMANY", "CYPRUS")
        assert c is None, "Kazakhstan→Germany should NOT be in corridors.yaml"

    def test_kazakhstan_cyprus_germany_corridor_matched_false(self):
        data = post_evaluate_with_fallback_mock(self._KAZAKHSTAN_CYPRUS_GERMANY)
        assert data["corridor_matched"] is False

    def test_kazakhstan_cyprus_germany_banner_fires(self):
        """(b) banner always fires for this corridor."""
        data = post_evaluate_with_fallback_mock(self._KAZAKHSTAN_CYPRUS_GERMANY)
        banner = data["fallback_result"]["ui_banner"]
        assert banner["type"] == "WARNING"
        assert "Illustrative" in banner["label"]

    def test_kazakhstan_cyprus_germany_structurally_sane(self):
        """(a) output complete and correct."""
        data = post_evaluate_with_fallback_mock(self._KAZAKHSTAN_CYPRUS_GERMANY)
        fr = data["fallback_result"]
        assert fr["is_rule_validated"] is False
        assert fr["is_allowed"] is None
        assert len(fr["illustrative_risks"]) >= 1
        assert len(fr["illustrative_touchpoints"]) >= 1

    def test_kazakhstan_cyprus_germany_no_crash(self):
        """(c) endpoint returns 200 and does not crash."""
        data = post_evaluate_with_fallback_mock(self._KAZAKHSTAN_CYPRUS_GERMANY)
        assert data is not None and data["fallback_result"] is not None

    # ─── NOVEL CORRIDOR 3: Nigeria → Mauritius → India ──────────────────────────
    # Sub-Saharan African origin into India via Mauritius — NOT in corridors.yaml
    # (Mauritius is used for India by others but Nigeria as origin is novel)

    _NIGERIA_MAURITIUS_INDIA = {
        "origin_jurisdiction": "NIGERIA",
        "target_jurisdiction": "INDIA",
        "spv_jurisdiction": "MAURITIUS",
        "sector": "Financial Services",
        "investment_amount_usd": 15_000_000,
        "equity_pct": 26.0,
        "prior_govt_approval_obtained": False,
    }

    def test_nigeria_mauritius_india_is_not_in_registry(self):
        """
        Verify this corridor is absent from corridors.yaml.
        Nigeria is not a land-border country with India (the India corridor
        only matches China/other land-border origin) and Mauritius SPV
        is not in any corridor's spv_jurisdictions list.
        """
        c = match_corridor("NIGERIA", "INDIA", "MAURITIUS")
        assert c is None, "Nigeria→Mauritius→India should NOT match any pre-validated corridor"

    def test_nigeria_mauritius_india_corridor_matched_false(self):
        data = post_evaluate_with_fallback_mock(self._NIGERIA_MAURITIUS_INDIA)
        assert data["corridor_matched"] is False

    def test_nigeria_mauritius_india_banner_fires(self):
        """(b) Banner fires — this is NOT a rule-validated corridor."""
        data = post_evaluate_with_fallback_mock(self._NIGERIA_MAURITIUS_INDIA)
        banner = data["fallback_result"]["ui_banner"]
        assert banner["type"] == "WARNING"
        assert banner["label"] == "Illustrative \u2014 Not Yet Rule-Validated"

    def test_nigeria_mauritius_india_structurally_sane(self):
        """(a) output complete even for Africa→Asia corridor."""
        data = post_evaluate_with_fallback_mock(self._NIGERIA_MAURITIUS_INDIA)
        fr = data["fallback_result"]
        assert fr["is_rule_validated"] is False
        assert len(fr["illustrative_risks"]) >= 1
        assert len(fr["illustrative_touchpoints"]) >= 1
        assert fr["uncertainty_summary"]

    def test_nigeria_mauritius_india_no_crash(self):
        """(c) Does not crash even for unusual Africa→Asia pairing."""
        data = post_evaluate_with_fallback_mock(self._NIGERIA_MAURITIUS_INDIA)
        assert data["fallback_result"] is not None

    # ─── NOVEL CORRIDOR 4: Mongolia → Singapore → Vietnam ───────────────────────
    # Deliberately obscure/unusual: Inner Asian → Southeast Asian via Singapore
    # Singapore IS used as SPV in China→India corridor but not for Mongolia→Vietnam

    _MONGOLIA_SINGAPORE_VIETNAM = {
        "origin_jurisdiction": "MONGOLIA",
        "target_jurisdiction": "VIETNAM",
        "spv_jurisdiction": "SINGAPORE",
        "sector": "Mining",
        "investment_amount_usd": 8_000_000,
        "equity_pct": 45.0,
    }

    def test_mongolia_singapore_vietnam_is_not_in_registry(self):
        """
        The most deliberately unusual pairing.
        Mongolia is NOT China; Vietnam is NOT India.
        Even though Singapore appears in the China→India corridor as SPV,
        it does not match here because origin and target don't match.
        """
        c = match_corridor("MONGOLIA", "VIETNAM", "SINGAPORE")
        assert c is None, "Mongolia→Singapore→Vietnam should NOT match any pre-validated corridor"

    def test_mongolia_singapore_vietnam_corridor_matched_false(self):
        data = post_evaluate_with_fallback_mock(self._MONGOLIA_SINGAPORE_VIETNAM)
        assert data["corridor_matched"] is False

    def test_mongolia_singapore_vietnam_banner_fires(self):
        """(b) Banner always fires — even for the most obscure pairings."""
        data = post_evaluate_with_fallback_mock(self._MONGOLIA_SINGAPORE_VIETNAM)
        banner = data["fallback_result"]["ui_banner"]
        assert banner["type"] == "WARNING"
        assert "Illustrative" in banner["label"]
        assert len(banner["message"]) > 30

    def test_mongolia_singapore_vietnam_structurally_sane(self):
        """(a) Even for ultra-obscure corridor, output is structurally complete."""
        data = post_evaluate_with_fallback_mock(self._MONGOLIA_SINGAPORE_VIETNAM)
        fr = data["fallback_result"]
        assert fr["is_rule_validated"] is False
        assert fr["is_allowed"] is None
        assert len(fr["illustrative_risks"]) >= 1
        assert len(fr["illustrative_touchpoints"]) >= 1
        assert len(fr["general_analysis"]) >= 50

    def test_mongolia_singapore_vietnam_no_crash(self):
        """(c) Does not crash or return a raw error for ultra-obscure pairing."""
        data = post_evaluate_with_fallback_mock(self._MONGOLIA_SINGAPORE_VIETNAM)
        assert data is not None
        assert data["fallback_result"] is not None

    def test_mongolia_singapore_vietnam_uncertainty_flags_non_empty(self):
        """For the most obscure corridor, uncertainty flags must explicitly acknowledge the unknown."""
        mock_output = _make_fallback_llm_output(
            origin="MONGOLIA", target="VIETNAM", spv="SINGAPORE"
        )
        for risk in mock_output.illustrative_risks:
            assert len(risk.uncertainty_flag) > 10
            # Uncertainty flags must not be generic empty placeholders
            assert risk.uncertainty_flag.lower() != "unknown"
        for tp in mock_output.illustrative_touchpoints:
            assert len(tp.uncertainty_flag) > 10


# ══════════════════════════════════════════════════════════════════════════════
# 9. SYSTEM PROMPT ANTI-HALLUCINATION CONTENT TESTS
# Verify the fallback prompt itself contains the anti-hallucination instructions
# ══════════════════════════════════════════════════════════════════════════════


class TestFallbackPromptAntiHallucination:
    """
    Tests that verify the fallback system prompt contains required anti-hallucination
    guardrails. These tests ensure the LLM instruction layer is correct even if
    individual LLM calls are not tested in CI.
    """

    def test_system_prompt_prohibits_specific_statutes(self):
        """System prompt must contain explicit prohibition on specific statute citations."""
        from app.services.fallback_prompts import FALLBACK_SYSTEM_PROMPT
        prompt_lower = FALLBACK_SYSTEM_PROMPT.lower()
        assert "do not cite" in prompt_lower or "do not" in prompt_lower
        # Must specifically mention statute/section/article prohibition
        assert any(kw in prompt_lower for kw in ["statute", "section", "article number", "form number"])

    def test_system_prompt_contains_uncertainty_flag_requirement(self):
        """System prompt must require uncertainty_flag in every item."""
        from app.services.fallback_prompts import FALLBACK_SYSTEM_PROMPT
        assert "uncertainty_flag" in FALLBACK_SYSTEM_PROMPT

    def test_system_prompt_contains_typically_language_instruction(self):
        """System prompt must instruct 'typically'/'commonly' language."""
        from app.services.fallback_prompts import FALLBACK_SYSTEM_PROMPT
        assert "typically" in FALLBACK_SYSTEM_PROMPT
        assert "commonly" in FALLBACK_SYSTEM_PROMPT

    def test_system_prompt_has_two_few_shot_exemplars(self):
        """System prompt must contain at least two few-shot examples."""
        from app.services.fallback_prompts import FALLBACK_SYSTEM_PROMPT
        # Count sections containing 'EXEMPLAR' or 'Example'
        count = FALLBACK_SYSTEM_PROMPT.upper().count("EXEMPLAR")
        assert count >= 2, f"Expected at least 2 few-shot exemplars, found {count}"

    def test_system_prompt_requires_local_counsel_disclaimer(self):
        """System prompt must require output to recommend local qualified counsel."""
        from app.services.fallback_prompts import FALLBACK_SYSTEM_PROMPT
        prompt_lower = FALLBACK_SYSTEM_PROMPT.lower()
        assert "local" in prompt_lower and "counsel" in prompt_lower

    def test_system_prompt_has_absolute_rules_section(self):
        """System prompt must have clearly labeled absolute rules section."""
        from app.services.fallback_prompts import FALLBACK_SYSTEM_PROMPT
        assert "ABSOLUTE" in FALLBACK_SYSTEM_PROMPT.upper()

    def test_fallback_llm_output_schema_has_no_citations_field(self):
        """
        FallbackLLMOutput schema must NOT have a 'citations' or 'cited_sources' field,
        which would encourage hallucinated citation behavior.
        """
        fields = set(FallbackLLMOutput.model_fields.keys())
        assert "citations" not in fields
        assert "cited_sources" not in fields
        assert "references" not in fields
        assert "statutory_references" not in fields

    def test_fallback_llm_output_has_uncertainty_summary_field(self):
        """FallbackLLMOutput schema must have uncertainty_summary."""
        assert "uncertainty_summary" in FallbackLLMOutput.model_fields

    def test_fallback_risk_item_schema_has_uncertainty_flag(self):
        """IllustrativeRiskItem must have uncertainty_flag."""
        assert "uncertainty_flag" in IllustrativeRiskItem.model_fields

    def test_fallback_touchpoint_schema_has_uncertainty_flag(self):
        """IllustrativeTouchpointItem must have uncertainty_flag."""
        assert "uncertainty_flag" in IllustrativeTouchpointItem.model_fields

    def test_build_banner_message_includes_corridor_info(self):
        """build_banner_message must include origin and target jurisdiction in the message."""
        from app.services.fallback_prompts import build_banner_message
        from app.schemas.compliance import ComplianceInput
        ci = ComplianceInput(
            origin_jurisdiction="MONGOLIA",
            target_jurisdiction="VIETNAM",
            spv_jurisdiction="SINGAPORE",
            sector="Mining",
            investment_amount_usd=5_000_000,
        )
        msg = build_banner_message(ci, "Test uncertainty summary.")
        assert "MONGOLIA" in msg
        assert "VIETNAM" in msg
        assert len(msg) > 50

    def test_build_banner_message_includes_uncertainty_summary(self):
        """Banner message must include the uncertainty_summary content."""
        from app.services.fallback_prompts import build_banner_message
        from app.schemas.compliance import ComplianceInput
        ci = ComplianceInput(
            origin_jurisdiction="BRAZIL",
            target_jurisdiction="TURKEY",
            sector="Infrastructure",
            investment_amount_usd=1_000_000,
        )
        unique_phrase = "unique-uncertainty-phrase-xyz"
        msg = build_banner_message(ci, unique_phrase)
        assert unique_phrase in msg


# ══════════════════════════════════════════════════════════════════════════════
# 8. POLICY EVALUATOR REGISTRY
# ══════════════════════════════════════════════════════════════════════════════

class TestPolicyEvaluatorRegistry:

    def test_get_evaluator_india(self):
        ev = get_evaluator("sententia.corridors.india")
        assert isinstance(ev, IndiaCorridor)

    def test_get_evaluator_us_cayman(self):
        ev = get_evaluator("sententia.corridors.us_cayman_india")
        assert isinstance(ev, USCaymanIndia)

    def test_get_evaluator_gulf_eu(self):
        ev = get_evaluator("sententia.corridors.gulf_eu")
        assert isinstance(ev, GulfEU)

    def test_get_evaluator_unknown_returns_none(self):
        ev = get_evaluator("sententia.corridors.nonexistent")
        assert ev is None

    def test_list_registered_packages(self):
        packages = list_registered_packages()
        assert "sententia.corridors.india" in packages
        assert "sententia.corridors.us_cayman_india" in packages
        assert "sententia.corridors.gulf_eu" in packages
        assert len(packages) == 3
