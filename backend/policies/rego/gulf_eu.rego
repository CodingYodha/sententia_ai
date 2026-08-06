# sententia/corridors/gulf_eu — Rego Policy
# Covers: French Golden Powers (Decree 2019-1590), EU FDI Screening Regulation (EU) 2019/452,
#         Luxembourg ATAD substance, OECD Pillar Two (Global Minimum Tax), EU DAC6
# OPA package: sententia.corridors.gulf_eu
#
# Expected input shape:
# {
#   "origin_jurisdiction":            "SAUDI_ARABIA",
#   "target_jurisdiction":            "FRANCE",
#   "spv_jurisdiction":               "LUXEMBOURG",
#   "sector":                         "Aerospace",
#   "investment_amount_usd":          500000000,
#   "equity_pct":                     35.0,
#   "target_sector_is_sensitive":     true,
#   "french_golden_powers_notified":  false,    # null = unknown
#   "eu_fdi_screening_notified":      false,    # null = unknown
#   "luxembourg_has_substance":       false,    # null = unknown
#   "lux_effective_tax_rate_pct":     9.0,      # % effective tax rate
#   "is_dual_use_technology":         false
# }

package sententia.corridors.gulf_eu

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# ─── Sensitive sectors triggering French Golden Powers ────────────────────────────
# Decree n°2019-1590 (21 November 2019) extended scope of screening

french_sensitive_sectors := {
    "AEROSPACE", "DEFENSE", "DUAL_USE_TECHNOLOGY",
    "ENERGY", "TRANSPORT", "WATER", "TELECOMMUNICATIONS",
    "HEALTH", "ARTIFICIAL_INTELLIGENCE", "SEMICONDUCTORS",
    "MEDIA", "CRITICAL_INFRASTRUCTURE", "FINANCIAL_MARKETS"
}

# ─── Gulf state sovereign wealth fund origins ─────────────────────────────────────
gulf_states := {
    "SAUDI_ARABIA", "UAE", "QATAR",
    "KUWAIT", "BAHRAIN", "OMAN"
}

# ─── Helpers ─────────────────────────────────────────────────────────────────────

target_is_france if {
    upper(input.target_jurisdiction) == "FRANCE"
}

origin_is_gulf if {
    upper(input.origin_jurisdiction) in gulf_states
}

sector_triggers_golden_powers if {
    upper(input.sector) in french_sensitive_sectors
}

sector_triggers_golden_powers if {
    input.target_sector_is_sensitive == true
}

luxembourg_lacks_substance if {
    input.luxembourg_has_substance == false
}

pillar_two_below_minimum if {
    input.lux_effective_tax_rate_pct < 15
}

# ─── VIOLATIONS ──────────────────────────────────────────────────────────────────

# BLOCKING: French Golden Powers — sensitive sector, no prior notification
violations contains v if {
    target_is_france
    sector_triggers_golden_powers
    input.french_golden_powers_notified == false
    v := {
        "code":        "FRENCH_GOLDEN_POWERS_REQUIRED",
        "rule":        "Decree n°2019-1590 — Article R151-1 et seq., French Monetary and Financial Code",
        "description": sprintf(
            "Acquisition of ≥%v%% of voting rights in a French company in sector '%v' requires prior authorization from the French Ministry of Economy under the 'Golden Powers' (investissements étrangers en France — IEF) regime. Closing cannot occur until authorization is granted. Timeline: 30 business days for initial review; up to 45 days if investigation opened.",
            [input.equity_pct, input.sector]
        ),
        "severity":    "blocking",
        "source":      "Decree n°2019-1590 (21 November 2019); Articles R151-1 to R153-11 of the Monetary and Financial Code"
    }
}

# WARNING: French Golden Powers — sector unclear, requires legal confirmation
violations contains v if {
    target_is_france
    not sector_triggers_golden_powers
    not input.target_sector_is_sensitive
    v := {
        "code":        "FRENCH_GOLDEN_POWERS_SECTOR_VERIFY",
        "rule":        "Decree n°2019-1590 — Sector Scope Assessment",
        "description": sprintf(
            "Sector '%v' does not obviously trigger French Golden Powers under the 2019 Decree. However, the French Government has broad discretion to characterise activities as 'strategic'. Confirm with French legal counsel whether any activity of the target company touches a listed strategic sector — particularly AI, semiconductors, biotech, or critical supplier designation.",
            [input.sector]
        ),
        "severity":    "warning",
        "source":      "Decree n°2019-1590; Arrêté of 31 December 2019 (list of strategic sectors)"
    }
}

# BLOCKING: EU FDI Screening — cross-EU notification not completed
violations contains v if {
    target_is_france
    input.eu_fdi_screening_notified == false
    v := {
        "code":        "EU_FDI_SCREENING_REQUIRED",
        "rule":        "Regulation (EU) 2019/452 — EU FDI Screening Framework",
        "description": "France must notify the European Commission and other EU Member States of this FDI transaction under the EU FDI Cooperation Mechanism. Timeline: French authority initiates notification within 5 working days; Commission/Member States may comment within 35 calendar days; Commission may issue opinion within 25 additional days. Investment in critical infrastructure, technology, or sensitive supply chains triggers most scrutiny.",
        "severity":    "blocking",
        "source":      "Regulation (EU) 2019/452, Articles 6-8; European Commission FDI Screening"
    }
}

# WARNING: EU FDI Screening status unknown
violations contains v if {
    target_is_france
    not input.eu_fdi_screening_notified
    not input.eu_fdi_screening_notified == false
    v := {
        "code":        "EU_FDI_SCREENING_STATUS_UNKNOWN",
        "rule":        "Regulation (EU) 2019/452 — Article 9",
        "description": "EU FDI Screening notification status not confirmed. Verify with French authorities whether this transaction falls within the EU Screening Cooperation Mechanism scope and whether a formal notification has been or must be submitted.",
        "severity":    "warning",
        "source":      "Regulation (EU) 2019/452"
    }
}

# WARNING: Luxembourg ATAD — entity lacks economic substance (EU GAAR/ATAD risk)
violations contains v if {
    upper(input.spv_jurisdiction) == "LUXEMBOURG"
    luxembourg_lacks_substance
    v := {
        "code":        "LUX_ATAD_SUBSTANCE_RISK",
        "rule":        "EU ATAD Directive 2016/1164 (Articles 6, 7) — transposed into Luxembourg law",
        "description": "Luxembourg holding company (SPV) lacks economic substance in Luxembourg. Risks: (a) French and German GAAR may disregard the Luxembourg entity and attribute income directly to Gulf origin; (b) ATAD Article 6 (GAAR) — Luxembourg itself may disregard the entity if arranged primarily for tax avoidance; (c) ATAD Article 7 (CFC rules) — passive income in Luxembourg SPV may be attributed to Gulf parent. Minimum substance: qualified directors, local management decisions, physical office, relevant employees.",
        "severity":    "warning",
        "source":      "ATAD Directive 2016/1164; Luxembourg Law of 21 December 2021 (ATAD transposition); French CGI Article 209B (CFC)"
    }
}

# WARNING: OECD Pillar Two — Luxembourg effective tax rate below 15% minimum
violations contains v if {
    upper(input.spv_jurisdiction) == "LUXEMBOURG"
    pillar_two_below_minimum
    v := {
        "code":        "PILLAR_TWO_BELOW_MINIMUM_RATE",
        "rule":        "OECD Pillar Two — Global Minimum Tax (GloBE Rules)",
        "description": sprintf(
            "Luxembourg effective tax rate of %v%% is below the 15%% global minimum under OECD Pillar Two (in force for groups with >EUR 750M revenue from 2024). If the Gulf parent's ultimate parent entity (UPE) or intermediate parent is in a Pillar Two participating jurisdiction, top-up taxes (Income Inclusion Rule or Undertaxed Profits Rule) will apply. Restructuring or substance enhancement in Luxembourg may be required.",
            [input.lux_effective_tax_rate_pct]
        ),
        "severity":    "warning",
        "source":      "OECD GloBE Model Rules 2021; EU Minimum Tax Directive 2022/2523; Luxembourg Pillar Two Law 2023"
    }
}

# WARNING: DAC6 mandatory disclosure — cross-border arrangement may be reportable
violations contains v if {
    origin_is_gulf
    upper(input.spv_jurisdiction) == "LUXEMBOURG"
    target_is_france
    v := {
        "code":        "DAC6_MANDATORY_DISCLOSURE",
        "rule":        "EU DAC6 Directive 2018/822 — Mandatory Disclosure Rules",
        "description": "This tri-party cross-border arrangement (Gulf → Luxembourg → France) may constitute a reportable arrangement under EU DAC6 if it involves: (a) use of a confidentiality clause, (b) standardized scheme, (c) specific tax benefit hallmarks (e.g., use of preferential Luxembourg regime), or (d) transfer pricing structure. Luxembourg intermediaries (law firms, tax advisers, banks) must report within 30 days of the arrangement being available, implemented, or ready for implementation.",
        "severity":    "warning",
        "source":      "Council Directive 2018/822/EU (DAC6); Luxembourg Law of 25 March 2020 (DAC6 transposition)"
    }
}

# ─── REQUIRED APPROVALS AND FILINGS ──────────────────────────────────────────────

required_approvals contains a if {
    target_is_france
    sector_triggers_golden_powers
    input.french_golden_powers_notified == false
    a := "French IEF (Investissements Étrangers en France) Authorization — file with Direction générale du Trésor before signing/closing (Decree n°2019-1590)"
}

required_approvals contains a if {
    target_is_france
    a := "EU FDI Screening — French authority to notify European Commission and EU Member States under Article 6 of Regulation (EU) 2019/452"
}

required_approvals contains a if {
    upper(input.spv_jurisdiction) == "LUXEMBOURG"
    a := "Luxembourg transfer pricing documentation — Luxembourg holding company must maintain arm's-length pricing documentation for intra-group transactions (Luxembourg Transfer Pricing Law 2017)"
}

required_approvals contains a if {
    target_is_france
    a := "French share transfer registration — notarized or registered transfer of French company shares; filing with Centre des Formalités des Entreprises (CFE) post-closing"
}

# ─── OVERALL DECISION ─────────────────────────────────────────────────────────────

default allow := false

allow if {
    every v in violations {
        v.severity != "blocking"
    }
}
