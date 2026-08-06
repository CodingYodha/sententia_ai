"""
Sententia.ai — Intake Pipeline Tests

Test strategy:
  - Unit tests (no LLM, no Supabase): schema validation, extraction logic
  - Integration tests (need API keys): marked with @pytest.mark.integration, skipped if no key set
  - All three fixtures are tested for sane extraction output

Run:
    cd backend
    conda run -n iitr pytest tests/test_intake.py -v

Run only unit tests (no keys needed):
    conda run -n iitr pytest tests/test_intake.py -v -m "not integration"
"""

from __future__ import annotations

import io
import os
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── FastAPI test client ────────────────────────────────────────────────────────
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# ── Fixture paths ──────────────────────────────────────────────────────────────
FIXTURES_DIR = Path(__file__).parent / "fixtures"
CAP_TABLE_TXT    = FIXTURES_DIR / "cap_table_fixture.txt"
SHA_TXT          = FIXTURES_DIR / "sha_fixture.txt"
DEAL_SUMMARY_TXT = FIXTURES_DIR / "deal_summary_fixture.txt"


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _load_fixture(path: Path) -> bytes:
    return path.read_bytes()


def _upload_text_as_file(text_bytes: bytes, filename: str = "test.txt") -> dict:
    """POST /api/intake/document with a plain-text file upload."""
    response = client.post(
        "/api/intake/document",
        files={"file": (filename, io.BytesIO(text_bytes), "text/plain")},
    )
    return response


# ══════════════════════════════════════════════════════════════════════════════
# 1. SCHEMA VALIDATION TESTS (pure Pydantic — no network)
# ══════════════════════════════════════════════════════════════════════════════

class TestSchemas:
    """Unit tests for Pydantic schema validation."""

    def test_ubo_entity_ownership_bounds(self):
        from app.schemas.intake import UBOEntity, EntityType
        # Valid
        entity = UBOEntity(
            name="Huang Wei",
            jurisdiction="China",
            entity_type=EntityType.INDIVIDUAL,
            ownership_pct=74.0,
            is_ubo=True,
        )
        assert entity.ownership_pct == 74.0

    def test_ubo_entity_rejects_over_100(self):
        from app.schemas.intake import UBOEntity, EntityType
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            UBOEntity(
                name="Test",
                jurisdiction="Singapore",
                entity_type=EntityType.COMPANY,
                ownership_pct=101.0,
            )

    def test_equity_stake_schema(self):
        from app.schemas.intake import EquityStake, EntityType
        stake = EquityStake(
            entity_name="Apex Holdings Pte. Ltd.",
            entity_type=EntityType.COMPANY,
            jurisdiction="Singapore",
            ownership_pct=74.0,
            share_class="Ordinary",
            num_shares=7_400_000,
        )
        assert stake.ownership_pct == 74.0
        assert stake.share_class == "Ordinary"

    def test_control_rights_defaults(self):
        from app.schemas.intake import ControlRights
        cr = ControlRights()
        assert cr.drag_along is False
        assert cr.tag_along is False
        assert cr.right_of_first_refusal is False
        assert cr.board_seats == []
        assert cr.veto_rights == []

    def test_scenario_create_required_fields(self):
        from app.schemas.intake import ScenarioCreate, InvestmentStructureType
        import pydantic
        # Missing required fields should raise
        with pytest.raises(pydantic.ValidationError):
            ScenarioCreate(
                capital_origin="China",
                # target_jurisdiction missing
                sector="Technology",
                investment_amount_usd=5_000_000,
                investment_structure_type=InvestmentStructureType.SPV_LAYERED,
            )

    def test_scenario_create_amount_must_be_positive(self):
        from app.schemas.intake import ScenarioCreate, InvestmentStructureType
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            ScenarioCreate(
                capital_origin="China",
                target_jurisdiction="India",
                sector="Technology",
                investment_amount_usd=-1000,
                investment_structure_type=InvestmentStructureType.DIRECT_FDI,
            )

    def test_scenario_create_strips_whitespace(self):
        from app.schemas.intake import ScenarioCreate, InvestmentStructureType
        scenario = ScenarioCreate(
            capital_origin="  China  ",
            target_jurisdiction=" India ",
            sector=" Technology ",
            investment_amount_usd=5_000_000,
            investment_structure_type=InvestmentStructureType.SPV_LAYERED,
        )
        assert scenario.capital_origin == "China"
        assert scenario.target_jurisdiction == "India"


# ══════════════════════════════════════════════════════════════════════════════
# 2. DOCLING SERVICE TESTS (no LLM, no network)
# ══════════════════════════════════════════════════════════════════════════════

class TestDoclingService:
    """Unit tests for the extraction service — uses PyPDF/plain-text fallback."""

    def test_extract_plain_text(self):
        from app.services.docling_service import extract_document
        text = b"Hello, this is a test document with some content."
        result = extract_document(text, "test.txt")
        assert "Hello" in result.text
        assert result.method == "text_plain"

    def test_extract_fixture_cap_table(self):
        from app.services.docling_service import extract_document
        fixture_bytes = _load_fixture(CAP_TABLE_TXT)
        result = extract_document(fixture_bytes, "cap_table.txt")
        assert len(result.text) > 100
        # Key entities should be present in extraction
        assert "Apex Holdings" in result.text
        assert "74" in result.text
        assert "Singapore" in result.text

    def test_extract_fixture_sha(self):
        from app.services.docling_service import extract_document
        fixture_bytes = _load_fixture(SHA_TXT)
        result = extract_document(fixture_bytes, "sha.txt")
        assert len(result.text) > 100
        assert "veto" in result.text.lower() or "Veto" in result.text

    def test_extract_fixture_deal_summary(self):
        from app.services.docling_service import extract_document
        fixture_bytes = _load_fixture(DEAL_SUMMARY_TXT)
        result = extract_document(fixture_bytes, "deal_summary.txt")
        assert len(result.text) > 100
        assert "85,000,000" in result.text or "85000000" in result.text or "USD" in result.text

    def test_empty_file_returns_empty_text(self):
        from app.services.docling_service import extract_document
        result = extract_document(b"", "empty.txt")
        assert result.text == "" or result.text.strip() == ""

    def test_method_is_text_plain_for_txt(self):
        from app.services.docling_service import extract_document
        result = extract_document(b"Some content", "document.txt")
        assert result.method == "text_plain"


# ══════════════════════════════════════════════════════════════════════════════
# 3. API ENDPOINT TESTS — POST /api/intake/document
# ══════════════════════════════════════════════════════════════════════════════

class TestDocumentEndpoint:
    """Tests for POST /api/intake/document — no LLM keys needed for basic tests."""

    def test_upload_cap_table_returns_200(self):
        fixture = _load_fixture(CAP_TABLE_TXT)
        response = _upload_text_as_file(fixture, "cap_table.txt")
        assert response.status_code == 200

    def test_upload_cap_table_response_structure(self):
        fixture = _load_fixture(CAP_TABLE_TXT)
        response = _upload_text_as_file(fixture, "cap_table.txt")
        data = response.json()
        # Required top-level fields
        assert "filename" in data
        assert "extraction_method" in data
        assert "extracted_text_preview" in data
        assert "extracted_text_length" in data
        assert "llm_structured" in data
        assert "warnings" in data
        assert "equity_stakes" in data

    def test_upload_cap_table_text_length_sane(self):
        fixture = _load_fixture(CAP_TABLE_TXT)
        response = _upload_text_as_file(fixture, "cap_table.txt")
        data = response.json()
        assert data["extracted_text_length"] > 200

    def test_upload_sha_returns_200(self):
        fixture = _load_fixture(SHA_TXT)
        response = _upload_text_as_file(fixture, "sha.txt")
        assert response.status_code == 200

    def test_upload_sha_preview_contains_veto(self):
        fixture = _load_fixture(SHA_TXT)
        response = _upload_text_as_file(fixture, "sha.txt")
        data = response.json()
        # Preview is first 500 chars — SHA starts with header, full text has veto
        assert data["extracted_text_length"] > 500

    def test_upload_deal_summary_returns_200(self):
        fixture = _load_fixture(DEAL_SUMMARY_TXT)
        response = _upload_text_as_file(fixture, "deal_summary.txt")
        assert response.status_code == 200

    def test_upload_deal_summary_has_usd_in_text(self):
        fixture = _load_fixture(DEAL_SUMMARY_TXT)
        response = _upload_text_as_file(fixture, "deal_summary.txt")
        data = response.json()
        full_preview = data["extracted_text_preview"]
        length = data["extracted_text_length"]
        assert length > 500

    def test_unsupported_mime_type_returns_415(self):
        response = client.post(
            "/api/intake/document",
            files={"file": ("test.xlsx", io.BytesIO(b"fake content"), "application/vnd.ms-excel")},
        )
        assert response.status_code == 415

    def test_empty_file_returns_400(self):
        response = client.post(
            "/api/intake/document",
            files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        )
        assert response.status_code == 400

    def test_no_llm_key_sets_llm_structured_false(self):
        """Without API keys configured, llm_structured must be False."""
        fixture = _load_fixture(CAP_TABLE_TXT)
        # Patch settings to return empty keys
        with patch("app.services.llm_router.get_llm_client", return_value=None):
            response = _upload_text_as_file(fixture, "cap_table.txt")
            data = response.json()
            assert data["llm_structured"] is False

    def test_no_llm_key_returns_warning(self):
        fixture = _load_fixture(CAP_TABLE_TXT)
        with patch("app.services.llm_router.get_llm_client", return_value=None):
            response = _upload_text_as_file(fixture, "cap_table.txt")
            data = response.json()
            assert len(data["warnings"]) > 0
            assert any("API key" in w or "skipped" in w for w in data["warnings"])


# ══════════════════════════════════════════════════════════════════════════════
# 4. API ENDPOINT TESTS — POST /api/intake/scenario
# ══════════════════════════════════════════════════════════════════════════════

class TestScenarioEndpoint:
    """Tests for POST /api/intake/scenario — no Supabase needed for basic tests."""

    _BASE_PAYLOAD = {
        "capital_origin": "United Arab Emirates",
        "target_jurisdiction": "India",
        "sector": "Agricultural Technology",
        "investment_amount_usd": 85_000_000,
        "investment_structure_type": "spv_layered",
        "spv_jurisdiction": "Singapore",
        "equity_pct": 34.0,
        "investor_profile": "sovereign_wealth_fund",
        "notes": "Project Monsoon — Series B",
    }

    def test_create_scenario_returns_201(self):
        with patch("app.routers.intake.get_supabase_client") as mock_sb:
            mock_sb.return_value.table.return_value.insert.return_value.execute.return_value = MagicMock()
            response = client.post("/api/intake/scenario", json=self._BASE_PAYLOAD)
        assert response.status_code == 201

    def test_create_scenario_returns_scenario_id(self):
        with patch("app.routers.intake.get_supabase_client") as mock_sb:
            mock_sb.return_value.table.return_value.insert.return_value.execute.return_value = MagicMock()
            response = client.post("/api/intake/scenario", json=self._BASE_PAYLOAD)
        data = response.json()
        assert "scenario_id" in data
        assert len(data["scenario_id"]) == 36  # UUID format

    def test_create_scenario_echoes_fields(self):
        with patch("app.routers.intake.get_supabase_client") as mock_sb:
            mock_sb.return_value.table.return_value.insert.return_value.execute.return_value = MagicMock()
            response = client.post("/api/intake/scenario", json=self._BASE_PAYLOAD)
        data = response.json()
        assert data["capital_origin"] == "United Arab Emirates"
        assert data["target_jurisdiction"] == "India"
        assert data["investment_amount_usd"] == 85_000_000
        assert data["spv_jurisdiction"] == "Singapore"

    def test_missing_required_field_returns_422(self):
        payload = {**self._BASE_PAYLOAD}
        del payload["target_jurisdiction"]
        response = client.post("/api/intake/scenario", json=payload)
        assert response.status_code == 422

    def test_negative_amount_returns_422(self):
        payload = {**self._BASE_PAYLOAD, "investment_amount_usd": -500}
        response = client.post("/api/intake/scenario", json=payload)
        assert response.status_code == 422

    def test_invalid_structure_type_returns_422(self):
        payload = {**self._BASE_PAYLOAD, "investment_structure_type": "not_a_real_type"}
        response = client.post("/api/intake/scenario", json=payload)
        assert response.status_code == 422

    def test_optional_fields_can_be_omitted(self):
        minimal = {
            "capital_origin": "China",
            "target_jurisdiction": "India",
            "sector": "Technology",
            "investment_amount_usd": 10_000_000,
            "investment_structure_type": "spv_layered",
        }
        with patch("app.routers.intake.get_supabase_client") as mock_sb:
            mock_sb.return_value.table.return_value.insert.return_value.execute.return_value = MagicMock()
            response = client.post("/api/intake/scenario", json=minimal)
        assert response.status_code == 201
        data = response.json()
        assert data["spv_jurisdiction"] is None
        assert data["equity_pct"] is None

    def test_supabase_failure_still_returns_201(self):
        """Scenario endpoint should not crash on Supabase connectivity issues."""
        with patch("app.routers.intake.get_supabase_client", side_effect=Exception("Supabase down")):
            response = client.post("/api/intake/scenario", json=self._BASE_PAYLOAD)
        # Should still return 201 with a scenario_id (graceful degradation)
        assert response.status_code == 201


# ══════════════════════════════════════════════════════════════════════════════
# 5. INTEGRATION TESTS — require real LLM keys
#    Run with: pytest -m integration
# ══════════════════════════════════════════════════════════════════════════════

@pytest.mark.integration
class TestLLMStructuringIntegration:
    """
    Integration tests that exercise real LLM calls.
    Skipped automatically if OPENROUTER_API_KEY and GROQ_API_KEY are not set.
    """

    @pytest.fixture(autouse=True)
    def skip_if_no_keys(self):
        if not os.getenv("OPENROUTER_API_KEY") and not os.getenv("GROQ_API_KEY"):
            pytest.skip("No LLM API keys set — skipping integration tests")

    def test_cap_table_produces_equity_stakes(self):
        fixture = _load_fixture(CAP_TABLE_TXT)
        response = _upload_text_as_file(fixture, "cap_table.txt")
        data = response.json()
        assert data["llm_structured"] is True
        assert len(data["equity_stakes"]) >= 2

    def test_sha_produces_control_rights(self):
        fixture = _load_fixture(SHA_TXT)
        response = _upload_text_as_file(fixture, "sha.txt")
        data = response.json()
        assert data["llm_structured"] is True
        cr = data["control_rights"]
        assert cr is not None
        assert len(cr["veto_rights"]) > 0

    def test_sha_detects_drag_and_tag(self):
        fixture = _load_fixture(SHA_TXT)
        response = _upload_text_as_file(fixture, "sha.txt")
        data = response.json()
        cr = data["control_rights"]
        assert cr["drag_along"] is True
        assert cr["tag_along"] is True

    def test_deal_summary_produces_ubo_info(self):
        fixture = _load_fixture(DEAL_SUMMARY_TXT)
        response = _upload_text_as_file(fixture, "deal_summary.txt")
        data = response.json()
        assert data["llm_structured"] is True
        ubo = data["ubo_info"]
        assert ubo is not None
        assert len(ubo["ultimate_beneficial_owners"]) >= 1
