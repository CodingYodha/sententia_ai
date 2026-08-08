"""
Sententia.ai — Simulation Service

Loads authoritative pre-generated structuring assets from simulation_template_folder/
and synthesizes a full StructureGenerationResponse, including line-by-line AI agent
reasoning steps and proposed execution timeline data.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import os
import time

from pathlib import Path
from typing import Any

from app.schemas.intake import ScenarioCreate
from app.schemas.structures import (
    ComplianceTiming,
    ComplianceTouchpoint,
    IdentifiedRisk,
    ImplementationStep,
    RegulatoryConfidence,
    RiskSeverity,
    RiskType,
    SetupComplexity,
    StructuringAlternative,
    StructureGenerationResponse,
)

logger = logging.getLogger(__name__)

# ── Safe Asset Location Resolver ──────────────────────────────────────────────
def _get_simulation_folder() -> Path:
    """Locates simulation_template_folder across current and parent directory hierarchies."""
    candidates = [
        Path(__file__).resolve().parents[3] / "simulation_template_folder",
        Path.cwd() / "simulation_template_folder",
        Path.cwd().parent / "simulation_template_folder",
        Path("simulation_template_folder"),
    ]
    for p in candidates:
        if p.exists() and p.is_dir():
            return p
    raise FileNotFoundError(f"simulation_template_folder not found in candidates: {[str(c) for c in candidates]}")


def _load_asset(filename: str) -> str:
    """Loads a text/markdown/mmd file from simulation_template_folder safely."""
    try:
        folder = _get_simulation_folder()
        file_path = folder / filename
        if not file_path.exists():
            logger.warning(f"Simulation asset missing: {file_path}")
            return ""
        content = file_path.read_text(encoding="utf-8")
        if filename.endswith(".mmd"):
            import re
            content = re.sub(r"^---[\s\S]*?---\s*", "", content)
            content = re.sub(r"<b>(.*?)<\/b>", r"\1", content, flags=re.IGNORECASE)
            content = re.sub(r"<i>(.*?)<\/i>", r"\1", content, flags=re.IGNORECASE)
            content = re.sub(r'-\.\s*"([^"]+)"\s*\.-\s*>', r'-.-|"\1"|', content)
            content = re.sub(r'-\.\s*"([^"]+)"\s*\.->', r'-.-|"\1"|', content)
            content = re.sub(r'-\.\s+([^\.]+)\s+\.-\s*>', r'-.-|"\1"|', content)
            content = re.sub(r'-\.\s+([^\.]+)\s+\.->', r'-.-|"\1"|', content)
            content = content.strip()
        return content

    except Exception as e:
        logger.warning(f"Error loading simulation asset {filename}: {e}")
        return ""



# ── Matcher Function ──────────────────────────────────────────────────────────
def is_simulation_triggered(scenario: ScenarioCreate, config_mode: str) -> bool:
    """
    Checks if simulation mode should be active.
    - "true" / "1" / "yes" -> Always active
    - "false" / "0" / "no" -> Never active
    - "auto" -> Active if corridor matches US-India Education or keywords match Ananta/PropCo
    """
    mode = config_mode.lower().strip()
    if mode in ("true", "1", "yes"):
        return True
    if mode in ("false", "0", "no"):
        return False

    # "auto" detection logic
    origin = scenario.capital_origin.lower()
    target = scenario.target_jurisdiction.lower()
    sector = scenario.sector.lower()
    notes  = (scenario.notes or "").lower()

    keywords = {"ananta", "propco", "opco", "jireh", "prf", "school", "k-12", "meridian"}
    if any(kw in notes for kw in keywords):
        return True

    is_us_india = origin in ("us", "usa", "united states") and target in ("in", "ind", "india")
    is_edu = "edu" in sector or "school" in sector
    return is_us_india and is_edu


# ── Main Generator ────────────────────────────────────────────────────────────
async def generate_simulated_structure(
    scenario: ScenarioCreate,
    delay_seconds: float = 6.5,
) -> StructureGenerationResponse:
    """
    Simulates live AI structure generation by loading authoritative templates
    from simulation_template_folder and waiting for delay_seconds (5-8s).
    """
    t_start = time.monotonic()
    logger.info(f"Running Simulation Generation for {scenario.capital_origin} -> {scenario.target_jurisdiction} ({scenario.sector})")

    # Staged non-blocking delay to simulate real-time AI reasoning (5-8s)
    if delay_seconds > 0:
        await asyncio.sleep(delay_seconds)

    # ── Load diagram assets ────────────────────────────────────────────────────
    diag1 = _load_asset("diagram1.mmd") or """flowchart TB

subgraph USA
direction LR
MGF["Meridian Grace<br/>Foundation (MGF)<br/>US 501(c)(3) non-profit"]
AEP["Atlas Education<br/>Partners LLC (AEP)<br/>Delaware LLC investor"]
MGF -.-|"co-invest under a<br/>Term Sheet"| AEP
end

subgraph INDIA
direction TB
PROP["Meridian Campus<br/>Infrastructure Pvt. Ltd.<br/>('PropCo')<br/>Indian WOS<br/>owns land & school building"]
OPCO["Ananta Educare<br/>Pvt. Ltd.<br/>('OpCo')<br/>for-profit Educational<br/>Services Company (ESC)"]
AET["Ananta Education Trust<br/>('AET')<br/>registered public charitable trust,<br/>holds CBSE affiliation,<br/>runs on no-profit-no-loss basis"]
SCHOOL(("Ananta International School<br/>(Pune, Maharashtra - CBSE)"))

PROP -->|"Registered long-term<br/>Lease Deed (campus)"| AET
OPCO -->|"Management &<br/>Consultancy Agreement"| AET
AET -.-|"operates"| SCHOOL
end

MGF -->|"FDI: equity shares<br/>(incorporation) +<br/>CCPS (capex tranche)"| PROP
AEP -->|"FDI: equity shares<br/>(FMV valuation,<br/>FC-GPR reporting)"| OPCO"""

    diag2 = _load_asset("diagram2.mmd") or """flowchart TB

subgraph USA
direction LR
MGF["Meridian Grace<br/>Foundation (MGF)"]
AEP["Atlas Education<br/>Partners LLC (AEP)"]
end

subgraph INDIA
direction TB
PROP["Meridian Campus<br/>Infrastructure Pvt. Ltd.<br/>('PropCo')"]
OPCO["Ananta Educare<br/>Pvt. Ltd.<br/>('OpCo')"]
AET["Ananta Education Trust<br/>('AET')<br/>school operator,<br/>no dividend capacity"]
FUNDS(("School fee collections fund<br/>lease rent + consultancy fees<br/>+ reasonable surplus (6–15%)"))

FUNDS -.- AET
AET -->|"Lease rental<br/>(Sec.194-I TDS 10% +<br/>18% GST - domestic,<br/>both Indian residents)"| PROP
AET -->|"Consultancy fees<br/>(arm's length,<br/>transfer-pricing tested;<br/>18% GST)"| OPCO
end

PROP -->|"Dividends<br/>(Art.10 India-US DTAA:<br/>15% -> >=10% voting stock)"| MGF
OPCO -->|"Dividends<br/>(Art.10 India-US DTAA:<br/>15% -> >=10% voting stock)"| AEP"""

    diag3 = _load_asset("diagram3.mmd") or """flowchart TB

subgraph USA
direction LR
MGF["Meridian Grace<br/>Foundation (MGF)"]
AEP["Atlas Education<br/>Partners LLC (AEP)"]
JV["Meridian-Atlas<br/>Education JV LLC<br/>(Delaware)<br/><br/>JV LLC allocates returns to MGF & AEP<br/>per Operating Agreement split"]

MGF -->|"capitalize jointly,<br/>per agreed split"| JV
AEP -->|"capitalize jointly,<br/>per agreed split"| JV
end

subgraph INDIA
direction TB
PROP["Meridian Campus<br/>Infrastructure Pvt. Ltd.<br/>('PropCo')<br/>sole FDI conduit<br/>for the campus"]
OPCO["Ananta Educare<br/>Pvt. Ltd.<br/>('OpCo')<br/>sole FDI conduit<br/>for school services"]
AET["Ananta Education Trust<br/>('AET')<br/>lease + consultancy<br/>counterparty for both entities"]

PROP --> AET
OPCO --> AET
end

JV -->|"single FDI<br/>tranche"| PROP
JV -->|"single FDI<br/>tranche"| OPCO

PROP -->|"dividends up<br/>to JV LLC"| JV
OPCO -->|"dividends up<br/>to JV LLC"| JV"""


    # ── Build Line-by-Line AI Reasoning Steps ──────────────────────────────────
    reasoning_steps = [
        "Analyzing deal scenario parameters: Capital Origin = USA, Target Jurisdiction = India, Sector = K-12 Education.",
        "Evaluating statutory constraints: Checking RTE Act 2009 & CBSE Affiliation Bye-Laws 'no-profit-no-loss' non-proprietary requirement.",
        "Reviewing Supreme Court precedents: T.M.A. Pai, Islamic Academy (permitting 6–15% reasonable surplus), and Modern Dental College rulings.",
        "Verifying FEMA (NDI) Rules Schedule I: Confirming 'real estate business' exemption for earning rent on educational infrastructure leases.",
        "Assessing Tax Treaties & Repatriation: India-US DTAA Art. 10 dividend capping (15%), Section 194-I TDS (10%), and GST (18%) implications.",
        "Insulating FCRA exposure: Verifying WOS structure prevents foreign non-profit contributions from touching non-profit school trust.",
        "Synthesizing ranked structuring alternatives and serializing interactive Mermaid flow diagrams.",
    ]

    # ── Build Alternatives ────────────────────────────────────────────────────
    alt1 = StructuringAlternative(
        rank=1,
        name="PropCo–OpCo Dual Vehicle Structure (Project Ananta Model)",
        structure_type="spv_layered",
        architecture_description=(
            "The primary investment structure routes capital through two separate for-profit Indian vehicles: "
            "Meridian Campus Infrastructure Pvt. Ltd. ('PropCo') owns the land and campus buildings, leasing them to "
            "Ananta Education Trust under a registered long-term Lease Deed. Ananta Educare Pvt. Ltd. ('OpCo') provides "
            "paid marketing, admissions, teacher training, and financial oversight services. Ananta Education Trust (AET) "
            "holds the CBSE affiliation and operates Ananta International School on a no-profit-no-loss basis, ensuring full "
            "compliance with the RTE Act 2009 and settled Supreme Court jurisprudence."
        ),
        ownership_chain="USA Investors (MGF 501(c)(3) & AEP LLC) -> Indian WOS (PropCo & OpCo) -> Ananta Education Trust (CBSE School)",
        jurisdictions_involved=["USA", "India"],
        mermaid_diagram=diag1,
        compliance_touchpoints=[
            ComplianceTouchpoint(
                jurisdiction="India",
                requirement="FEMA FC-GPR filing within 30 days of allotment for equity/CCPS issuance",
                timing=ComplianceTiming.POST_CLOSING,
                authority="Reserve Bank of India (RBI) / AD Bank",
                notes="Requires Merchant Banker / CA Fair Market Valuation (FMV) report upfront."
            ),
            ComplianceTouchpoint(
                jurisdiction="India",
                requirement="Section 194-I TDS (10%) deduction on Lease Rental payments from Trust to PropCo",
                timing=ComplianceTiming.ONGOING,
                authority="Income Tax Department (CBDT)",
                notes="18% GST applies to commercial real estate leasing; TDS computed net of GST."
            ),
            ComplianceTouchpoint(
                jurisdiction="India",
                requirement="CBSE Affiliation Bye-Laws non-proprietary character compliance",
                timing=ComplianceTiming.PRE_CLOSING,
                authority="Central Board of Secondary Education (CBSE)",
                notes="Trust managing body must maintain non-proprietary character without direct dividend distribution."
            ),
            ComplianceTouchpoint(
                jurisdiction="USA",
                requirement="Form 5471 / 8865 annual foreign corporate entity disclosures",
                timing=ComplianceTiming.POST_CLOSING,
                authority="Internal Revenue Service (IRS)",
                notes="Filing required for US parent entities holding 100% WOS equity."
            ),
        ],
        cited_sources=[
            "FEMA (Non-Debt Instruments) Rules, 2019 — Schedule I Real Estate Lease Carve-out",
            "CBSE Affiliation Bye-Laws (Non-Profit Mandate)",
            "Supreme Court Judgment: Modern Dental College & Research Centre v. State of M.P. (2016) 7 SCC 353",
            "Supreme Court Judgment: Islamic Academy of Education v. State of Karnataka (2003) 6 SCC 697",
            "India-US Double Tax Avoidance Agreement (DTAA) — Article 10 (Dividends)",
        ],
        identified_risks=[
            IdentifiedRisk(
                risk_type=RiskType.REGULATORY,
                description="GAAR / General Anti-Avoidance Rule scrutiny if lease rentals or service fees are deemed excessive.",
                severity=RiskSeverity.MEDIUM,
                mitigation="Maintain strict arm's-length valuation reports for lease rent and transfer pricing documentation for service fees."
            ),
            IdentifiedRisk(
                risk_type=RiskType.LEGAL,
                description="State Fee Regulatory Committee disallowance of inflated school operating expenses.",
                severity=RiskSeverity.LOW,
                mitigation="Ensure lease terms align with market rates and surplus retained by Trust remains within 6–15% reasonable bounds."
            ),
            IdentifiedRisk(
                risk_type=RiskType.REGULATORY,
                description="FCRA 2011 scrutiny if foreign non-profit donor funds touch Indian non-profit trust directly.",
                severity=RiskSeverity.HIGH,
                mitigation="Complete WOS insulation: foreign capital flows strictly as FDI equity into for-profit PropCo/OpCo, never into the Trust."
            ),
        ],
        implementation_steps=[
            ImplementationStep(
                step_number=1,
                phase="Phase 1: Structure Setup & Term Sheet",
                title="Execute Investor Co-Investment Term Sheet & Incorp PropCo WOS",
                description="Incorporate Meridian Campus Infrastructure Pvt. Ltd. as an Indian private limited company (2 directors, 1 Indian resident). Execute term sheet between MGF and AEP.",
                key_deliverables=["Certificate of Incorporation", "PAN/TAN/DIN/DSC", "Signed Co-Investment Term Sheet"],
                estimated_timeline="2-3 weeks"
            ),
            ImplementationStep(
                step_number=2,
                phase="Phase 2: Land Lease & Operational SLAs",
                title="Execute Long-Term Campus Lease Deed & Management Agreement",
                description="Register 30-year campus lease deed between PropCo and Ananta Education Trust at market rental valuation. Sign OpCo Consultancy Agreement.",
                key_deliverables=["Registered Lease Deed", "Management & Consultancy SLA", "Valuation Certificate"],
                estimated_timeline="3-4 weeks"
            ),
            ImplementationStep(
                step_number=3,
                phase="Phase 3: Capital Remittance & Share Allotment",
                title="Remit Foreign FDI Funds & Issue Equity/CCPS Shares",
                description="Remit FDI via normal banking channels to AD Bank account. Issue CCPS/Equity shares to MGF and AEP at FMV valuation.",
                key_deliverables=["FIRC (Foreign Inward Remittance Cert)", "Share Certificates", "FC-GPR FIRMS Receipt"],
                estimated_timeline="2 weeks"
            ),
            ImplementationStep(
                step_number=4,
                phase="Phase 4: Post-Closing Compliance",
                title="File Annual Returns & Maintain Transfer Pricing Files",
                description="File FLA annual return with RBI, maintain transfer pricing documentation for OpCo services, and file 194-I TDS returns.",
                key_deliverables=["FLA Acknowledgement", "Transfer Pricing Study", "Quarterly TDS Filings"],
                estimated_timeline="Ongoing"
            ),
        ],
        rationale="Top-ranked structure because it fully isolates the non-profit school operator while providing legally sound 100% FDI channels for campus infrastructure and services.",
        estimated_setup_complexity=SetupComplexity.MEDIUM,
        regulatory_confidence=RegulatoryConfidence.HIGH,
    )

    alt2 = StructuringAlternative(
        rank=2,
        name="Delaware Joint Venture (JV LLC) Holding Structure",
        structure_type="joint_venture",
        architecture_description=(
            "MGF and AEP co-invest into a single Delaware holding vehicle: Meridian-Atlas Education JV LLC. "
            "The JV LLC then injects a single consolidated FDI tranche into PropCo and OpCo in India. Dividend returns "
            "from PropCo and OpCo flow up to the JV LLC in Delaware before being distributed to MGF and AEP per the JV Operating Agreement."
        ),
        ownership_chain="MGF (US) + AEP (US) -> Delaware JV LLC -> Indian PropCo & OpCo -> Ananta Education Trust",
        jurisdictions_involved=["USA", "India", "Delaware (US)"],
        mermaid_diagram=diag3,
        compliance_touchpoints=[
            ComplianceTouchpoint(
                jurisdiction="USA",
                requirement="Delaware LLC Operating Agreement & Joint Governance Framework",
                timing=ComplianceTiming.PRE_SIGNING,
                authority="Delaware Division of Corporations",
                notes="Defines return allocations, deadlock mechanisms, and capital contribution calls."
            ),
            ComplianceTouchpoint(
                jurisdiction="India",
                requirement="Single Foreign Direct Investment (FDI) reporting on RBI FIRMS portal",
                timing=ComplianceTiming.POST_CLOSING,
                authority="Reserve Bank of India (RBI)",
                notes="Consolidated FC-GPR filing for JV LLC investment into PropCo."
            ),
        ],
        cited_sources=[
            "FEMA Non-Debt Instruments Rules, 2019",
            "Delaware Limited Liability Company Act",
            "India-US Double Tax Avoidance Agreement (Article 10)",
        ],
        identified_risks=[
            IdentifiedRisk(
                risk_type=RiskType.OPERATIONAL,
                description="Governance deadlock risk between MGF and AEP at the Delaware JV level.",
                severity=RiskSeverity.MEDIUM,
                mitigation="Include clear shotgun clause or third-party arbitration in the Delaware Operating Agreement."
            )
        ],
        implementation_steps=[
            ImplementationStep(
                step_number=1,
                phase="Phase 1: Delaware JV Setup",
                title="Incorporate Delaware JV LLC & Draft Operating Agreement",
                description="File Certificate of Formation in Delaware and finalize Operating Agreement between MGF and AEP.",
                key_deliverables=["Delaware LLC Certificate", "LLC Operating Agreement"],
                estimated_timeline="1-2 weeks"
            )
        ],
        rationale="Ranked second: provides unified investor governance in the US, but introduces an extra holding layer and tax pass-through complexity.",
        estimated_setup_complexity=SetupComplexity.HIGH,
        regulatory_confidence=RegulatoryConfidence.HIGH,
    )

    alt3 = StructuringAlternative(
        rank=3,
        name="Direct FDI & Lease Fee Repatriation Structure",
        structure_type="direct_fdi",
        architecture_description=(
            "Focuses on direct fee repatriation and lease rental flows: Ananta Education Trust receives school fees "
            "and pays commercial lease rent to PropCo and consultancy fees to OpCo. Annual profits are repatriated to "
            "MGF and AEP as foreign dividends under Article 10 of the India-US Tax Treaty."
        ),
        ownership_chain="School Fee Surplus -> Ananta Education Trust -> PropCo & OpCo (India) -> DTAA Art. 10 Dividends -> MGF & AEP (USA)",
        jurisdictions_involved=["USA", "India"],

        mermaid_diagram=diag2,
        compliance_touchpoints=[
            ComplianceTouchpoint(
                jurisdiction="India",
                requirement="Arm's-length transfer pricing documentation for consultancy fees",
                timing=ComplianceTiming.ONGOING,
                authority="Income Tax Department (Transfer Pricing Officer)",
                notes="18% GST applies on educational consultancy services."
            )
        ],
        cited_sources=[
            "Income Tax Act 1961 — Section 92 (Transfer Pricing)",
            "India-US DTAA — Article 12 (Fees for Included Services)",
        ],
        identified_risks=[
            IdentifiedRisk(
                risk_type=RiskType.TAX,
                description="Disallowance of consultancy fees under DTAA 'make available' scrutiny.",
                severity=RiskSeverity.MEDIUM,
                mitigation="Structure services as managerial/consulting rather than technical transfer of know-how."
            )
        ],
        implementation_steps=[
            ImplementationStep(
                step_number=1,
                phase="Phase 1: OpCo Incorporation",
                title="Incorporate Ananta Educare Pvt. Ltd. and Execute Service SLA",
                description="Set up for-profit ESC entity and sign management agreement with Trust.",
                key_deliverables=["OpCo Incorporation Cert", "Consultancy SLA"],
                estimated_timeline="2-3 weeks"
            )
        ],
        rationale="Ranked third: faster setup if campus real estate is already acquired, but provides less asset security for foreign capital.",
        estimated_setup_complexity=SetupComplexity.LOW,
        regulatory_confidence=RegulatoryConfidence.MEDIUM,
    )

    # ── Build Execution Timeline Data ─────────────────────────────────────────
    def _dyn_date(day_offset: int) -> str:
        d = datetime.now() + timedelta(days=day_offset)
        return d.strftime("%d %b %Y")

    proposed_timeline = {
        "usa_phase": [
            {"task": "Term Sheet Execution", "date": _dyn_date(8), "completed": True},
            {"task": "Delaware LLC Formation", "date": _dyn_date(10), "completed": True},
            {"task": "Name Reservation & IRS EIN", "date": _dyn_date(15), "completed": True},
        ],
        "india_phase": [
            {"task": "PropCo WOS Incorporation", "date": _dyn_date(22), "completed": True},
            {"task": "Registered Campus Lease Deed", "date": _dyn_date(25), "completed": True},
            {"task": "OpCo Consultancy Agreement", "date": _dyn_date(34), "completed": True},
            {"task": "FDI Capital Injection & FC-GPR", "date": _dyn_date(42), "completed": True},
        ],

        "gantt_tasks": [
            {"id": "t1", "name": "Term Sheet", "phase": "USA", "start_day": 3, "end_day": 8, "status": "completed"},
            {"id": "t2", "name": "Delaware LLC Formation", "phase": "USA", "start_day": 5, "end_day": 10, "status": "completed"},
            {"id": "t3", "name": "Name Reservation", "phase": "USA", "start_day": 8, "end_day": 15, "status": "completed"},
            {"id": "t4", "name": "PropCo Incorporation", "phase": "India", "start_day": 10, "end_day": 22, "status": "completed"},
            {"id": "t5", "name": "Registered Lease Deed", "phase": "India", "start_day": 15, "end_day": 25, "status": "completed"},
            {"id": "t6", "name": "OpCo SLA Signing", "phase": "India", "start_day": 22, "end_day": 34, "status": "completed"},
            {"id": "t7", "name": "FDI Remittance & Allotment", "phase": "India", "start_day": 25, "end_day": 36, "status": "completed"},
            {"id": "t8", "name": "FC-GPR Reporting (FIRMS)", "phase": "India", "start_day": 34, "end_day": 42, "status": "completed"},
            {"id": "t9", "name": "CBSE Operational Clearance", "phase": "India", "start_day": 36, "end_day": 45, "status": "active"},
        ]
    }

    t_total_ms = int((time.monotonic() - t_start) * 1000)

    general_analysis_md = (
        "### Regulatory Analysis — US-to-India K-12 Education FDI Corridor\n\n"
        "1. **No-Profit-No-Loss Mandate:** Statutory rules under the Right to Education (RTE) Act 2009 "
        "and CBSE Affiliation Bye-Laws mandate that K-12 schools be run by non-profit societies, trusts, or Section 8 companies. "
        "A settled line of Supreme Court precedent (*T.M.A. Pai*, *Islamic Academy*, *Modern Dental College*) affirms that education "
        "is a noble occupation that does not permit commercialization or dividend extraction from the school entity.\n\n"
        "2. **FDI Exemption & PropCo Real Estate Lease:** 100% FDI is permitted under the automatic route in education services "
        "and construction-development of educational institutions. Crucially, Schedule I of the FEMA (Non-Debt Instruments) Rules "
        "expressly carves out *'earning of rent or income on lease of the property, not amounting to transfer'* from prohibited real estate business. "
        "This legal lynchpin enables a foreign-owned PropCo to construct school facilities and earn commercial lease rentals.\n\n"
        "3. **FCRA & Anti-Avoidance Insulation:** Channelling investments through a for-profit PropCo/OpCo prevents foreign funds "
        "from directly touching the non-profit school trust, completely avoiding FCRA 2011 'foreign contribution' triggers. Arm's-length "
        "pricing and market-rate lease terms ensure the structure withstands GAAR scrutiny while enabling compliant capital repatriation."
    )

    return StructureGenerationResponse(
        scenario_summary=f"{scenario.capital_origin} → {scenario.target_jurisdiction} ({scenario.sector} - Project Ananta Model)",
        alternatives=[alt1, alt2, alt3],
        general_analysis=general_analysis_md,
        recommended_alternative_rank=1,
        disclaimer=(
            "⚡ Sententia.ai Simulation Mode: Output generated from pre-validated Project Ananta regulatory templates. "
            "Always verify with qualified legal counsel before closing."
        ),
        rag_sources_used=5,
        llm_provider_used="sententia_simulation_engine",
        rag_corpus_coverage="direct",
        generation_time_ms=t_total_ms,
        reasoning_steps=reasoning_steps,
        proposed_timeline=proposed_timeline,
    )
