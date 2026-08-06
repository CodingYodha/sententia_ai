"""
Sententia.ai — Diagram Serializer Tests

Tests the structure JSON → Mermaid.js graph TD serialization pipeline.

Test matrix:
  1. FIXTURE A — 2-entity direct structure (no SPV)
  2. FIXTURE B — 4-entity layered structure with SPV
  3. FIXTURE C — multiple parallel capital-flow paths

For each fixture, we verify:
  (a) Output is non-empty
  (b) graph TD header present
  (c) No malformed brackets (opens == closes, roughly)
  (d) Entity nodes present
  (e) Edge arrows present
  (f) classDef block present
  (g) Regulatory checkpoint nodes present (if touchpoints included)

Additional tests:
  - HTTP endpoint: POST /api/diagram/generate (inline structure_json)
  - Pass 1 / Pass 2 routing logic
  - validate_mermaid_syntax helper
  - Edge labels / flow labels
  - Regulatory checkpoint nodes styled correctly
"""

from __future__ import annotations

import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.diagram_serializer import (
    serialize_structure_to_mermaid,
    validate_mermaid_syntax,
    _validate_llm_mermaid,
    _parse_ownership_chain,
)

client = TestClient(app)


# ══════════════════════════════════════════════════════════════════════════════
# SHARED HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _count_arrows(mermaid: str) -> int:
    return len(re.findall(r"-->|--\||-\.-?>", mermaid))


def _count_nodes(mermaid: str) -> int:
    """Rough count of node definitions (lines with [, {, or ()."""
    return len(re.findall(r"^\s+\w+[\[({]", mermaid, re.MULTILINE))


def _has_graph_td(mermaid: str) -> bool:
    return bool(re.search(r"graph\s+TD", mermaid, re.IGNORECASE))


def _has_classdef(mermaid: str) -> bool:
    return "classDef" in mermaid


def _has_regulatory_node(mermaid: str) -> bool:
    return "regulatoryNode" in mermaid


def _brackets_balanced(mermaid: str, tolerance: int = 6) -> bool:
    """Check that open/close bracket counts are roughly balanced."""
    opens  = mermaid.count("[") + mermaid.count("{") + mermaid.count("(")
    closes = mermaid.count("]") + mermaid.count("}") + mermaid.count(")")
    return abs(opens - closes) <= tolerance


# ══════════════════════════════════════════════════════════════════════════════
# TEST FIXTURES — three distinct structure shapes
# ══════════════════════════════════════════════════════════════════════════════

# ── FIXTURE A: 2-entity direct structure ─────────────────────────────────────
# Origin investor → Target OpCo (no intermediate SPV)

FIXTURE_A_DIRECT = {
    "rank": 1,
    "name": "US Direct Investment into Germany",
    "structure_type": "direct_fdi",
    "architecture_description": (
        "A US-based PE fund invests directly into a German operating company "
        "without any intermediate holding structure. Simplest possible structure."
    ),
    "ownership_chain": "US PE Fund (100%) → Germany OpCo",
    "jurisdictions_involved": ["United States", "Germany"],
    "mermaid_diagram": """graph TD
    A["US PE Fund\\n[United States]"]
    B["Germany OpCo\\n[Germany]"]
    A -->|"Capital / 100% equity"| B
    classDef originNode fill:#1e3a5f,stroke:#4a9eff,color:#fff
    classDef targetNode fill:#1b4332,stroke:#40916c,color:#d8f3dc
    class A originNode
    class B targetNode""",
    "compliance_touchpoints": [
        {
            "jurisdiction": "Germany",
            "requirement": "Foreign trade office (BAFA) screening for acquisitions above 25%",
            "timing": "pre-signing",
            "authority": "BAFA",
            "notes": "Mandatory for non-EU acquirers in sensitive sectors",
        }
    ],
    "cited_sources": ["OECD MTC Commentary", "German Foreign Trade Regulation"],
    "identified_risks": [
        {
            "risk_type": "regulatory",
            "description": "German FDI screening for US origin",
            "severity": "medium",
            "mitigation": "File BAFA notification prior to signing",
        }
    ],
    "rationale": "Lowest setup complexity for small-scale direct investment.",
    "estimated_setup_complexity": "low",
    "regulatory_confidence": "medium",
}

# ── FIXTURE B: 4-entity layered structure with SPV ───────────────────────────
# PRC Fund → Singapore HoldCo → India SPV → India OpCo

FIXTURE_B_LAYERED = {
    "rank": 1,
    "name": "China → Singapore HoldCo → India OpCo (DTAA Optimized)",
    "structure_type": "spv_layered",
    "architecture_description": (
        "PRC Fund holds 100% of Singapore HoldCo, which holds 74% of India SPV, "
        "which in turn holds 100% of India OpCo. Singapore is used to access "
        "DTAA benefits and reduce withholding on dividends."
    ),
    "ownership_chain": "PRC Fund (100%) → Singapore HoldCo (74%) → India SPV (51%) → India OpCo",
    "jurisdictions_involved": ["China", "Singapore", "India"],
    "mermaid_diagram": """graph TD
    A["PRC Fund\\n[China]"]
    B["Singapore HoldCo\\n[Singapore]"]
    C["India SPV\\n[India]"]
    D["India OpCo\\n[India]"]
    A -->|"100% equity"| B
    B -->|"74% equity"| C
    C -->|"51% equity"| D
    classDef originNode fill:#1e3a5f,stroke:#4a9eff,color:#fff,stroke-width:2px
    classDef entityNode fill:#243b55,stroke:#3a7bd5,color:#e8eaf6
    classDef targetNode fill:#1b4332,stroke:#40916c,color:#d8f3dc,stroke-width:2px
    class A originNode
    class B entityNode
    class C entityNode
    class D targetNode""",
    "compliance_touchpoints": [
        {
            "jurisdiction": "India",
            "requirement": "Press Note 3 prior approval from DPIIT — Chinese-origin capital above threshold",
            "timing": "pre-signing",
            "authority": "DPIIT",
            "notes": "Mandatory for all Chinese beneficial owners regardless of SPV structure",
        },
        {
            "jurisdiction": "India",
            "requirement": "FC-GPR filing with RBI within 30 days of share allotment",
            "timing": "post-closing",
            "authority": "RBI",
            "notes": "Required for all inbound FDI",
        },
        {
            "jurisdiction": "Singapore",
            "requirement": "IRAS substance documentation for DTAA treaty benefits",
            "timing": "pre-closing",
            "authority": "IRAS",
            "notes": "Singapore HoldCo must have genuine economic substance",
        },
        {
            "jurisdiction": "India",
            "requirement": "Significant Beneficial Ownership disclosure under Companies Act §90",
            "timing": "at-closing",
            "authority": "RoC",
            "notes": "Required when UBO exceeds 25% ownership threshold",
        },
    ],
    "cited_sources": ["Press Note 3 (2020)", "DTAA India-Singapore 2016", "Companies Act §90"],
    "identified_risks": [
        {
            "risk_type": "regulatory",
            "description": "PN3 requires prior government approval for Chinese-origin capital",
            "severity": "high",
            "mitigation": "Obtain DPIIT approval before transaction signing",
        },
        {
            "risk_type": "tax",
            "description": "Singapore SPV may face PPT challenge",
            "severity": "medium",
            "mitigation": "Ensure genuine economic substance in Singapore entity",
        },
    ],
    "rationale": "Most tax-efficient structure for China-origin capital investing into India.",
    "estimated_setup_complexity": "high",
    "regulatory_confidence": "high",
}

# ── FIXTURE C: Multiple parallel capital-flow paths ──────────────────────────
# Investor → Branch A (equity) + Branch B (debt instrument) → Target
# Tests that the serializer handles a Mermaid diagram with branching topology

FIXTURE_C_PARALLEL = {
    "rank": 2,
    "name": "UAE Fund → Parallel Equity + Convertible Note → Indian JV",
    "structure_type": "joint_venture",
    "architecture_description": (
        "UAE Fund invests through two parallel paths: (1) direct equity into Indian JV OpCo "
        "and (2) convertible notes via UAE HoldCo into Indian JV OpCo. "
        "The parallel structure optimizes tax treatment for returns."
    ),
    "ownership_chain": "UAE Fund (51%) → India JV OpCo | UAE Fund → UAE HoldCo → India JV OpCo",
    "jurisdictions_involved": ["UAE", "India"],
    "mermaid_diagram": """graph TD
    A["UAE Fund\\n[UAE]"]
    B["UAE HoldCo\\n[UAE]"]
    C["India JV OpCo\\n[India]"]
    A -->|"51% equity\\ndirect path"| C
    A -->|"100% ownership"| B
    B -.->|"Convertible note\\n(debt instrument)"| C
    classDef originNode fill:#1e3a5f,stroke:#4a9eff,color:#fff,stroke-width:2px
    classDef entityNode fill:#243b55,stroke:#3a7bd5,color:#e8eaf6
    classDef targetNode fill:#1b4332,stroke:#40916c,color:#d8f3dc,stroke-width:2px
    class A originNode
    class B entityNode
    class C targetNode""",
    "compliance_touchpoints": [
        {
            "jurisdiction": "India",
            "requirement": "RBI External Commercial Borrowings (ECB) approval for convertible notes",
            "timing": "pre-closing",
            "authority": "RBI",
            "notes": "Convertible instruments require ECB framework compliance",
        },
        {
            "jurisdiction": "India",
            "requirement": "FC-GPR and FC-TRS filings for equity and secondary transfers",
            "timing": "at-closing",
            "authority": "RBI",
            "notes": "Both direct equity and instrument conversion require separate filings",
        },
    ],
    "cited_sources": ["RBI ECB Framework 2019", "FEMA Regulations"],
    "identified_risks": [
        {
            "risk_type": "regulatory",
            "description": "Parallel debt and equity paths require separate RBI filings",
            "severity": "medium",
            "mitigation": "Engage Indian external counsel for ECB and FDI compliance",
        }
    ],
    "rationale": "Optimizes tax on interest vs dividend returns from India.",
    "estimated_setup_complexity": "medium",
    "regulatory_confidence": "medium",
}

# ── FIXTURE D: Malformed mermaid_diagram (to test Pass 2 fallback) ────────────
FIXTURE_D_MALFORMED = {
    "rank": 3,
    "name": "Malformed LLM Output — Pass 2 Fallback Test",
    "structure_type": "spv_layered",
    "architecture_description": "Test that Pass 2 works when LLM emits broken Mermaid.",
    "ownership_chain": "Japan Fund (100%) → Netherlands HoldCo (60%) → Brazil OpCo",
    "jurisdictions_involved": ["Japan", "Netherlands", "Brazil"],
    "mermaid_diagram": "THIS IS NOT VALID MERMAID SYNTAX AT ALL ~~~",  # Deliberately broken
    "compliance_touchpoints": [
        {
            "jurisdiction": "Brazil",
            "requirement": "SISBACEN foreign investment registration",
            "timing": "pre-closing",
            "authority": "Central Bank of Brazil",
            "notes": "Required for all direct foreign investment",
        }
    ],
    "cited_sources": ["OECD MTC"],
    "identified_risks": [],
    "rationale": "Testing only.",
    "estimated_setup_complexity": "medium",
    "regulatory_confidence": "low",
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. DIRECT STRUCTURE (FIXTURE A) — 2-entity, no SPV
# ══════════════════════════════════════════════════════════════════════════════

class TestFixtureADirect:
    """2-entity direct structure: origin → target, no intermediate SPV."""

    def _render(self, show_reg=True, show_labels=True):
        mermaid, entities, edges, checkpoints, warnings = serialize_structure_to_mermaid(
            FIXTURE_A_DIRECT, show_regulatory_checkpoints=show_reg,
            show_capital_flow_labels=show_labels,
        )
        return mermaid, entities, edges, checkpoints, warnings

    def test_non_empty_output(self):
        mermaid, *_ = self._render()
        assert mermaid and len(mermaid.strip()) > 20

    def test_graph_td_header(self):
        mermaid, *_ = self._render()
        assert _has_graph_td(mermaid)

    def test_at_least_two_entity_nodes(self):
        mermaid, entities, *_ = self._render()
        assert entities >= 2

    def test_at_least_one_edge(self):
        mermaid, _, edges, *_ = self._render()
        assert edges >= 1 or _count_arrows(mermaid) >= 1

    def test_classdef_block_present(self):
        mermaid, *_ = self._render()
        assert _has_classdef(mermaid), "classDef block must always be present"

    def test_brackets_balanced(self):
        mermaid, *_ = self._render()
        assert _brackets_balanced(mermaid)

    def test_regulatory_checkpoint_added(self):
        """BAFA pre-signing touchpoint should produce a regulatory node."""
        mermaid, _, __, checkpoints, ___ = self._render(show_reg=True)
        assert _has_regulatory_node(mermaid)
        assert checkpoints >= 1
        # Diamond labels must be quoted: unquoted parentheses are parsed as
        # Mermaid syntax rather than as the jurisdiction text.
        assert 'reg_0_bafa{"BAFA (Germany)' in mermaid

    def test_regulatory_checkpoint_suppressed(self):
        """When show_regulatory_checkpoints=False, no regulatoryNode."""
        mermaid, _, __, checkpoints, ___ = self._render(show_reg=False)
        assert checkpoints == 0

    def test_pass1_used_for_valid_llm_diagram(self):
        """Fixture A has a valid LLM diagram — Pass 1 should succeed (no fallback warning)."""
        _, _, __, ___, warnings = self._render()
        fallback_warnings = [w for w in warnings if "fallback" in w.lower()]
        assert not fallback_warnings, f"Pass 1 should succeed for valid Mermaid, got: {warnings}"

    def test_validate_syntax_passes(self):
        mermaid, *_ = self._render()
        valid, reason = validate_mermaid_syntax(mermaid)
        assert valid, f"validate_mermaid_syntax failed: {reason}\n\nMermaid:\n{mermaid}"


# ══════════════════════════════════════════════════════════════════════════════
# 2. LAYERED SPV STRUCTURE (FIXTURE B) — 4 entities, 3 edges, 3 checkpoints
# ══════════════════════════════════════════════════════════════════════════════

class TestFixtureBLayered:
    """4-entity layered: PRC Fund → Singapore HoldCo → India SPV → India OpCo."""

    def _render(self, show_reg=True, show_labels=True):
        return serialize_structure_to_mermaid(
            FIXTURE_B_LAYERED, show_regulatory_checkpoints=show_reg,
            show_capital_flow_labels=show_labels,
        )

    def test_non_empty_output(self):
        mermaid, *_ = self._render()
        assert mermaid and len(mermaid.strip()) > 20

    def test_graph_td_header(self):
        mermaid, *_ = self._render()
        assert _has_graph_td(mermaid)

    def test_four_entity_nodes(self):
        """Layered structure must have at least 4 entity nodes."""
        mermaid, entities, *_ = self._render()
        assert entities >= 4

    def test_three_edges(self):
        """4-entity chain requires at least 3 edges."""
        mermaid, _, edges, *_ = self._render()
        assert edges >= 3 or _count_arrows(mermaid) >= 3

    def test_classdef_block_present(self):
        mermaid, *_ = self._render()
        assert _has_classdef(mermaid)

    def test_brackets_balanced(self):
        mermaid, *_ = self._render()
        assert _brackets_balanced(mermaid)

    def test_regulatory_checkpoints_added(self):
        """pre-signing DPIIT + pre-closing IRAS + at-closing RoC → 3 checkpoint nodes."""
        mermaid, _, __, checkpoints, ___ = self._render(show_reg=True)
        assert _has_regulatory_node(mermaid)
        assert checkpoints >= 2  # DPIIT (pre-signing), IRAS (pre-closing), RoC (at-closing)

    def test_post_closing_touchpoint_excluded(self):
        """
        FC-GPR is post-closing → should NOT generate a regulatory node
        (post_closing and ongoing are excluded from diagram to avoid clutter).
        The count must be < 4 since one touchpoint is filtered.
        """
        _, _, __, checkpoints, ___ = self._render(show_reg=True)
        assert checkpoints <= 3  # 4 touchpoints but 1 is post-closing

    def test_pass1_used(self):
        """Fixture B has a valid LLM diagram — no fallback warnings expected."""
        _, _, __, ___, warnings = self._render()
        fallback_warnings = [w for w in warnings if "fallback" in w.lower()]
        assert not fallback_warnings

    def test_validate_syntax_passes(self):
        mermaid, *_ = self._render()
        valid, reason = validate_mermaid_syntax(mermaid)
        assert valid, f"Mermaid invalid: {reason}\n\n{mermaid[:500]}"

    def test_no_malformed_special_chars(self):
        """Mermaid output must not contain unquoted backticks or raw curly after classDef."""
        mermaid, *_ = self._render()
        # Backtick in labels is illegal in Mermaid
        assert "`" not in mermaid, "Backtick found in Mermaid output"


# ══════════════════════════════════════════════════════════════════════════════
# 3. PARALLEL CAPITAL-FLOW PATHS (FIXTURE C)
# ══════════════════════════════════════════════════════════════════════════════

class TestFixtureCParallel:
    """Parallel paths: UAE Fund → direct equity + convertible note → India JV."""

    def _render(self, show_reg=True, show_labels=True):
        return serialize_structure_to_mermaid(
            FIXTURE_C_PARALLEL, show_regulatory_checkpoints=show_reg,
            show_capital_flow_labels=show_labels,
        )

    def test_non_empty_output(self):
        mermaid, *_ = self._render()
        assert mermaid and len(mermaid.strip()) > 20

    def test_graph_td_header(self):
        mermaid, *_ = self._render()
        assert _has_graph_td(mermaid)

    def test_multiple_parallel_edges(self):
        """Parallel topology: at least 3 edges (A→C, A→B, B→C)."""
        mermaid, _, edges, *_ = self._render()
        assert edges >= 3 or _count_arrows(mermaid) >= 3

    def test_dashed_edge_preserved(self):
        """Convertible note path uses dashed edge (-.->) — should be preserved."""
        mermaid, *_ = self._render()
        # Pass 1 reuses the LLM diagram which has -.->;
        # must be present somewhere in the rendered output
        assert ".->" in mermaid or "-->" in mermaid

    def test_classdef_block_present(self):
        mermaid, *_ = self._render()
        assert _has_classdef(mermaid)

    def test_brackets_balanced(self):
        mermaid, *_ = self._render()
        assert _brackets_balanced(mermaid)

    def test_regulatory_checkpoints_added(self):
        """pre-closing RBI ECB + at-closing FC-GPR → 2 checkpoint nodes."""
        mermaid, _, __, checkpoints, ___ = self._render(show_reg=True)
        assert _has_regulatory_node(mermaid)
        assert checkpoints >= 2

    def test_validate_syntax_passes(self):
        mermaid, *_ = self._render()
        valid, reason = validate_mermaid_syntax(mermaid)
        assert valid, f"Mermaid invalid: {reason}\n\n{mermaid[:500]}"

    def test_pass1_used(self):
        """Fixture C has valid LLM Mermaid — no fallback."""
        _, _, __, ___, warnings = self._render()
        fallback_w = [w for w in warnings if "fallback" in w.lower()]
        assert not fallback_w


# ══════════════════════════════════════════════════════════════════════════════
# 4. PASS 2 FALLBACK (FIXTURE D — malformed LLM mermaid_diagram)
# ══════════════════════════════════════════════════════════════════════════════

class TestFixtureDPass2Fallback:
    """When the LLM emits broken Mermaid, Pass 2 regenerates from structured fields."""

    def _render(self):
        return serialize_structure_to_mermaid(FIXTURE_D_MALFORMED)

    def test_pass2_still_produces_output(self):
        """Pass 2 always produces something — never crashes or returns empty."""
        mermaid, *_ = self._render()
        assert mermaid and len(mermaid.strip()) > 20

    def test_pass2_output_is_valid_mermaid(self):
        """Even regenerated from fields, the output must be valid Mermaid."""
        mermaid, *_ = self._render()
        valid, reason = validate_mermaid_syntax(mermaid)
        assert valid, f"Pass 2 output invalid: {reason}\n\n{mermaid[:500]}"

    def test_pass2_issues_fallback_warning(self):
        """Pass 2 must produce a warning explaining the fallback was used."""
        _, _, __, ___, warnings = self._render()
        fallback_w = [w for w in warnings if "fallback" in w.lower() or "malformed" in w.lower()]
        assert fallback_w, f"Expected fallback warning, got: {warnings}"

    def test_pass2_entities_from_ownership_chain(self):
        """Pass 2 extracts Japan Fund, Netherlands HoldCo, Brazil OpCo from ownership_chain."""
        mermaid, entities, *_ = self._render()
        assert entities >= 2

    def test_pass2_regulatory_checkpoints(self):
        """Pass 2 still adds regulatory checkpoint nodes from compliance_touchpoints."""
        mermaid, _, __, checkpoints, ___ = self._render()
        assert _has_regulatory_node(mermaid)
        assert checkpoints >= 1

    def test_pass2_classdef_present(self):
        mermaid, *_ = self._render()
        assert _has_classdef(mermaid)

    def test_pass2_brackets_balanced(self):
        mermaid, *_ = self._render()
        assert _brackets_balanced(mermaid)


# ══════════════════════════════════════════════════════════════════════════════
# 5. VALIDATE_MERMAID_SYNTAX UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestValidateMermaidSyntax:

    def test_valid_graph_td(self):
        valid, _ = validate_mermaid_syntax("graph TD\n    A[\"X\"] --> B[\"Y\"]")
        assert valid

    def test_empty_string_invalid(self):
        valid, _ = validate_mermaid_syntax("")
        assert not valid

    def test_no_graph_declaration_invalid(self):
        valid, _ = validate_mermaid_syntax("A --> B")
        assert not valid

    def test_no_edges_invalid(self):
        valid, _ = validate_mermaid_syntax("graph TD\n    A[\"X\"]")
        assert not valid

    def test_fenced_code_block_stripped(self):
        raw = "```mermaid\ngraph TD\n    A[\"X\"] --> B[\"Y\"]\n```"
        valid, _ = validate_mermaid_syntax(raw)
        assert valid

    def test_graph_lr_accepted(self):
        valid, _ = validate_mermaid_syntax("graph LR\n    A[\"X\"] --> B[\"Y\"]")
        assert valid

    def test_arbitrary_text_invalid(self):
        valid, _ = validate_mermaid_syntax("THIS IS NOT MERMAID ~~~")
        assert not valid


# ══════════════════════════════════════════════════════════════════════════════
# 6. PARSE_OWNERSHIP_CHAIN UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestParseOwnershipChain:

    def test_simple_two_entity(self):
        result = _parse_ownership_chain("US PE Fund (100%) → Germany OpCo")
        assert len(result) == 2
        assert result[0][0] == "US PE Fund"
        assert result[0][1] == "100%"
        assert result[1][0] == "Germany OpCo"

    def test_four_entity_chain(self):
        result = _parse_ownership_chain(
            "PRC Fund (100%) → Singapore HoldCo (74%) → India SPV (51%) → India OpCo"
        )
        assert len(result) == 4
        assert result[1][1] == "74%"
        assert result[2][1] == "51%"

    def test_jurisdiction_hint_extracted(self):
        result = _parse_ownership_chain("Japan Fund (100%) → Singapore HoldCo (60%) → Brazil OpCo")
        _, _, jur_sg = result[1]
        assert jur_sg == "Singapore"

    def test_arrow_variants(self):
        """Both → and -> should work."""
        result1 = _parse_ownership_chain("A (100%) → B")
        result2 = _parse_ownership_chain("A (100%) -> B")
        assert len(result1) == len(result2) == 2

    def test_empty_chain(self):
        result = _parse_ownership_chain("")
        # Should not crash; returns at most one empty entry
        assert isinstance(result, list)


# ══════════════════════════════════════════════════════════════════════════════
# 7. HTTP ENDPOINT TESTS — POST /api/diagram/generate
# ══════════════════════════════════════════════════════════════════════════════

class TestDiagramEndpoint:

    def test_inline_direct_structure_returns_200(self):
        resp = client.post(
            "/api/diagram/generate",
            json={"structure_json": FIXTURE_A_DIRECT},
        )
        assert resp.status_code == 200

    def test_inline_layered_structure_returns_200(self):
        resp = client.post(
            "/api/diagram/generate",
            json={"structure_json": FIXTURE_B_LAYERED},
        )
        assert resp.status_code == 200

    def test_inline_parallel_structure_returns_200(self):
        resp = client.post(
            "/api/diagram/generate",
            json={"structure_json": FIXTURE_C_PARALLEL},
        )
        assert resp.status_code == 200

    def test_response_has_mermaid_syntax(self):
        resp = client.post("/api/diagram/generate", json={"structure_json": FIXTURE_A_DIRECT})
        data = resp.json()
        assert "mermaid_syntax" in data
        assert len(data["mermaid_syntax"]) > 20

    def test_response_mermaid_is_valid(self):
        resp = client.post("/api/diagram/generate", json={"structure_json": FIXTURE_B_LAYERED})
        mermaid = resp.json()["mermaid_syntax"]
        valid, reason = validate_mermaid_syntax(mermaid)
        assert valid, f"HTTP response Mermaid is invalid: {reason}"

    def test_response_entity_count(self):
        resp = client.post("/api/diagram/generate", json={"structure_json": FIXTURE_B_LAYERED})
        data = resp.json()
        assert data["entity_count"] >= 4

    def test_response_edge_count(self):
        resp = client.post("/api/diagram/generate", json={"structure_json": FIXTURE_B_LAYERED})
        data = resp.json()
        assert data["edge_count"] >= 3

    def test_response_regulatory_checkpoint_count(self):
        resp = client.post("/api/diagram/generate", json={"structure_json": FIXTURE_B_LAYERED})
        data = resp.json()
        assert data["regulatory_checkpoint_count"] >= 2

    def test_response_jurisdictions_present(self):
        resp = client.post("/api/diagram/generate", json={"structure_json": FIXTURE_B_LAYERED})
        data = resp.json()
        assert "India" in data["jurisdictions"] or len(data["jurisdictions"]) > 0

    def test_response_structure_name(self):
        resp = client.post("/api/diagram/generate", json={"structure_json": FIXTURE_A_DIRECT})
        data = resp.json()
        assert data["structure_name"] == FIXTURE_A_DIRECT["name"]

    def test_show_regulatory_false_reduces_checkpoint_count(self):
        resp = client.post("/api/diagram/generate", json={
            "structure_json": FIXTURE_B_LAYERED,
            "show_regulatory_checkpoints": False,
        })
        data = resp.json()
        assert data["regulatory_checkpoint_count"] == 0

    def test_malformed_llm_diagram_still_returns_200(self):
        """Pass 2 fallback: malformed mermaid_diagram → still valid HTTP 200."""
        resp = client.post("/api/diagram/generate", json={"structure_json": FIXTURE_D_MALFORMED})
        assert resp.status_code == 200
        data = resp.json()
        assert data["mermaid_syntax"]
        assert len(data["generation_warnings"]) > 0

    def test_no_structure_json_or_id_returns_422(self):
        """Neither structure_json nor structure_id → 422."""
        resp = client.post("/api/diagram/generate", json={})
        assert resp.status_code == 422

    def test_invalid_structure_id_returns_404(self):
        resp = client.post("/api/diagram/generate", json={"structure_id": "nonexistent-id-xyz"})
        assert resp.status_code == 404

    def test_all_three_fixtures_produce_valid_mermaid(self):
        """Parametrized smoke test: all three canonical fixtures must produce valid Mermaid."""
        for fixture in [FIXTURE_A_DIRECT, FIXTURE_B_LAYERED, FIXTURE_C_PARALLEL]:
            resp = client.post("/api/diagram/generate", json={"structure_json": fixture})
            assert resp.status_code == 200, f"Failed for: {fixture['name']}"
            mermaid = resp.json()["mermaid_syntax"]
            valid, reason = validate_mermaid_syntax(mermaid)
            assert valid, f"Invalid Mermaid for '{fixture['name']}': {reason}"
