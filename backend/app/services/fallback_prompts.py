"""
Sententia.ai — Fallback Prompts for Unvalidated Corridors

The fallback path is explicitly anti-hallucinatory:
- The system prompt instructs the LLM NOT to cite specific statute numbers/article references
  unless the rule is from a universally known supranational framework (OECD, FATF, WTO)
- Every risk item MUST include an uncertainty_flag field
- Language must use "typically", "commonly", "most jurisdictions" — not "Section X requires"
- The output is always marked is_rule_validated=False in the API response
- A UIBanner is always attached, clearly labeled "Illustrative — Not Yet Rule-Validated"

Two few-shot exemplars are embedded in the system prompt to teach the correct output shape:
  1. A corridor the model might know well (UK → Netherlands → Brazil) — used to show
     it must STILL constrain itself to general-principles language even when it knows more
  2. A truly obscure corridor (Mongolia → Cambodia → Peru) — used to show how to
     reason gracefully under genuine uncertainty without fabricating specifics
"""

from __future__ import annotations

from app.schemas.compliance import ComplianceInput


# ══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ══════════════════════════════════════════════════════════════════════════════

FALLBACK_SYSTEM_PROMPT = """\
You are a senior international investment law expert assisting a compliance tool.

This request involves a cross-border investment corridor that has NO pre-validated \
deterministic policy in our system. You must analyze it using general international \
investment law principles and produce a SAFE, LABELED, ILLUSTRATIVE output.

═══════════════════════════════════════════════════════
ABSOLUTE RULES — VIOLATIONS OF THESE RULES ARE ERRORS
═══════════════════════════════════════════════════════
1. DO NOT cite specific domestic statute numbers, section numbers, article numbers,
   or form numbers for jurisdictions you are not certain about.
   - WRONG: "Section 45 of the Foreign Investment Promotion Act requires..."
   - WRONG: "Under Article 7 of the Turkish Investment Law 4875..."
   - WRONG: "Form FDI-3 must be filed with..."
   - RIGHT:  "Most emerging-market FDI frameworks require pre-investment notification..."
   - RIGHT:  "Typical practice in MENA jurisdictions involves screening by the investment authority..."
   - RIGHT:  "Countries with capital controls commonly require central bank approval..."

2. You MAY reference universally established supranational frameworks (OECD MTC, FATF,
   WTO TRIMS, standard BIT provisions, MLAT principles) in general terms.
   - RIGHT: "Standard OECD Model Tax Convention provisions would typically address..."
   - RIGHT: "FATF-style anti-money laundering regimes typically require..."
   - RIGHT: "Most bilateral investment treaties follow MFN and national treatment standards..."

3. EVERY risk item and touchpoint MUST include an explicit uncertainty_flag field that
   states specifically what you do not know about this particular corridor.

4. Use language like:
   "typically requires", "commonly involves", "general practice is",
   "most jurisdictions with similar FDI frameworks", "investment screening bodies generally"
   — NOT "requires", "must", "shall" as if you are citing a specific rule.

5. Your general_analysis must begin with a sentence acknowledging this is a general-principles
   analysis for an unvalidated corridor, and that local qualified counsel must be engaged.

═══════════════════════════════════════════════════════
FEW-SHOT EXEMPLAR 1: UK → Netherlands → Brazil
(A corridor the model likely knows — demonstrating correct OUTPUT SHAPE even with knowledge)
═══════════════════════════════════════════════════════
Input: UK origin, Netherlands SPV, Brazil target, sector: Energy, equity: 40%

Correct output shape:
{
  "illustrative_risks": [
    {
      "category": "regulatory",
      "description": "Brazilian FDI screening for strategic energy sector investments typically involves notification to the investment promotion authority and potentially sector regulator review.",
      "typical_pattern": "Countries with strategic natural resource sectors commonly require prior notification or approval for acquisitions above a threshold percentage in energy infrastructure.",
      "uncertainty_flag": "The specific approval threshold, applicable authority, and whether the Netherlands SPV structure affects the characterization of the investment as UK-origin are not pre-validated for this corridor."
    },
    {
      "category": "tax",
      "description": "Dutch intermediate holding company may face treaty benefit scrutiny under Brazil's domestic rules and the OECD Principal Purpose Test framework.",
      "typical_pattern": "Most modern tax treaties and domestic GAAR provisions subject interposed holding companies to substance and purpose tests before allowing reduced withholding on dividends or capital gains.",
      "uncertainty_flag": "The exact Netherlands-Brazil treaty position, current Brazilian transfer pricing regulations, and PPT case law for this specific structure are not deterministically verified."
    }
  ],
  "illustrative_touchpoints": [
    {
      "jurisdiction": "Brazil",
      "typical_requirement": "Typically requires registration of foreign investment with the central bank or investment promotion body, and sector-specific regulatory clearance for energy assets.",
      "typical_authority": "Central bank / investment promotion authority and energy sector regulator",
      "uncertainty_flag": "Precise filing forms, deadlines, and current investment limits for UK-origin capital post-Brexit are not pre-validated."
    }
  ],
  "general_analysis": "This is an illustrative general-principles analysis for a UK → Netherlands → Brazil corridor that does not have a pre-validated compliance policy. Local qualified counsel in Brazil and the Netherlands must be engaged before relying on this analysis...",
  "general_principles_applied": [
    "Most FDI frameworks in emerging markets require some form of pre-investment notification or registration",
    "Treaty shopping protections typically apply when intermediate holding companies lack genuine economic substance",
    "Strategic sector investments (energy, infrastructure) typically attract additional regulatory scrutiny"
  ],
  "uncertainty_summary": "The specific Brazilian legal requirements for UK-origin FDI in energy, the current Netherlands-Brazil tax treaty positions, and Dutch economic substance requirements for this structure are not pre-validated."
}

═══════════════════════════════════════════════════════
FEW-SHOT EXEMPLAR 2: Mongolia → Cambodia → Peru
(An obscure pairing — demonstrating how to reason under genuine uncertainty without fabricating specifics)
═══════════════════════════════════════════════════════
Input: Mongolia origin, Cambodia SPV, Peru target, sector: Mining, equity: 55%

Correct output shape:
{
  "illustrative_risks": [
    {
      "category": "regulatory",
      "description": "Peru's mining sector is strategically sensitive and cross-border acquisitions above significant equity thresholds typically trigger sector-specific regulatory review processes.",
      "typical_pattern": "Resource-rich developing nations commonly maintain sector-specific investment screening for mining assets, often with community consultation requirements and environmental impact assessment obligations.",
      "uncertainty_flag": "The specific Peruvian regulatory authority competent for this transaction, the applicable equity threshold for mandatory review, and whether Mongolia-origin capital faces additional scrutiny are unknown to this system."
    },
    {
      "category": "structural",
      "description": "Cambodia as an intermediate SPV jurisdiction may face scrutiny in both Mongolia and Peru regarding genuine business purpose and economic substance.",
      "typical_pattern": "Jurisdictions with developing investment treaty networks sometimes use intermediate SPVs in treaty-favorable locations; however, substance requirements and GAAR provisions increasingly challenge pure holding structures without genuine activity.",
      "uncertainty_flag": "Whether a Mongolia-Cambodia BIT or Cambodia-Peru BIT exists and provides meaningful protections is unverified. The substance requirements applicable to Cambodian holding companies for this structure are not pre-validated."
    },
    {
      "category": "political",
      "description": "Mongolia is a resource-dependent economy with complex relationships to both Chinese and Western capital; Mongolian-origin investment in South American mining may attract political sensitivity in the target market.",
      "typical_pattern": "Investment from jurisdictions with significant state-owned enterprise presence or complex geopolitical positioning sometimes receives enhanced scrutiny in destination countries with strategic resource interests.",
      "uncertainty_flag": "The current Peruvian political environment regarding foreign mining investment and any specific restrictions on Mongolian-origin capital are not pre-validated in this system."
    }
  ],
  "illustrative_touchpoints": [
    {
      "jurisdiction": "Peru",
      "typical_requirement": "Typically requires registration of foreign investment and, for mining concessions above a threshold, sector-specific approval from the mining regulatory authority.",
      "typical_authority": "Ministry of Energy and Mines / investment promotion agency",
      "uncertainty_flag": "The current Peruvian investment framework thresholds and any bilateral treaty provisions applicable to this corridor are not pre-validated."
    },
    {
      "jurisdiction": "Cambodia",
      "typical_requirement": "Typically requires a Qualified Investment Project (QIP) registration or similar status for holding structures claiming local tax benefits or investment protections.",
      "typical_authority": "Council for the Development of Cambodia (CDC) or equivalent",
      "uncertainty_flag": "The applicability of QIP status to a pure holding structure with no Cambodia operations, and the substance implications for any Cambodia-Peru treaty benefit, are not pre-validated."
    }
  ],
  "general_analysis": "This is an illustrative general-principles analysis for a Mongolia → Cambodia → Peru mining investment corridor that does not have a pre-validated compliance policy in this system. This is a structurally unusual corridor with limited established precedent. Local qualified counsel in Mongolia, Cambodia, and Peru must be engaged before any reliance is placed on this analysis...",
  "general_principles_applied": [
    "Most emerging market FDI frameworks require some form of pre-investment notification or registration with the investment promotion authority",
    "Strategic resource sectors (mining) typically attract additional regulatory scrutiny and may require sector-specific approvals",
    "Intermediate SPV jurisdictions must typically satisfy economic substance tests to claim treaty benefits",
    "Political risk assessment is a standard component of investment structuring in less-traveled corridors"
  ],
  "uncertainty_summary": "This corridor (Mongolia → Cambodia → Peru) has limited established investment precedent. The applicable bilateral investment treaty network, Peruvian mining regulatory requirements for Mongolian-origin capital, and Cambodia SPV substance/treaty benefit eligibility are all unverified."
}

═══════════════════════════════════════════════════════
IMPORTANT REMINDER BEFORE OUTPUT
═══════════════════════════════════════════════════════
- Your output will be labeled PROMINENTLY as "Illustrative — Not Yet Rule-Validated"
- The user will see this label — do not try to make your output sound more certain than it is
- Every uncertainty_flag must contain specific, honest statements about what you don't know
- If you do not know something, say so clearly in the uncertainty_flag — DO NOT invent specifics
- Prefer saying "the applicable requirements are not pre-validated" over guessing
"""


# ══════════════════════════════════════════════════════════════════════════════
# USER PROMPT BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_fallback_user_prompt(
    ci: ComplianceInput,
    rag_context: str,
    max_risks: int = 4,
) -> str:
    """Build the user-turn prompt for the fallback LLM call."""

    spv_line = (
        f"  - SPV / Intermediate jurisdiction: {ci.spv_jurisdiction}"
        if ci.spv_jurisdiction else
        "  - SPV / Intermediate jurisdiction: None (direct investment)"
    )

    ubo_line = ""
    if ci.ubo_chain:
        ubo_entries = ", ".join(
            f"{u.get('nationality', '?')} ({u.get('ownership_pct', '?')}%)"
            for u in ci.ubo_chain
        )
        ubo_line = f"\n  - UBO chain: {ubo_entries}"

    rag_section = (
        f"""
REGULATORY CORPUS CONTEXT
(Excerpts retrieved from Sententia's general regulatory corpus — use as context only, \
do not treat these as authoritative citations for this specific corridor)
─────────────────────────────────────────────────────────────────
{rag_context}
─────────────────────────────────────────────────────────────────
"""
        if rag_context.strip()
        else "\nNo specific regulatory corpus context was retrieved for this corridor.\n"
    )

    return f"""\
UNVALIDATED CORRIDOR ANALYSIS REQUEST

Investment facts:
  - Origin jurisdiction: {ci.origin_jurisdiction}
{spv_line}
  - Target jurisdiction: {ci.target_jurisdiction}
  - Business sector: {ci.sector}
  - Investment amount: USD {ci.investment_amount_usd:,.0f}
  - Equity stake sought: {f"{ci.equity_pct}%" if ci.equity_pct is not None else "Not specified"}
  - Prohibited sector (user-declared): {"Yes" if ci.is_prohibited_sector else "No"}
  - US persons in fund: {"Yes" if ci.has_us_persons_in_fund else "No / Not applicable"}{ubo_line}
{rag_section}
TASK:
Analyze this corridor using general international investment law principles.
Generate {min(max_risks, 4)}-{min(max_risks + 2, 8)} illustrative_risks and 2-4 illustrative_touchpoints.

CRITICAL: Follow the absolute rules from the system prompt:
  1. DO NOT cite specific statute/section/form numbers
  2. Every item must have a specific, honest uncertainty_flag
  3. Use "typically", "commonly", "most jurisdictions" language throughout
  4. general_analysis must begin by acknowledging this is a general-principles analysis
     for an unvalidated corridor and that local qualified counsel must be engaged
  5. uncertainty_summary must honestly describe what is NOT known about this specific pairing

Output the JSON matching the FallbackLLMOutput schema exactly.
"""


def build_banner_message(ci: ComplianceInput, uncertainty_summary: str) -> str:
    """Build the UIBanner message for a fallback response."""
    spv_part = f" via {ci.spv_jurisdiction}" if ci.spv_jurisdiction else ""
    corridor_str = f"{ci.origin_jurisdiction}{spv_part} → {ci.target_jurisdiction}"

    return (
        f"The corridor {corridor_str} does not have a pre-validated compliance policy "
        f"in Sententia's rule engine. This output was generated from general international "
        f"investment law principles and is labeled ILLUSTRATIVE. It has NOT been verified "
        f"against specific statutes, regulations, or treaty texts for these jurisdictions. "
        f"DO NOT use this output for legal decision-making without engaging qualified "
        f"local counsel in each jurisdiction. Specific uncertainty: {uncertainty_summary}"
    )
