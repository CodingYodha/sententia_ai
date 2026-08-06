# sententia/corridors/india — Rego Policy
# Covers: Press Note 3 (2020), Section 9(1)(i), Companies Act §90 SBO
# OPA package: sententia.corridors.india
#
# Expected input shape:
# {
#   "origin_jurisdiction":            "CHINA",
#   "target_jurisdiction":            "INDIA",
#   "spv_jurisdiction":               "SINGAPORE",     # optional
#   "sector":                         "Technology",
#   "investment_amount_usd":          50000000,
#   "equity_pct":                     49.0,
#   "prior_govt_approval_obtained":   false,
#   "is_prohibited_sector":           false,
#   "spv_india_asset_value_pct":      75.0,            # % of SPV FMV from India assets
#   "ubo_chain": [                                      # optional
#     {"nationality": "CHINA", "ownership_pct": 100}
#   ]
# }

package sententia.corridors.india

import future.keywords.contains
import future.keywords.if
import future.keywords.in

# ─── Land-border country set — Press Note 3 (2020) / Press Note 2 (2026) ───────
# Countries sharing a land border with India from which ALL FDI requires
# prior Government Approval from DPIIT (automatic route NOT available).

land_border_countries := {
    "CHINA", "PAKISTAN", "BANGLADESH",
    "NEPAL", "MYANMAR", "BHUTAN", "AFGHANISTAN"
}

# ─── Helpers ─────────────────────────────────────────────────────────────────────

origin_is_land_border if {
    upper(input.origin_jurisdiction) in land_border_countries
}

# UBO chain check: any UBO with land-border nationality and >0% ownership
ubo_chain_has_land_border if {
    some ubo in input.ubo_chain
    upper(ubo.nationality) in land_border_countries
    ubo.ownership_pct > 0
}

# SPV value test: >50% of SPV FMV attributable to Indian assets
spv_predominantly_india_assets if {
    input.spv_india_asset_value_pct > 50
}

# SBO threshold: individual beneficial interest ≥10% of Indian company
sbo_threshold_met if {
    input.equity_pct >= 10
}

# ─── VIOLATIONS ──────────────────────────────────────────────────────────────────

# BLOCKING: PN3 — land-border origin without prior Government Approval
violations contains v if {
    origin_is_land_border
    not input.prior_govt_approval_obtained
    v := {
        "code":        "PN3_NO_PRIOR_APPROVAL",
        "rule":        "Press Note 3 (2020 Series) — Para 3.1.1",
        "description": sprintf(
            "FDI from %v — a land-border country — requires prior Government Approval from DPIIT before any investment. The automatic route is NOT available. Investment cannot proceed without CCEA/DPIIT approval.",
            [input.origin_jurisdiction]
        ),
        "severity":    "blocking",
        "source":      "Press Note 3 (2020 Series), DPIIT, Ministry of Commerce & Industry"
    }
}

# BLOCKING: PN3 applies even when UBO (not direct origin) is land-border
violations contains v if {
    not origin_is_land_border
    ubo_chain_has_land_border
    not input.prior_govt_approval_obtained
    v := {
        "code":        "PN3_UBO_LAND_BORDER",
        "rule":        "Press Note 3 (2020 Series) — Beneficial Ownership Look-Through",
        "description": "UBO chain contains individuals/entities with land-border country nationality. Press Note 3 applies based on ultimate beneficial ownership, not only direct investor nationality. Government Approval is required.",
        "severity":    "blocking",
        "source":      "Press Note 3 (2020 Series); DPIIT FAQ on land-border UBO tracing"
    }
}

# WARNING: PN3 compliance — approval obtained but scope must be verified
violations contains v if {
    origin_is_land_border
    input.prior_govt_approval_obtained
    v := {
        "code":        "PN3_APPROVAL_SCOPE_VERIFY",
        "rule":        "Press Note 3 (2020) — Post-Approval Compliance",
        "description": "Government Approval obtained. Verify that approval expressly covers: current sector, investment amount, equity percentage, and entity structure. Any material deviation from approved terms requires a fresh DPIIT application.",
        "severity":    "warning",
        "source":      "Press Note 3 (2020 Series); FEMA Regulations"
    }
}

# BLOCKING: Prohibited sector — no FDI permissible
violations contains v if {
    input.is_prohibited_sector
    v := {
        "code":        "PROHIBITED_SECTOR",
        "rule":        "Consolidated FDI Policy 2020 — Annex: Prohibited Sectors",
        "description": sprintf(
            "Sector '%v' is prohibited for FDI under the Consolidated FDI Policy (DPIIT). No FDI is permitted in any form, regardless of approval route. Examples of prohibited sectors: lottery, gambling, chit funds, Nidhi companies, real estate (agricultural land).",
            [input.sector]
        ),
        "severity":    "blocking",
        "source":      "Consolidated FDI Policy 2020, DPIIT"
    }
}

# WARNING: Section 9(1)(i) Explanation 5 — indirect transfer risk on exit
violations contains v if {
    spv_predominantly_india_assets
    v := {
        "code":        "S9_INDIRECT_TRANSFER_RISK",
        "rule":        "Section 9(1)(i) Explanation 5/6 — Income Tax Act 1961",
        "description": sprintf(
            "SPV holds %v%% of its fair market value from Indian assets (statutory threshold: >50%%). On future exit via sale of SPV shares, the transfer will be deemed a transfer of Indian capital assets. Indian capital gains tax will apply; Section 195 withholding (TDS) obligations arise on the acquirer; Form 3CT reporting within 90 days of transfer required.",
            [input.spv_india_asset_value_pct]
        ),
        "severity":    "warning",
        "source":      "Section 9(1)(i) Explanation 5/6 — ITA 1961, inserted by Finance Act 2012 and amended by Finance Act 2015"
    }
}

# WARNING: Singapore SPV POEM/PPT risk (if SPV jurisdiction is Singapore)
violations contains v if {
    upper(input.spv_jurisdiction) == "SINGAPORE"
    v := {
        "code":        "SINGAPORE_SPV_POEM_PPT_RISK",
        "rule":        "POEM — Section 6(3)(ii) ITA 1961; PPT — MLI Article 7 / Singapore-India DTAA 2016 Protocol",
        "description": "Singapore SPV must maintain genuine economic substance in Singapore to avoid: (a) Indian POEM characterisation (treated as India-resident, negating DTAA benefits) and (b) PPT challenge denying DTAA benefits if a principal purpose of the Singapore SPV is to access treaty benefits. Minimum requirements: local board meetings, Singapore-resident directors exercising genuine decision-making, local employees, Singapore bank account with real cash flows.",
        "severity":    "warning",
        "source":      "Section 6(3)(ii) ITA 1961 (POEM Rules 2017); MLI Article 7 (PPT); Singapore-India DTAA 2016 Protocol"
    }
}

# ─── REQUIRED APPROVALS AND FILINGS ──────────────────────────────────────────────

required_approvals contains a if {
    origin_is_land_border
    not input.prior_govt_approval_obtained
    a := "DPIIT Government Approval — file via FIFP portal (estimated timeline: 60 working days; refer to Cabinet Committee on Economic Affairs for amounts >INR 5,000 crore)"
}

required_approvals contains a if {
    sbo_threshold_met
    a := "Form BEN-1 — SBO Declaration by ultimate beneficial owner to Indian company (Companies Act §90; within 30 days of triggering 10%+ threshold)"
}

required_approvals contains a if {
    sbo_threshold_met
    a := "Form BEN-2 — Return of SBO filed by Indian company with Registrar of Companies (within 30 days of receiving BEN-1 from SBO)"
}

required_approvals contains a if {
    a := "FC-GPR — Foreign Currency-Gross Provisional Return filed with RBI via FIRMS portal (within 30 days of allotment of shares)"
}

required_approvals contains a if {
    spv_predominantly_india_assets
    a := "Form 3CT — Indirect Transfer Reporting by non-resident transferor to Income Tax authority (within 90 days of transfer)"
}

# ─── OVERALL DECISION ─────────────────────────────────────────────────────────────

default allow := false

allow if {
    # No blocking violations
    every v in violations {
        v.severity != "blocking"
    }
}
