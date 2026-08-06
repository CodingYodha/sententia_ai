"""
Sententia.ai — Python-Native Policy Evaluator

Faithful Python mirror of the Rego policies in policies/rego/*.rego.
Used when no OPA server or OPA binary is available (dev/test environments).

IMPORTANT: The Rego files in policies/rego/ are the AUTHORITATIVE policy definitions.
This Python implementation is kept in sync with them. Any change to the Rego
policies must be reflected here. Both are tested against the same test cases.

Evaluators:
  IndiaCorridor       — sententia.corridors.india
  USCaymanIndia       — sententia.corridors.us_cayman_india
  GulfEU              — sententia.corridors.gulf_eu
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)

# ── Violation builder ─────────────────────────────────────────────────────────

def _v(code: str, rule: str, description: str, severity: str, source: str) -> dict:
    return {
        "code":        code,
        "rule":        rule,
        "description": description,
        "severity":    severity,
        "source":      source,
    }


# ══════════════════════════════════════════════════════════════════════════════
# BASE EVALUATOR
# ══════════════════════════════════════════════════════════════════════════════

class PolicyEvaluator(ABC):
    """Abstract base for all Python-native corridor policy evaluators."""

    @abstractmethod
    def evaluate(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Evaluate policy against input_data.
        Returns a dict with keys: violations, required_approvals, allow
        """
        ...

    @staticmethod
    def _upper(val: str | None) -> str:
        return (val or "").upper().replace(" ", "_").replace("-", "_")


# ══════════════════════════════════════════════════════════════════════════════
# INDIA CORRIDOR
# Rego source: policies/rego/india_corridor.rego
# Package:     sententia.corridors.india
# ══════════════════════════════════════════════════════════════════════════════

class IndiaCorridor(PolicyEvaluator):
    """
    Python mirror of india_corridor.rego

    Rules implemented:
      PN3_NO_PRIOR_APPROVAL          — BLOCKING
      PN3_UBO_LAND_BORDER            — BLOCKING
      PN3_APPROVAL_SCOPE_VERIFY      — WARNING
      PROHIBITED_SECTOR              — BLOCKING
      S9_INDIRECT_TRANSFER_RISK      — WARNING
      SINGAPORE_SPV_POEM_PPT_RISK    — WARNING
      required: FC-GPR, BEN-1, BEN-2, Form 3CT
    """

    LAND_BORDER_COUNTRIES = {
        "CHINA", "PAKISTAN", "BANGLADESH",
        "NEPAL", "MYANMAR", "BHUTAN", "AFGHANISTAN",
    }

    def _origin_is_land_border(self, data: dict) -> bool:
        return self._upper(data.get("origin_jurisdiction")) in self.LAND_BORDER_COUNTRIES

    def _ubo_chain_has_land_border(self, data: dict) -> bool:
        ubo_chain = data.get("ubo_chain") or []
        for ubo in ubo_chain:
            if (
                self._upper(ubo.get("nationality")) in self.LAND_BORDER_COUNTRIES
                and (ubo.get("ownership_pct") or 0) > 0
            ):
                return True
        return False

    def evaluate(self, data: dict[str, Any]) -> dict[str, Any]:
        violations: list[dict] = []
        required_approvals: list[str] = []

        origin = self._upper(data.get("origin_jurisdiction", ""))
        spv    = self._upper(data.get("spv_jurisdiction", "") or "")
        equity = data.get("equity_pct") or 0
        spv_india_pct = data.get("spv_india_asset_value_pct") or 0
        prior_approval = data.get("prior_govt_approval_obtained", False)
        is_prohibited  = data.get("is_prohibited_sector", False)
        is_land_border = self._origin_is_land_border(data)
        ubo_land_border = self._ubo_chain_has_land_border(data)

        # ── PN3: direct origin ─────────────────────────────────────────────────
        if is_land_border and not prior_approval:
            violations.append(_v(
                code="PN3_NO_PRIOR_APPROVAL",
                rule="Press Note 3 (2020 Series) — Para 3.1.1",
                description=(
                    f"FDI from {data.get('origin_jurisdiction')} — a land-border country — requires "
                    "prior Government Approval from DPIIT before any investment. The automatic route "
                    "is NOT available. Investment cannot proceed without CCEA/DPIIT approval."
                ),
                severity="blocking",
                source="Press Note 3 (2020 Series), DPIIT, Ministry of Commerce & Industry",
            ))
            required_approvals.append(
                "DPIIT Government Approval — file via FIFP portal (estimated timeline: 60 working days; "
                "CCEA review for amounts >INR 5,000 crore)"
            )

        # ── PN3: UBO look-through ─────────────────────────────────────────────
        elif not is_land_border and ubo_land_border and not prior_approval:
            violations.append(_v(
                code="PN3_UBO_LAND_BORDER",
                rule="Press Note 3 (2020 Series) — Beneficial Ownership Look-Through",
                description=(
                    "UBO chain contains individuals/entities with land-border country nationality. "
                    "Press Note 3 applies based on ultimate beneficial ownership. Government Approval required."
                ),
                severity="blocking",
                source="Press Note 3 (2020 Series); DPIIT FAQ on land-border UBO tracing",
            ))
            required_approvals.append(
                "DPIIT Government Approval — file via FIFP portal (PN3 UBO look-through applies)"
            )

        # ── PN3: approval obtained — scope verification ────────────────────────
        if is_land_border and prior_approval:
            violations.append(_v(
                code="PN3_APPROVAL_SCOPE_VERIFY",
                rule="Press Note 3 (2020) — Post-Approval Compliance",
                description=(
                    "Government Approval obtained. Verify that approval expressly covers: current sector, "
                    "investment amount, equity percentage, and entity structure. Any material deviation from "
                    "approved terms requires a fresh DPIIT application."
                ),
                severity="warning",
                source="Press Note 3 (2020 Series); FEMA Regulations",
            ))

        # ── Prohibited sector ──────────────────────────────────────────────────
        if is_prohibited:
            violations.append(_v(
                code="PROHIBITED_SECTOR",
                rule="Consolidated FDI Policy 2020 — Annex: Prohibited Sectors",
                description=(
                    f"Sector '{data.get('sector')}' is prohibited for FDI under the Consolidated FDI Policy (DPIIT). "
                    "No FDI is permitted in any form, regardless of approval route."
                ),
                severity="blocking",
                source="Consolidated FDI Policy 2020, DPIIT",
            ))

        # ── Section 9(1)(i) indirect transfer ─────────────────────────────────
        if spv_india_pct > 50:
            violations.append(_v(
                code="S9_INDIRECT_TRANSFER_RISK",
                rule="Section 9(1)(i) Explanation 5/6 — Income Tax Act 1961",
                description=(
                    f"SPV holds {spv_india_pct}% of its fair market value from Indian assets (statutory threshold: >50%). "
                    "On future exit via sale of SPV shares, the transfer will be deemed a transfer of Indian capital assets. "
                    "Indian capital gains tax will apply; Section 195 withholding obligations arise on the acquirer; "
                    "Form 3CT reporting within 90 days of transfer required."
                ),
                severity="warning",
                source="Section 9(1)(i) Explanation 5/6 — ITA 1961, Finance Act 2012/2015",
            ))
            required_approvals.append(
                "Form 3CT — Indirect Transfer Reporting to Indian Income Tax authority (within 90 days of transfer of SPV shares)"
            )

        # ── Singapore SPV — POEM / PPT risk ───────────────────────────────────
        if spv == "SINGAPORE":
            violations.append(_v(
                code="SINGAPORE_SPV_POEM_PPT_RISK",
                rule="POEM — Section 6(3)(ii) ITA 1961; PPT — MLI Article 7 / Singapore-India DTAA 2016 Protocol",
                description=(
                    "Singapore SPV must maintain genuine economic substance in Singapore to avoid: "
                    "(a) Indian POEM characterisation (Section 6(3)(ii)) — would treat SPV as India-resident, "
                    "negating DTAA benefits; and (b) PPT challenge denying DTAA benefits if a principal purpose "
                    "of the Singapore SPV is to access treaty benefits. "
                    "Minimum substance: local board meetings, Singapore-resident directors, local employees, "
                    "Singapore bank account with real cash flows."
                ),
                severity="warning",
                source="Section 6(3)(ii) ITA 1961 (POEM Rules 2017); MLI Article 7; Singapore-India DTAA 2016 Protocol",
            ))

        # ── Required approvals (always required) ──────────────────────────────
        required_approvals.append(
            "FC-GPR — Foreign Currency-Gross Provisional Return filed with RBI via FIRMS portal "
            "(within 30 days of allotment of shares)"
        )

        if equity >= 10:
            required_approvals.append(
                "Form BEN-1 — SBO Declaration by ultimate beneficial owner to Indian company "
                "(Companies Act §90; within 30 days)"
            )
            required_approvals.append(
                "Form BEN-2 — Return of SBO filed by Indian company with Registrar of Companies "
                "(within 30 days of receiving BEN-1)"
            )

        # ── Decision ──────────────────────────────────────────────────────────
        is_allowed = not any(v["severity"] == "blocking" for v in violations)

        return {
            "violations": violations,
            "required_approvals": list(dict.fromkeys(required_approvals)),  # deduplicate
            "allow": is_allowed,
        }


# ══════════════════════════════════════════════════════════════════════════════
# US → CAYMAN → INDIA CORRIDOR
# Rego source: policies/rego/us_cayman_india.rego
# Package:     sententia.corridors.us_cayman_india
# ══════════════════════════════════════════════════════════════════════════════

class USCaymanIndia(PolicyEvaluator):
    """
    Python mirror of us_cayman_india.rego

    Rules implemented:
      FATCA_NON_COMPLIANCE           — BLOCKING
      FATCA_STATUS_UNVERIFIED        — WARNING
      CAYMAN_SUBSTANCE_DEFICIENT     — WARNING
      PFIC_PASSIVE_ASSET_RISK        — WARNING
      S9_INDIRECT_TRANSFER_RISK      — WARNING
      PROHIBITED_SECTOR              — BLOCKING
      required: FC-GPR, BEN-1, FATCA, Form 3CT
    """

    def evaluate(self, data: dict[str, Any]) -> dict[str, Any]:
        violations: list[dict] = []
        required_approvals: list[str] = []

        equity             = data.get("equity_pct") or 0
        has_us_persons     = data.get("has_us_persons_in_fund", False)
        fatca_compliant    = data.get("fatca_compliant")     # None = unknown
        cayman_substance   = data.get("cayman_has_substance")  # None = unknown
        passive_asset_pct  = data.get("spv_passive_asset_pct") or 0
        spv_india_pct      = data.get("spv_india_asset_value_pct") or 0
        is_prohibited      = data.get("is_prohibited_sector", False)

        # NOTE: US is not a land-border country. PN3 does NOT apply.

        # ── FATCA: non-compliant ────────────────────────────────────────────────
        if has_us_persons and fatca_compliant is False:
            violations.append(_v(
                code="FATCA_NON_COMPLIANCE",
                rule="FATCA — IRC §1471-1474; FBAR — 31 USC §5314",
                description=(
                    "Fund contains US persons who are not FATCA-compliant. Foreign financial institutions "
                    "(FFIs) in the structure must be FATCA-registered or exempt. Failure to comply results "
                    "in 30% US withholding on withholdable payments."
                ),
                severity="blocking",
                source="Foreign Account Tax Compliance Act (FATCA), IRC §1471-1474",
            ))

        # ── FATCA: status unknown ─────────────────────────────────────────────
        elif has_us_persons and fatca_compliant is None:
            violations.append(_v(
                code="FATCA_STATUS_UNVERIFIED",
                rule="FATCA — IRC §1471-1474",
                description=(
                    "Fund contains US persons. FATCA compliance status is unverified. Confirm: "
                    "(a) US persons have provided Form W-9; (b) Cayman fund has registered as FFI with IRS "
                    "or qualifies for FATCA exemption; (c) PFIC annual elections considered."
                ),
                severity="warning",
                source="FATCA, IRC §1471-1474; IRS FATCA FFI Registration System",
            ))

        # ── Cayman substance ──────────────────────────────────────────────────
        if cayman_substance is False:
            violations.append(_v(
                code="CAYMAN_SUBSTANCE_DEFICIENT",
                rule="Cayman Islands Economic Substance Act 2019 (ESA)",
                description=(
                    "Cayman Islands SPV lacks adequate economic substance. Under the ESA, entities conducting "
                    "relevant activities must demonstrate: adequate employees/physical presence in Cayman, "
                    "core income-generating activities conducted in Cayman, directed and managed from Cayman. "
                    "Failure triggers reporting to the Cayman Tax Information Authority and penalties."
                ),
                severity="warning",
                source="Cayman Islands Economic Substance Act 2019; ESA Regulations 2018",
            ))

        # ── PFIC test ─────────────────────────────────────────────────────────
        if passive_asset_pct >= 50 and has_us_persons:
            violations.append(_v(
                code="PFIC_PASSIVE_ASSET_RISK",
                rule="IRC §1297 — Passive Foreign Investment Company",
                description=(
                    f"Cayman SPV has {passive_asset_pct}% passive assets (PFIC threshold: ≥50%). "
                    "If classified as a PFIC, US investors face punitive taxation on excess distributions "
                    "and dispositions (interest charge regime under IRC §1291) or must make QEF/mark-to-market "
                    "elections. Confirm active trade-or-business test or look-through rule applies."
                ),
                severity="warning",
                source="IRC §1297 (PFIC definition); IRC §1291-1298 (PFIC taxation)",
            ))

        # ── Section 9(1)(i) indirect transfer ─────────────────────────────────
        if spv_india_pct > 50:
            violations.append(_v(
                code="S9_INDIRECT_TRANSFER_RISK",
                rule="Section 9(1)(i) Explanation 5 — Income Tax Act 1961",
                description=(
                    f"Cayman SPV holds {spv_india_pct}% of value from Indian assets (>50% threshold). "
                    "On exit via transfer of Cayman SPV shares, Indian capital gains tax applies. "
                    "US investors face dual tax: Indian CGT + US federal CGT (foreign tax credit may be limited)."
                ),
                severity="warning",
                source="Section 9(1)(i) Explanation 5/6 — ITA 1961; IRC §901 (Foreign Tax Credit)",
            ))
            required_approvals.append(
                "Form 3CT — Indirect Transfer Reporting to Indian Income Tax authority (within 90 days of transfer)"
            )

        # ── Prohibited sector ──────────────────────────────────────────────────
        if is_prohibited:
            violations.append(_v(
                code="PROHIBITED_SECTOR",
                rule="Consolidated FDI Policy 2020 — Prohibited Sectors",
                description=(
                    f"Sector '{data.get('sector')}' is prohibited for FDI in India. "
                    "This restriction applies regardless of investor nationality or structure."
                ),
                severity="blocking",
                source="Consolidated FDI Policy 2020, DPIIT",
            ))

        # ── Required approvals ────────────────────────────────────────────────
        required_approvals.append(
            "FC-GPR — Foreign Currency-Gross Provisional Return filed with RBI via FIRMS portal "
            "(within 30 days of share allotment in India OpCo)"
        )
        if equity >= 10:
            required_approvals.append(
                "Form BEN-1 — SBO Declaration by US fund beneficial owner to Indian company "
                "(Companies Act §90, within 30 days)"
            )
        if has_us_persons:
            required_approvals.append(
                "FATCA compliance — Cayman fund must register as FFI with IRS (or verify exemption); "
                "US investors must file Form 8621 if PFIC election made; "
                "FBAR filing for US persons with Cayman account >USD 10,000"
            )

        is_allowed = not any(v["severity"] == "blocking" for v in violations)
        return {
            "violations": violations,
            "required_approvals": list(dict.fromkeys(required_approvals)),
            "allow": is_allowed,
        }


# ══════════════════════════════════════════════════════════════════════════════
# GULF → LUXEMBOURG → FRANCE CORRIDOR
# Rego source: policies/rego/gulf_eu.rego
# Package:     sententia.corridors.gulf_eu
# ══════════════════════════════════════════════════════════════════════════════

class GulfEU(PolicyEvaluator):
    """
    Python mirror of gulf_eu.rego

    Rules implemented:
      FRENCH_GOLDEN_POWERS_REQUIRED      — BLOCKING
      FRENCH_GOLDEN_POWERS_SECTOR_VERIFY — WARNING
      EU_FDI_SCREENING_REQUIRED          — BLOCKING
      EU_FDI_SCREENING_STATUS_UNKNOWN    — WARNING
      LUX_ATAD_SUBSTANCE_RISK            — WARNING
      PILLAR_TWO_BELOW_MINIMUM_RATE      — WARNING
      DAC6_MANDATORY_DISCLOSURE          — WARNING
      required: French IEF authorization, EU FDI Screening, Lux TP docs
    """

    GULF_STATES = {"SAUDI_ARABIA", "UAE", "QATAR", "KUWAIT", "BAHRAIN", "OMAN"}

    FRENCH_SENSITIVE_SECTORS = {
        "AEROSPACE", "DEFENSE", "DUAL_USE_TECHNOLOGY",
        "ENERGY", "TRANSPORT", "WATER", "TELECOMMUNICATIONS",
        "HEALTH", "ARTIFICIAL_INTELLIGENCE", "SEMICONDUCTORS",
        "MEDIA", "CRITICAL_INFRASTRUCTURE", "FINANCIAL_MARKETS",
    }

    def _sector_triggers_golden_powers(self, data: dict) -> bool:
        sector_upper = self._upper(data.get("sector", ""))
        return (
            sector_upper in self.FRENCH_SENSITIVE_SECTORS
            or data.get("target_sector_is_sensitive", False)
            or data.get("is_dual_use_technology", False)
        )

    def evaluate(self, data: dict[str, Any]) -> dict[str, Any]:
        violations: list[dict] = []
        required_approvals: list[str] = []

        target_is_france    = self._upper(data.get("target_jurisdiction", "")) == "FRANCE"
        spv_is_lux          = self._upper(data.get("spv_jurisdiction", "") or "") == "LUXEMBOURG"
        origin_is_gulf      = self._upper(data.get("origin_jurisdiction", "")) in self.GULF_STATES

        golden_powers_triggers = self._sector_triggers_golden_powers(data)
        golden_powers_notified = data.get("french_golden_powers_notified")  # None = unknown
        eu_screening_notified  = data.get("eu_fdi_screening_notified")      # None = unknown
        lux_substance          = data.get("luxembourg_has_substance")        # None = unknown
        lux_etr                = data.get("lux_effective_tax_rate_pct")
        equity                 = data.get("equity_pct") or 0

        # ── French Golden Powers: blocking ────────────────────────────────────
        if target_is_france and golden_powers_triggers and golden_powers_notified is False:
            violations.append(_v(
                code="FRENCH_GOLDEN_POWERS_REQUIRED",
                rule="Decree n°2019-1590 — Article R151-1 et seq., French Monetary and Financial Code",
                description=(
                    f"Acquisition of ≥{equity}% voting rights in a French company in sector "
                    f"'{data.get('sector')}' requires prior authorization from the French Ministry of Economy "
                    "under the Golden Powers (IEF) regime. Closing cannot occur until authorization is granted. "
                    "Timeline: 30 business days for initial review; up to 45 days if investigation opened."
                ),
                severity="blocking",
                source="Decree n°2019-1590 (21 November 2019); Articles R151-1 to R153-11 of the Monetary and Financial Code",
            ))
            required_approvals.append(
                "French IEF (Investissements Étrangers en France) Authorization — "
                "file with Direction générale du Trésor before signing/closing (Decree n°2019-1590)"
            )

        # ── French Golden Powers: sector unclear ──────────────────────────────
        elif target_is_france and not golden_powers_triggers:
            violations.append(_v(
                code="FRENCH_GOLDEN_POWERS_SECTOR_VERIFY",
                rule="Decree n°2019-1590 — Sector Scope Assessment",
                description=(
                    f"Sector '{data.get('sector')}' does not obviously trigger French Golden Powers. "
                    "However, the French Government has broad discretion to characterise activities as strategic. "
                    "Confirm with French legal counsel, particularly for AI, semiconductors, biotech, or "
                    "critical supplier designation."
                ),
                severity="warning",
                source="Decree n°2019-1590; Arrêté of 31 December 2019 (list of strategic sectors)",
            ))

        # ── EU FDI Screening: blocking ─────────────────────────────────────────
        if target_is_france and eu_screening_notified is False:
            violations.append(_v(
                code="EU_FDI_SCREENING_REQUIRED",
                rule="Regulation (EU) 2019/452 — EU FDI Screening Framework",
                description=(
                    "France must notify the European Commission and other EU Member States of this FDI "
                    "transaction under the EU FDI Cooperation Mechanism. Investment in critical infrastructure, "
                    "technology, or sensitive supply chains triggers scrutiny."
                ),
                severity="blocking",
                source="Regulation (EU) 2019/452, Articles 6-8",
            ))
            required_approvals.append(
                "EU FDI Screening — French authority to notify European Commission and EU Member States "
                "under Article 6 of Regulation (EU) 2019/452"
            )

        # ── EU FDI Screening: status unknown ──────────────────────────────────
        elif target_is_france and eu_screening_notified is None:
            violations.append(_v(
                code="EU_FDI_SCREENING_STATUS_UNKNOWN",
                rule="Regulation (EU) 2019/452 — Article 9",
                description=(
                    "EU FDI Screening notification status not confirmed. Verify with French authorities "
                    "whether this transaction falls within the EU Screening Cooperation Mechanism scope."
                ),
                severity="warning",
                source="Regulation (EU) 2019/452",
            ))

        # ── Luxembourg ATAD substance ──────────────────────────────────────────
        if spv_is_lux and lux_substance is False:
            violations.append(_v(
                code="LUX_ATAD_SUBSTANCE_RISK",
                rule="EU ATAD Directive 2016/1164 (Articles 6, 7) — transposed into Luxembourg law",
                description=(
                    "Luxembourg holding company lacks economic substance. Risks: "
                    "(a) French/German GAAR may disregard the Luxembourg entity; "
                    "(b) ATAD Article 6 (GAAR) — Luxembourg itself may disregard the entity; "
                    "(c) ATAD Article 7 (CFC) — passive income in Luxembourg may be attributed to Gulf parent. "
                    "Minimum substance: qualified directors, local management, physical office."
                ),
                severity="warning",
                source="ATAD Directive 2016/1164; Luxembourg Law of 21 December 2021 (ATAD transposition)",
            ))

        # ── Pillar Two: below 15% minimum ─────────────────────────────────────
        if spv_is_lux and lux_etr is not None and lux_etr < 15:
            violations.append(_v(
                code="PILLAR_TWO_BELOW_MINIMUM_RATE",
                rule="OECD Pillar Two — Global Minimum Tax (GloBE Rules)",
                description=(
                    f"Luxembourg effective tax rate of {lux_etr}% is below the 15% global minimum "
                    "under OECD Pillar Two (applies to groups with >EUR 750M revenue from 2024). "
                    "Top-up taxes (IIR or UTPR) will apply in the UPE jurisdiction. "
                    "Restructuring or substance enhancement in Luxembourg may be required."
                ),
                severity="warning",
                source="OECD GloBE Model Rules 2021; EU Minimum Tax Directive 2022/2523; Luxembourg Pillar Two Law 2023",
            ))

        # ── DAC6 mandatory disclosure ──────────────────────────────────────────
        if origin_is_gulf and spv_is_lux and target_is_france:
            violations.append(_v(
                code="DAC6_MANDATORY_DISCLOSURE",
                rule="EU DAC6 Directive 2018/822 — Mandatory Disclosure Rules",
                description=(
                    "This tri-party arrangement (Gulf → Luxembourg → France) may constitute a reportable "
                    "arrangement under EU DAC6 if it involves confidentiality clauses, standardized schemes, "
                    "or specific tax benefit hallmarks (e.g., preferential Luxembourg regime). Luxembourg "
                    "intermediaries must report within 30 days of arrangement being available or implemented."
                ),
                severity="warning",
                source="Council Directive 2018/822/EU (DAC6); Luxembourg Law of 25 March 2020 (DAC6 transposition)",
            ))

        # ── Required approvals (always) ────────────────────────────────────────
        if target_is_france:
            required_approvals.append(
                "French share transfer registration — registered transfer of French company shares; "
                "filing with Centre des Formalités des Entreprises post-closing"
            )
        if spv_is_lux:
            required_approvals.append(
                "Luxembourg transfer pricing documentation — arm's-length pricing documentation "
                "for intra-group transactions (Luxembourg Transfer Pricing Law 2017)"
            )

        is_allowed = not any(v["severity"] == "blocking" for v in violations)
        return {
            "violations": violations,
            "required_approvals": list(dict.fromkeys(required_approvals)),
            "allow": is_allowed,
        }


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRY + FACTORY
# ══════════════════════════════════════════════════════════════════════════════

_EVALUATORS: dict[str, type[PolicyEvaluator]] = {
    "sententia.corridors.india":           IndiaCorridor,
    "sententia.corridors.us_cayman_india": USCaymanIndia,
    "sententia.corridors.gulf_eu":         GulfEU,
}


def get_evaluator(policy_package: str) -> PolicyEvaluator | None:
    """
    Return the Python-native evaluator for the given OPA policy package name.
    Returns None if no evaluator is registered for this package.
    """
    cls = _EVALUATORS.get(policy_package)
    if cls is None:
        logger.warning(f"No Python-native evaluator for policy package: {policy_package}")
        return None
    return cls()


def list_registered_packages() -> list[str]:
    """Return all registered policy package names."""
    return list(_EVALUATORS.keys())
