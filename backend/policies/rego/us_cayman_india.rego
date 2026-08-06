# sententia/corridors/us_cayman_india — Rego Policy
# Covers: FATCA, Cayman Islands Economic Substance, FEMA FC-GPR, PFIC, Section 9(1)(i)
# OPA package: sententia.corridors.us_cayman_india
#
# Expected input shape:
# {
#   "origin_jurisdiction":            "UNITED_STATES",
#   "target_jurisdiction":            "INDIA",
#   "spv_jurisdiction":               "CAYMAN_ISLANDS",
#   "sector":                         "Technology",
#   "investment_amount_usd":          20000000,
#   "equity_pct":                     25.0,
#   "has_us_persons_in_fund":         true,
#   "fatca_compliant":                false,        # null = unknown
#   "cayman_has_substance":           true,         # null = unknown
#   "spv_india_asset_value_pct":      80.0,
#   "spv_passive_asset_pct":          85.0,         # for PFIC test
#   "is_prohibited_sector":           false
# }

package sententia.corridors.us_cayman_india

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# ─── Helpers ─────────────────────────────────────────────────────────────────────

us_persons_in_fund if {
    input.has_us_persons_in_fund == true
}

cayman_lacks_substance if {
    input.cayman_has_substance == false
}

fatca_non_compliant if {
    input.fatca_compliant == false
}

# PFIC test: foreign corporation is a PFIC if ≥75% of gross income is passive
# OR ≥50% of assets (by value) are passive assets (IRC §1297)
pfic_passive_income_test if {
    input.spv_passive_asset_pct >= 50
}

# Section 9(1)(i) indirect transfer: SPV value >50% from India assets
spv_predominantly_india_assets if {
    input.spv_india_asset_value_pct > 50
}

sbo_threshold_met if {
    input.equity_pct >= 10
}

# ─── VIOLATIONS ──────────────────────────────────────────────────────────────────

# NOTE: US is NOT a land-border country. Press Note 3 does NOT apply.
# No Government Approval required for US-origin FDI under PN3.

# BLOCKING: FATCA non-compliance for US persons in fund
violations contains v if {
    us_persons_in_fund
    fatca_non_compliant
    v := {
        "code":        "FATCA_NON_COMPLIANCE",
        "rule":        "FATCA — IRC §1471-1474; FBAR — 31 USC §5314",
        "description": "Fund contains US persons who are not FATCA-compliant. US persons investing in foreign financial accounts/entities must comply with FATCA reporting requirements. Foreign financial institutions (FFIs) in the structure must be FATCA-registered or exempt. Failure to comply results in 30% US withholding on withholdable payments.",
        "severity":    "blocking",
        "source":      "Foreign Account Tax Compliance Act (FATCA), IRC §1471-1474; IRS Publication 5118"
    }
}

# WARNING: FATCA — US persons present, compliance status unknown
violations contains v if {
    us_persons_in_fund
    not input.fatca_compliant
    not input.fatca_compliant == false
    v := {
        "code":        "FATCA_STATUS_UNVERIFIED",
        "rule":        "FATCA — IRC §1471-1474",
        "description": "Fund contains US persons. FATCA compliance status is unverified. Confirm: (a) all US persons have provided Form W-9; (b) the Cayman fund has registered as an FFI with IRS or qualifies for a FATCA exemption category; (c) PFIC annual elections have been considered for US fund investors.",
        "severity":    "warning",
        "source":      "FATCA, IRC §1471-1474; IRS FATCA FFI Registration System"
    }
}

# WARNING: Cayman Islands Economic Substance — no genuine substance
violations contains v if {
    cayman_lacks_substance
    v := {
        "code":        "CAYMAN_SUBSTANCE_DEFICIENT",
        "rule":        "Cayman Islands Economic Substance Act 2019 (ESA)",
        "description": "Cayman Islands SPV lacks adequate economic substance in the Cayman Islands. Under the ESA, entities conducting 'relevant activities' (holding company, fund management) must demonstrate: adequate employees/physical presence in Cayman, core income-generating activities conducted in Cayman, directed and managed from Cayman. Failure may trigger reporting to the Cayman Tax Information Authority and penalties.",
        "severity":    "warning",
        "source":      "Cayman Islands Economic Substance Act 2019; ESA Regulations 2018"
    }
}

# WARNING: PFIC risk for US investors — passive asset concentration
violations contains v if {
    pfic_passive_income_test
    us_persons_in_fund
    v := {
        "code":        "PFIC_PASSIVE_ASSET_RISK",
        "rule":        "IRC §1297 — Passive Foreign Investment Company",
        "description": sprintf(
            "Cayman SPV has %v%% passive assets (PFIC threshold: ≥50%%). If classified as a PFIC, US investors face punitive taxation on excess distributions and dispositions (interest charge regime under IRC §1291) or must make QEF/mark-to-market elections. Cayman venture/PE funds commonly rely on the 'active trade or business' test or the 'look-through' rule for subsidiaries to avoid PFIC status.",
            [input.spv_passive_asset_pct]
        ),
        "severity":    "warning",
        "source":      "IRC §1297 (PFIC definition); IRC §1291-1298 (PFIC taxation)"
    }
}

# WARNING: Section 9(1)(i) indirect transfer on exit
violations contains v if {
    spv_predominantly_india_assets
    v := {
        "code":        "S9_INDIRECT_TRANSFER_RISK",
        "rule":        "Section 9(1)(i) Explanation 5 — Income Tax Act 1961",
        "description": sprintf(
            "Cayman SPV holds %v%% of value from Indian assets (>50%% threshold). On exit via transfer of Cayman SPV shares, Indian capital gains tax applies. US investors face a dual tax burden: Indian capital gains tax AND US federal capital gains tax (with potential foreign tax credit, but credit may be limited).",
            [input.spv_india_asset_value_pct]
        ),
        "severity":    "warning",
        "source":      "Section 9(1)(i) Explanation 5/6 — ITA 1961; IRC §901 (Foreign Tax Credit)"
    }
}

# WARNING: Prohibited sector
violations contains v if {
    input.is_prohibited_sector
    v := {
        "code":        "PROHIBITED_SECTOR",
        "rule":        "Consolidated FDI Policy 2020 — Prohibited Sectors",
        "description": sprintf(
            "Sector '%v' is prohibited for FDI in India. This restriction applies regardless of investor nationality or structure.",
            [input.sector]
        ),
        "severity":    "blocking",
        "source":      "Consolidated FDI Policy 2020, DPIIT"
    }
}

# ─── REQUIRED APPROVALS AND FILINGS ──────────────────────────────────────────────

required_approvals contains a if {
    a := "FC-GPR — Foreign Currency-Gross Provisional Return filed with RBI via FIRMS portal (within 30 days of share allotment in India OpCo)"
}

required_approvals contains a if {
    sbo_threshold_met
    a := "Form BEN-1 — SBO Declaration by US fund beneficial owner to Indian company (Companies Act §90, within 30 days)"
}

required_approvals contains a if {
    us_persons_in_fund
    a := "FATCA compliance — Cayman fund must register as FFI with IRS (or verify exemption); US investors must file Form 8621 if PFIC election made; FBAR filing for US persons with Cayman account >USD 10,000"
}

required_approvals contains a if {
    spv_predominantly_india_assets
    a := "Form 3CT — Indirect Transfer Reporting to Indian Income Tax authority (within 90 days of transfer of Cayman SPV shares)"
}

# ─── OVERALL DECISION ─────────────────────────────────────────────────────────────

default allow := false

allow if {
    every v in violations {
        v.severity != "blocking"
    }
}
