

# Decorative background graphic of interlocking circlessententia.ai Transactional Thinking, Done Right.

# Product Requirements Document

**CONFIDENTIAL PROPERTY, DO NOT REPRODUCE.**

The AI Legal Model for Cross-Border Fund Investment Structuring and Asset Management Advisory

|                         |                     |
|-------------------------|---------------------|
| <b>Document Status:</b> | FINAL               |
| <b>Prepared by:</b>     | sententia.ai        |
| <b>Date:</b>            | 11/05/2026          |
| <b>Classification:</b>  | <b>Confidential</b> |

![Decorative footer graphic with colorful abstract patterns](7e91b03571ba48fd413a01b934c59662_img.jpg)

opinion. thought. judgement.

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

---

## Table of Contents ---

## 1. Executive Summary

## 2. Problem Statement

## 3. Market Opportunity & Why Now

*3.1 Pillar One — Record Deal Activity, With Rising Regulatory Overhead*

*3.2 Pillar Two — Legal AI Adoption Has Crossed From Experimentation Into Infrastructure*

*3.3 Structuring and Research Is the Largest, Fastest-Growing Segment*

*3.4 What This Means for Sententia.ai*

## 4. Product Vision & Goals

## 5. Target Users & Personas

## 6. Illustrative Use Case

## 7. Scope

## 8. Functional Requirements

*8.1 Scenario Intake*

*8.2 Legal Processing Layer*

*8.3 Structuring Generation*

*8.4 Compliance Validation Layer*

*8.5 Visualization Layer*

*8.6 Expert Review & Output Delivery*

*8.7 Administration & Access Control*

## 9. Non-Functional Requirements

## 10. System Architecture Overview

## 11. Data Sources & Data Strategy

## 12. Expert Validation Process

## 13. Competitive Landscape

## 14. Success Metrics / KPIs

## 15. Roadmap

## 16. Risks & Mitigations

## 17. Glossary

---

Confidential — Page 2 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 1. Executive Summary ---

Cross-border fund and asset structuring sits at the intersection of overlapping, frequently amended regulatory regimes, securities law, foreign-exchange control, tax treaties, sectoral investment caps, and reporting obligations that differ by jurisdiction and change without warning. A single investment routed from, say, a U.S. fund into an Indian operating company by way of a Singapore or Mauritius holding vehicle can implicate a dozen or more distinct statutory frameworks at once — FEMA, the Consolidated FDI Policy, RBI and SEBI regulations, FCRA, U.S. securities and tax-reporting rules, and the treaty provisions governing each leg of the structure. Today, resolving that complexity is almost entirely a manual, human research exercise: associates and partners read statutes and regulatory guidance, search for comparable precedent, cross-check treaty positions, and synthesize all of it into a structuring memo, often taking days of senior practitioner time per transaction, before diligence on the specific deal facts even begins.

The most time-intensive part of that process is due diligence: verifying that a proposed structure holds up against the actual facts of a specific client, investor, and target & their corporate documents, capitalization tables, prior filings, beneficial-ownership chains, existing agreements, and any jurisdiction-specific disclosures. Under the current workflow, a lawyer must manually read every uploaded document, cross-reference it against the applicable regulatory regime in each relevant jurisdiction, and manually verify that nothing in the paperwork conflicts with, or is left unaddressed by, the proposed structure. This is slow, difficult to scale across a growing deal pipeline, and heavily dependent on the tacit expertise of a small number of senior practitioners rather than on a system that captures and reuses that expertise consistently.

Sententia.ai is designed to compress that research and diligence burden directly. A client or advisory team uploads the relevant deal documents into the system; Sententia.ai reads them, identifies the jurisdictions, entities, capital flows, and regulatory touchpoints they implicate, and then independently researches the live, currently-in-force regulations, statutory provisions, tax treaties, and regulatory guidance relevant to that specific fact pattern — checking the uploaded documents against those requirements rather than against a generic checklist. Because every deal has a different mix of capital origin, target sector, investor profile, and jurisdictional path, this research is not templated: Sententia.ai tailors its regulatory research to the specific scenario in front of it on a case-by-case basis, the same way a specialist lawyer would approach a genuinely novel fact pattern rather than applying a boilerplate answer.

Beyond diligence and compliance mapping, sententia.ai is designed to reason about the structuring problem itself. Rather than simply retrieving and summarizing existing precedent, the system is intended to understand the underlying scenario, the investor's objectives, the target jurisdiction's constraints, and the regulatory trade-offs at play — well enough to propose new transaction structures suited to that specific case, not just recombinations of pre-existing templates. Each proposed structure is designed to come with its own regulatory rationale, cited sources, identified risks, and an auto-generated capital-flow diagram, so that what a lawyer receives back is a credible, well-sourced first draft, the kind of output a senior associate would produce after days of research available in minutes, and always subject to expert legal review before it is treated as validated (Section 8.6).

---

Confidential — Page 3 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 2. Problem Statement

Cross-border investment structures are subject to overlapping, frequently amended regulatory regimes across jurisdictions. Structuring a single cross-border investment typically requires lawyers to synthesize statutory materials, prior structuring precedent, and internal expert consultation before arriving at a compliant, workable structure. Independent industry data confirms just how much this manual burden costs in time: due-diligence periods for a small, clean, single-jurisdiction deal typically run 3–4 weeks, but the same process for a mid-market transaction stretches to 6–12 weeks, and for a large or cross-border regulated deal — the profile Sententia.ai is built for — it commonly runs 13–26 weeks (3–6 months) end to end, once foreign-investment review, multi-jurisdictional coordination, and layered regulatory sign-off are factored in.

![](09af5b86cf9391543d22db5f2129b3ca_img.jpg)

**Manual Due-Diligence Timelines Lengthen Sharply for Cross-Border & Regulated Transactions**

Time to Complete Due Diligence (weeks)

| Deal Category                           | Average Time | Time Range  |
|-----------------------------------------|--------------|-------------|
| Small / Clean Domestic Deal             | 3.5 wks avg  | (3-4 wks)   |
| Mid-Market Domestic Deal (\$50-500M)    | 9.0 wks avg  | (6-12 wks)  |
| Cross-Border / Regulated Deal (>\$500M) | 19.5 wks avg | (13-26 wks) |

Source: Dealroom.net, DFIN Solutions, ibinterviewquestions.com M&A Due Diligence guides (2026)

Figure 1: Manual due-diligence timelines lengthen sharply as deals cross borders and add regulatory layers. Source: Dealroom.net, DFIN Solutions, ibinterviewquestions.com M&A due-diligence guides (2026).

This is not a shrinking problem. Industry surveys of dealmaking practitioners in 2026 found that 73% expect cross-border due diligence to become even more complex going forward, driven by expanding foreign-investment screening regimes, data-localization rules, and AI-specific regulation layered on top of existing securities, tax, and exchange-control law.

Confidential — Page 4 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI![](6de7dcb072cef2388026fb0f504084b2_img.jpg)

|                                             |     |
|---------------------------------------------|-----|
| Expect due diligence to become MORE complex | 73% |
| Do not expect increased complexity          | 27% |

Source: Dataroom-providers.org, 2026 M&A Due Diligence Practitioner Survey

Figure 2: Nearly three-quarters of practitioners expect the complexity of cross-border due diligence to increase, not decrease. Source: Dataroom-providers.org, 2026 M&A due-diligence practitioner survey.

###### This creates several recurring, compounding limitations in current advisory workflows:

- High time cost** — Structuring a transaction can consume days of senior practitioner time, and diligence alone can run into months for cross-border deals (Figure 1). For example, a \$30M Series C round structured from a U.S. fund into an Indian target through a Mauritius SPV can require three separate advisory teams (U.S., Mauritius, India) each independently reviewing the same underlying document set against their own jurisdiction's rules — multiplying, rather than dividing, the total review time.
- Dependence on institutional knowledge** — Much of the relevant expertise is tacit, held by individual senior lawyers rather than captured in structured systems. When a senior partner who has handled a dozen similar Mauritius-route deals is unavailable, a firm effectively loses that precedent, and a more junior team may re-derive the same structuring logic from scratch.
- Limited scalability** — Advisory teams cannot easily scale their expertise to handle a growing volume of structuring queries. A boutique advisory practice fielding twenty simultaneous cross-border structuring mandates cannot linearly add senior partner hours to match that volume without a proportional cost increase passed on to clients.
- Fragmented analysis** — Manually integrating regulatory considerations across jurisdictions increases the risk of oversight. A structure that satisfies RBI sectoral caps but overlooks a treaty-eligibility condition under the India–Mauritius DTAA, for instance, may only surface as an issue during a later compliance audit or bank KYC review — well after capital has already moved.

Confidential — Page 5 of 28

Sententia.aiProduct Requirements Document

**CONFIDENTIAL PROPERTY OF SENTENTIA.AI**

---

- **Cross-jurisdictional coordination and communication overhead** — Language differences, differing documentation conventions, and time-zone-separated advisory teams routinely introduce delay and miscommunication risk into cross-border deals, on top of the underlying legal complexity.
- **Regulatory currency risk** — Because underlying statutes, RBI/SEBI circulars, and treaty positions are amended frequently and without centralized notice, a structuring memo that was accurate when drafted can become stale within months, and firms have no systematic way to detect when a previously-issued opinion needs to be revisited.
- **Escalating advisory cost from multi-firm coordination** — Because no single firm is licensed to opine across every relevant jurisdiction, clients often must retain and pay separate counsel in each jurisdiction touched by the structure, with the associated cost, duplicated onboarding, and coordination overhead borne largely by the client.

*This is a sensitive, high-stakes domain: outputs inform real capital-allocation and regulatory-compliance decisions. Every requirement in this document should be read with that standard in mind.*

---

Confidential — Page 6 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 3. Market Opportunity & Why Now

Two independent trends make this the right moment to build Sententia.ai:

(a) M&A and cross-border capital activity is at its highest level since 2021

(b) Legal-specific AI adoption has crossed from experimentation into firm-wide infrastructure.

Each trend is reinforced by a third, connecting force, regulatory complexity itself is expanding, not contracting, which increases rather than decreases the value of a structuring tool built specifically to keep pace with it. The figures below are drawn directly from primary sources, cross-checked for accuracy.

### 3.1 Pillar One — Record Deal Activity, With Rising Regulatory Overhead

Global M&A deal value is on track to reach approximately **\$4.0 trillion in 2026**; the strongest year since 2021 and mega-deals are absorbing a rapidly growing share of that total: up from 26% of global deal value in 2024, to 39% in 2025, to 48% in 2026 (PwC). Fewer, larger, more structurally complex deals mean more capital is concentrated in exactly the kind of multi-entity, multi-jurisdiction transactions that require the heaviest structuring and compliance work per dollar deployed.

![](112f3fc5dde002caf1c91da443844204_img.jpg)

**Mega-Deals Are Consolidating a Growing Share of Global M&A Value**

| Year                                            | 2024 | 2025 | 2026E |
|-------------------------------------------------|------|------|-------|
| Share of Global M&A Deal Value from Deals >\$5B | 26%  | 39%  | 48%   |

Source: PwC Global M&A Trends, Mid-Year 2026 Outlook

Figure 3: Mega-deals are consolidating a growing share of global M&A value, concentrating capital into the most structurally complex transaction category. Source: PwC Global M&A Trends, Mid-Year 2026 Outlook.

Global buyout value tells the same story: it rose 39% year-over-year to roughly \$850 billion in 2025, spread across just 13 mega-buyouts — more than double the prior year's count (MoFo). U.S. domestic M&A (U.S. acquirer/U.S. target) value reached approximately \$1.46 trillion, up 29% year-over-year (Torys); cross-border M&A specifically is estimated closer to \$1.2–1.24 trillion for the comparable period per LSEG-based tracking.

Critically, this deal-volume surge is colliding with a genuinely expanding regulatory perimeter, not a stable one. Foreign direct investment (FDI) screening regimes have proliferated globally: 26 of the EU's 27 member states now operate a national FDI screening mechanism (up from 24 as of September 2024), and the EU's new FDI Screening

Confidential — Page 7 of 28

Sententia.aiProduct Requirements Document

**CONFIDENTIAL PROPERTY OF SENTENTIA.AI**

Regulation will soon make such mechanisms mandatory bloc-wide (Cleary Gottlieb; White & Case, 2026 FDI Reviews). The U.S. CFIUS regime continues to broaden in scope, and India, Singapore, and other corridor jurisdictions are each layering their own sector-specific and data-related restrictions on top of existing exchange-control and securities law. More deal volume, concentrated in larger and more structurally complex transactions, moving through a denser and still-tightening regulatory perimeter, is precisely the compounding dynamic that turns structuring and diligence into the bottleneck described in Section 2.

### 3.2 Pillar Two — Legal AI Adoption Has Crossed From Experimentation Into Infrastructure

Firm-wide adoption of legal-specific AI tools reached 34% in 2026, up from 21% the prior year (8am 2026 Legal Industry Report), which represents a genuine shift from pilot programs to standing infrastructure. But that institutional figure still trails individual behaviour by a wide margin: 69% of individuals at those same firms report using general-purpose AI tools in their work, and 83% of lawyers overall have used AI at least once (Bloomberg Law, State of Practice 2026). Pulled down to the most demanding standard — genuinely daily use — only 23% of in-house lawyers report relying on AI tools every day (Bloomberg Law).

![](27b22513fc27a0ff5f230b062ad3112f_img.jpg)

**The Institutional AI Adoption Gap in Legal:  
Individuals Are Outpacing Firms**

| Category                                      | Share of Lawyers / Firms (%) | Source                |
|-----------------------------------------------|------------------------------|-----------------------|
| Individual Use of General-Purpose AI at Firms | 69%                          | (8am, 2026)           |
| Firm-Wide Adoption of Legal-Specific AI Tools | 34%                          | (8am, 2026)           |
| Daily AI Use Among In-House Lawyers           | 23%                          | (Bloomberg Law, 2026) |

Sources: 8am 2026 Legal Industry Report; Bloomberg Law State of Practice 2026

Figure 4: Individual lawyers are adopting AI faster than their institutions can formalize it — the gap between informal, individual usage and validated, firm-wide daily reliance is an institutional trust problem, not a capability problem. Sources: 8am 2026 Legal Industry Report; Bloomberg Law State of Practice 2026.

**That gap is the opportunity, not a weakness in the underlying thesis.** It shows lawyers already trust general AI enough to use it informally and constantly, while firms have not yet found a tool rigorous enough to formalize that usage into a validated, auditable, daily-use system for high-stakes work. A **purpose-built structuring tool** with a mandatory expert-review layer (Section 8.6) and a rule-based compliance engine (Section 8.4) is designed to close exactly that gap, converting informal, unvalidated individual usage into sanctioned, firm-wide infrastructure.

Confidential — Page 8 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

### 3.3 Structuring and Research Is the Largest, Fastest-Growing Segment

The AI-in-legal market is projected to grow from \$5.59 billion in 2026 to \$12.49 billion by 2030, at a 22.3% compound annual growth rate (Research And Markets) — among the fastest-growing segments of applied enterprise AI.

![Bar chart showing the projected AI-in-Legal Market Size in billions of dollars from 2026 to 2030. The values are: 2026: $5.6B, 2027: $6.8B, 2028: $8.4B, 2029: $10.2B, 2030: $12.5B.](925f55ce69802b9d3b00546382663ee2_img.jpg)

**AI-in-Legal Market Size Is Projected to More Than Double by 2030**

AI-in-Legal Market Size (\$B)

| Year | Market Size (\$B) |
|------|-------------------|
| 2026 | \$5.6B            |
| 2027 | \$6.8B            |
| 2028 | \$8.4B            |
| 2029 | \$10.2B           |
| 2030 | \$12.5B           |

Bar chart showing the projected AI-in-Legal Market Size in billions of dollars from 2026 to 2030. The values are: 2026: \$5.6B, 2027: \$6.8B, 2028: \$8.4B, 2029: \$10.2B, 2030: \$12.5B.

Source: ResearchAndMarkets AI in Legal Market Report (2026); 2027-2029 modeled from the reported 22.3% CAGR

Figure 5: The AI-in-legal market is on track to more than double by 2030. 2026 and 2030 figures are directly reported; intermediate years are modelled from the reported 22.3% CAGR. Source: ResearchAndMarkets AI in Legal Market Report (2026).

Within that market, legal research is already the single largest application segment, accounting for 29.1% of AI-in-legal software revenue (Mordor Intelligence) — ahead of contract review, compliance, drafting, and e-discovery individually.

---

Confidential — Page 9 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

#### Legal Research Is the Largest Application Segment in AI-in-Legal Revenue

![Donut chart showing the distribution of AI-in-Legal revenue. Legal Research is the largest single segment at 29.1%, while all other segments (contract review, compliance, drafting, e-discovery, etc.) combined account for 70.9%.](6b32b7b928d34eeccb15c29cdf9d2cb3_img.jpg)

|                                                                               |       |
|-------------------------------------------------------------------------------|-------|
| Legal Research — largest single segment                                       | 29.1% |
| All other segments (contract review, compliance, drafting, e-discovery, etc.) | 70.9% |

Donut chart showing the distribution of AI-in-Legal revenue. Legal Research is the largest single segment at 29.1%, while all other segments (contract review, compliance, drafting, e-discovery, etc.) combined account for 70.9%.

Source: Mordor Intelligence, AI Software Market in Legal Industry (2026)

Figure 6: Legal research and structuring-adjacent work already commands the largest share of AI-in-legal software revenue. Source: Mordor Intelligence, AI Software Market in Legal Industry (2026).

The value of the time this segment frees up is significant and growing: legal professionals expect AI to free up **nearly 240 hours per year, up from 200 hours in 2024** (Thomson Reuters Institute, Future of Professionals 2025) — worth an average of \$19,000 per professional annually, and a combined \$32 billion impact across the U.S. legal and tax-accounting sectors. Independent, vendor-sponsored ROI studies (e.g., Forrester’s Total Economic Impact analysis of Thomson Reuters CoCounsel, commissioned by Thomson Reuters itself) report up to 400% ROI for legal AI deployments — a promising but not fully independent data point, worth citing with that caveat attached rather than presenting as unsponsored research.

### 3.4 What This Means for sententia.ai

- Legal research and structuring-adjacent work is both the largest revenue segment (29%+) and the segment growing fastest (22%+ CAGR) within legal AI — Sententia.ai sits directly in that segment, but purpose-built for transactional structuring rather than generic research.
- Firm-wide adoption (34%) trails individual usage (69%) — the gap is an institutional trust and validation problem, not a capability problem (Figure 4). Sententia.ai’s compliance engine and mandatory expert-review layer (Section 8) are designed specifically to close that trust gap for a high-stakes use case.
- Record deal volumes and rising mega-deal share (Figure 3) mean structuring capacity, not just structuring accuracy, is now a competitive bottleneck for law firms and in-house teams.
- A proliferating, still-tightening global FDI-screening perimeter means the regulatory research burden underlying every cross-border structure is growing in parallel with deal volume — reinforcing rather than diminishing the case for a system built to track and apply that complexity systematically, rather than case-by-case from memory.

Sources: PwC Global M&A Trends Mid-Year 2026; MoFo M&A in 2025 and Trends for 2026; Torys Quarterly Q3 2025; ResearchAndMarkets AI in Legal Market Report (2026); Bloomberg Law State of Practice 2026; 8am 2026 Legal Industry Report; Mordor Intelligence AI Software Market in Legal Industry; Thomson Reuters Institute, Future of Professionals 2025; Forrester

Confidential — Page 10 of 28

Sententia.aiProduct Requirements Document

**CONFIDENTIAL PROPERTY OF SENTENTIA.AI**

*TEI study of Thomson Reuters CoCounsel Legal (vendor-commissioned); White & Case 2026 Foreign Direct Investment Reviews; Cleary Gottlieb, The Rise of the New EU FDI Screening Regulation.*

## 4. Product Vision & Goals

**Vision:** Sententia.ai becomes the default AI associate that legal and advisory teams turn to for the first pass on any cross-border structuring question, producing output that a senior associate or partner would recognize as a credible, well-sourced starting point for their own review. Sententia.ai doesn't aim to replace the application of mind, but rather redirect the critical thought of a transactions team towards accurate approval of the workflow and in turn execute the Investment Plan in a time efficient manner.

### 4.1 Product Goals

- Reduce the time to a first structuring draft from days to minutes.
- Generate multiple legally viable, ranked structuring alternatives per scenario, matching how advisors already present options to clients.
- Map compliance obligations and flag risks for each structure, jurisdiction by jurisdiction.
- Auto-generate client-ready capital-flow diagrams for every structure.
- Maintain legal accuracy through a rigorous expert-validation layer and a rule-based compliance engine — not model output alone.

### 4.2 Non-Goals (at this stage)

- Sententia.ai does not provide final legal advice or opinions, and does not replace lawyer sign-off.
- Sententia.ai does not (at MVP) execute filings, submit regulatory approvals, or move capital.
- Sententia.ai does not, at MVP, cover litigation, IP prosecution, or employment law — the initial scope is transactional structuring only.

---

Confidential — Page 11 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 5. Target Users & Personas ---

| Persona                                        | Description / Primary Need                                                                                                                                                         |
|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <b>Corporate / Structuring Associate</b>       | Associate at a law firm handling cross-border transactions. Needs a fast, well- sourced first draft of structuring options to accelerate research and drafting.                    |
| <b>Partner / Senior Counsel</b>                | Reviews and signs off on structuring advice given to clients. Needs confidence that first-pass output is accurate, complete, and defensible, with time saved on routine synthesis. |
| <b>In-House Counsel (Fund / Family Office)</b> | Legal or compliance lead at a fund, family office, or multinational. Needs self-serve exploration of structuring options before engaging outside counsel.                          |
| <b>Compliance / Risk Officer</b>               | Reviews regulatory exposure of proposed structures. Needs clear compliance mapping and risk flags per structure, per jurisdiction.                                                 |

---

Confidential — Page 12 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 6. Illustrative Use Case

**Scenario: Client:** HSG Corp., a Semi-Conductor manufacturer based in Shenzhen, China seeks to invest in a Semiconductor Manufacturing facility in India funding Semi (India) Ltd.

Given the origin of capital, target jurisdiction, sector, investment size, and investor profile, sententia.ai generates multiple structuring alternatives, such as:

**Primary Structure** Under this approach, HSG (China) first invests into a Singapore-incorporated special-purpose vehicle Global Fund. That Singapore SPV then enters into a joint venture with the Indian entity Semi (I) Ltd. on a 74:26 ownership basis **Semi (I) Ltd. holding 74 % and the Singapore SPV holding 26 %**), without veto rights or any form of negative control.

The resulting JV in turn owns and operates the new manufacturing facility, New Semi Manufacturing Co. This layered structure preserves Indian majority ownership and key managerial control at both the JV and operating-company levels, aligns with emerging ISM/ECMS policy signals and anticipated PN3 parameters, and mirrors approved 74:26 precedents. Governance is documented through a Shareholders' Agreement that expressly excludes negative-control rights for the minority investor, rendering the overall arrangement materially more acceptable to Indian authorities than a direct or controlling acquisition.

![Diagram of the Primary Structure for HSG investment in India.](4636adff5682a064f0ae5f13a1d464a6_img.jpg)

The diagram illustrates the Primary Structure across three jurisdictions: CHINA, SINGAPORE, and INDIA.

- CHINA:** HSG (Horizon Semiconductor Group) is the initial investor.
- SINGAPORE:** HSG invests in the SEMI(I) JV through a Singaporean SPV Global fund with International Investors to reduce Beneficial Ownership (BO) of Chinese entity citing Press Note-3 Regulations applicable on Chinese Investments into Indian Jurisdiction.
- INDIA:** The Singapore SPV Global Fund and SEMI (I) Ltd. enter into a joint venture, SEMI (I) - S. SPV GF.JV, with ownership divided according to the prescribed structure of 74%-26%. This structure is implemented in Indian Jurisdiction, citing Press Note 3 regulation. FDI flows into the JV by cash via AD Banking Channels. The Singaporean SPV will expressly hold no voting rights.
- Operating Company:** The JV, SEMI (I) - S. SPV GF.JV, owns and operates the New Semi Manufacturing Co.

Diagram of the Primary Structure for HSG investment in India.

12

**Alternative Structure** HSG (or a wholly-owned affiliate) invests directly into a newly incorporated Indian joint-venture company alongside Semi (I) Ltd. on the same 74:26 ownership split, with Semi (I) Ltd. retaining majority ownership, board control and all key managerial rights.

The JV itself owns and operates New Semi Manufacturing Co. This simpler two-party structure eliminates the Singapore layer, reduces intermediate compliance steps, and still satisfies the core PN3 risk-mitigation preferences of Indian control and non-controlling foreign participation, though it places the Chinese investor in a more direct (and therefore more heavily

![Diagram of the Alternative Structure for HSG investment in India.](5dfc130b129ace4df375839020a5700d_img.jpg)

The diagram illustrates the Alternative Structure across two jurisdictions: CHINA and INDIA.

- CHINA:** HSG is the investor.
- INDIA:** HSG invests directly into a joint venture, SEMI (I) - HSG JV, alongside SEMI (I) Ltd. Ownership is divided according to the prescribed structure of 74%-26%, implemented in Indian Jurisdiction, citing Press Note 3 regulation. FDI flows into the JV by cash via AD Banking Channels. The Regulatory Landscape does not expressly bar a Joint Venture between India-China, however, Clear Intent of Indian Beneficial Ownership must be shown to avoid rejection from MEA. HSG will expressly hold no voting rights.
- Operating Company:** The JV, SEMI (I) - HSG JV, owns and operates the New Semi Manufacturing Co.

Diagram of the Alternative Structure for HSG investment in India.

1Confidential — Page 13 of 28

Sententia.aiProduct Requirements Document

**CONFIDENTIAL PROPERTY OF SENTENTIA.AI**

scrutinised) position under the existing approval regime.

For each structure, Sententia.ai identifies the governing frameworks, for example, FEMA regulations, sectoral caps under the Consolidated FDI Policy, RBI and SEBI requirements, tax-treaty implications, and reporting obligations and renders a capital-flow diagram showing entities, jurisdictions, and approval checkpoints.

### 1. Scenario Intake (FR-1.1, FR-1.2)

- Transaction snapshot: HSG Corp. (Shenzhen, China) proposes a majority-capital investment into a new semiconductor fabrication facility in India, sponsored by Semi (I) Ltd.
- Data captured: capital origin, target jurisdiction, sector (semiconductor manufacturing), investment size, investor profile, indicative deal timeline
- All required fields are validated before the associate can proceed to the next layer

*How the AI gathers this: the associate completes a structured intake form inside Sententia.ai; the model auto-fills known company details from public filings/registries where available (e.g., MCA/ROC data) and flags any missing mandatory field before allowing progression.*

### 2. Legal Knowledge Layer (FR-2.1, FR-2.2)

- Retrieves the exact provisions triggered by this fact pattern: Press Note 3 (land-bordering-country rule), the Consolidated FDI Policy's semiconductor-sector conditions, FEMA (Non-Debt Instruments) Rules, and India-Singapore DTAA terms
- Every provision shown is version- and source-dated, so the associate always sees the text currently in force

*How the AI gathers this: a retrieval pipeline queries a continuously updated corpus of RBI/DPIIT circulars, gazette notifications and treaty texts, ranks passages by relevance to the Step-1 fact pattern, and surfaces the specific clauses — not just the topic areas — that apply.*

### 4. Compliance Validation (FR-4.1 – 4.3)

- Cross-checks each structure against sectoral investment caps, PN3 investor-eligibility conditions, and capital-inflow / AD-banking rules
- Flags or blocks any variant that fails a hard rule, and logs every check performed for the audit trail

*How the AI gathers this: a separate, deterministic rule-based engine re-reads the structured output of Step 3 against a codified rule set — independently of the LLM's own reasoning — so a hallucinated citation cannot silently pass compliance.*

### 3. Structuring Generation (FR-3.1 – 3.3)

- Drafts the Primary and Alternative structures as distinct, ranked options — never a single “take-it-or-leave-it” answer
- Cites the specific regulatory provision behind each design choice: the 74:26 ownership split, the no-negative-control drafting convention, the SPV layer

*How the AI gathers this: the LLM layer combines the Step-1 fact pattern with the Step-2 retrieved provisions in a structured prompt, generates candidate ownership/control configurations, and self-checks each candidate's citations against the source text before presenting it.*

### 5. Visualization Layer (FR-5.1, FR-5.2)

- Maps every cited rule — PN3, FDI sectoral cap, FEMA, treaty terms — onto the entities and edges below: each ownership %, control right and approval checkpoint is rendered directly on the diagram
- Produces an annotated, exportable (image / PDF) capital-flow diagram for each structure

*How the AI gathers this: the layer parses the validated structure object (entities, ownership %, rights, citations) from Steps 3–4 and auto-lays out a node-edge diagram, attaching the underlying clause reference to each connector as footnote metadata.*

↓ Two structures are generated in parallel ↓

#### Primary Structure — Lead Recommendation

- AI consolidation: merges the PN3 land-border trigger + FDI sectoral cap for semiconductors + India-Singapore DTAA relief + the no-negative-control drafting convention
- Outcome: preserves Indian majority ownership and key managerial control at both the JV and operating-company levels; aligns with anticipated PN3 parameters

*How the AI gathers this: cross-references the Step-2 treaty corpus with prior validated deal structures in the firm's precedent library to select the SPV jurisdiction and ownership split most likely to be accepted by the regulator.*

#### Alternative Structure — Simpler, More Exposed

- AI consolidation: merges the PN3 land-border trigger + FDI sectoral cap + the direct-JV compliance convention (fewer intermediate filings, no treaty layer)
- Outcome: eliminates the Singapore layer and reduces intermediate compliance steps, but places HSG in a more directly scrutinised position under the existing approval regime

*How the AI gathers this: benchmarks the simplified two-party structure against Sententia.ai's compliance-rule engine to confirm it still clears sectoral caps, then raises the residual scrutiny risk as a structured warning for the reviewer.*

Confidential — Page 14 of 28

Sententia.ai

Product Requirements Document

###### CONFIDENTIAL PROPERTY OF SENTENTIA.AI

![](7efae06af3af43ffe5d4b956a679cf54_img.jpg)

|                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |                                                                                                                                                                                                                                                                                                                                                   |
|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <p><b>HSG Corp. (Shenzhen, China) — Origin of Capital</b></p> <ul style="list-style-type: none"><li>Invests capital into the Singapore SPV “Global Fund”</li></ul> <p><i>How the AI gathers this: KYC / beneficial-ownership intake, constitutional documents, and the board resolution authorising the outbound investment.</i></p>                                                                                                                                                                                                                                                                                                         | <p><b>HSG Corp. (Shenzhen, China) — Origin of Capital</b></p> <ul style="list-style-type: none"><li>Invests directly into the Indian JV — no SPV layer</li></ul> <p><i>How the AI gathers this: KYC / beneficial-ownership intake, constitutional documents, and the board resolution authorising the direct investment.</i></p>                  |
| ↓                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ↓                                                                                                                                                                                                                                                                                                                                                 |
| <p><b>Singapore SPV “Global Fund”</b></p> <ul style="list-style-type: none"><li>Holding vehicle; enters the JV with Semi (I) Ltd. on a 74:26 basis</li></ul> <p><i>How the AI gathers this: SPV incorporation certificate and a treaty-eligibility questionnaire, used to confirm the DTAAs benefit test is met.</i></p>                                                                                                                                                                                                                                                                                                                     | <p><b>— No SPV Layer in This Route —</b></p> <ul style="list-style-type: none"><li>HSG invests directly; this step is skipped entirely in the Alternative Structure</li></ul> <p><i>How the AI gathers this: n/a — the compliance engine confirms no treaty layer is required for the direct-JV route.</i></p>                                    |
| ↓                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ↓                                                                                                                                                                                                                                                                                                                                                 |
| <p><b>JV: Semi (I) Ltd. 74% + Singapore SPV 26%</b></p> <ul style="list-style-type: none"><li>No veto rights or any form of negative control held by the SPV</li></ul> <p><i>How the AI gathers this: draft JV agreement terms, board composition and the shareholder-rights matrix — checked against the “no negative control” rule.</i></p>                                                                                                                                                                                                                                                                                                | <p><b>JV: Semi (I) Ltd. 74% + HSG 26% (direct)</b></p> <ul style="list-style-type: none"><li>Indian board control and all key managerial rights retained by Semi (I) Ltd.</li></ul> <p><i>How the AI gathers this: draft JV agreement terms, board composition and the shareholder-rights matrix — checked against the same control rule.</i></p> |
| ↓                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            | ↓                                                                                                                                                                                                                                                                                                                                                 |
| <p><b>New Semi Manufacturing Co. (India)</b></p> <ul style="list-style-type: none"><li>Owns and operates the fabrication facility</li></ul> <p><i>How the AI gathers this: proposed project cost, land/site details and the facility commissioning timeline — feeds the capital-inflow schedule.</i></p>                                                                                                                                                                                                                                                                                                                                     | <p><b>New Semi Manufacturing Co. (India)</b></p> <ul style="list-style-type: none"><li>Owns and operates the fabrication facility</li></ul> <p><i>How the AI gathers this: same project data set as the Primary Structure; re-validated against the direct-JV ownership split.</i></p>                                                            |
| ↓ Both structures are routed to the Transactions Team for review ↓                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |                                                                                                                                                                                                                                                                                                                                                   |
| <p><b>6. Human-in-Loop Approval (Section 12, FR-6.1 – 6.4) — Final Step</b></p> <ul style="list-style-type: none"><li>The Transactions Team reviews BOTH structures above for legal correctness, regulatory completeness and clarity</li><li>Standard advisory disclaimer applies to every output until it is marked validated for client-facing use</li></ul> <p><i>How the AI gathers this: compiles a review packet (structures, citations, compliance log, open flags) so the human reviewer is not starting from scratch, and captures reviewer edits back into the precedent library to improve future structuring generation.</i></p> |                                                                                                                                                                                                                                                                                                                                                   |

Confidential — Page 15 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

---

## 7. Scope ---

### 7.1 MVP Scope (Phase 0)

- Structured scenario intake (capital origin, target jurisdiction, sector, size, regulatory constraints, investor profile).
- Generation of 2–4 ranked structuring alternatives per scenario.
- Compliance mapping and risk flagging against a curated regulatory knowledge base for the MVP corridor.
- Auto-generated capital-flow diagram per structure, exportable as image/PDF.
- Expert review workflow for validating and correcting model output before it reaches end users.

### 7.2 Out of Scope for MVP

- Automated regulatory filing or submission.
- Tax structuring, M&A/PE transaction planning, and automated legal memo drafting (targeted for later phases — see Section 15).
- Public self-serve access without an onboarding/validation relationship with a firm or design partner.

---

Confidential — Page 16 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 8. Functional Requirements

Requirements are grouped by the four architectural layers described in Section 12. Priority: P0 = required for MVP, P1 = near-term post-MVP, P2 = later phase.

### 8.1 Scenario Intake

| ID     | Requirement                                                                                                                                                                                              | Priority |
|--------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-1.1 | The system shall capture, at minimum: origin of investment capital, target jurisdiction, sector of the underlying business, investment size and structure, regulatory constraints, and investor profile. | P0       |
| FR-1.2 | The system shall validate required fields and prompt the user for missing information before generating output.                                                                                          | P0       |
| FR-1.3 | The system shall allow users to save, duplicate, and re-run a scenario with modified parameters.                                                                                                         | P1       |
| FR-1.4 | The system shall support saved scenario templates for recurring deal types (e.g., standard VC round, PE buyout).                                                                                         | P2       |

### 8.2 Legal Knowledge Layer

| ID     | Requirement                                                                                                                                                                                                  | Priority |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-2.1 | The system shall maintain a structured, versioned repository of statutory texts, regulations, government policy documents, regulatory guidance, and applicable tax treaties for each supported jurisdiction. | P0       |
| FR-2.2 | The system shall record the effective date and source of every regulatory provision used in an output, to support traceability.                                                                              | P0       |
| FR-2.3 | The system shall flag when underlying source material has been superseded or amended since last indexed, and shall notify the expert-review team.                                                            | P1       |
| FR-2.4 | The system shall support incremental addition of new jurisdictions without requiring a full system re-architecture.                                                                                          | P1       |

### 8.3 Structuring Generation (LLM Processing Layer)

| ID     | Requirement                                                                                                                                                                                                                                                                          | Priority |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-3.1 | The system shall generate multiple (2–4 for MVP) distinct, legally viable structuring alternatives per scenario, rather than a single recommendation.                                                                                                                                | P0       |
| FR-3.2 | Each generated structure shall include: a description of the investment architecture, the jurisdictions involved, applicable compliance requirements, required regulatory approvals, and potential risks after-which which the model will create a multi-stage Investment structure. | P0       |

Confidential — Page 17 of 28

Sententia.aiProduct Requirements Document

###### **CONFIDENTIAL PROPERTY OF SENTENTIA.AI**

| ID     | Requirement                                                                                                | Priority |
|--------|------------------------------------------------------------------------------------------------------------|----------|
| FR-3.3 | The system shall cite the specific regulatory provisions supporting each element of a generated structure. | P0       |
| FR-3.4 | The system shall allow a user to ask follow-up, scenario-specific questions about a generated structure.   | P1       |
| FR-3.5 | The system shall support side-by-side comparison of generated structures.                                  | P1       |

### 8.4 Compliance Validation Layer

| ID     | Requirement                                                                                                                                                                                                                                                                     | Priority |
|--------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-4.1 | The system shall cross-check every generated structure against a rule-based compliance engine covering, at minimum: sectoral caps on foreign investment, investor eligibility, capital-inflow restrictions, reporting/approval requirements, and treaty-eligibility conditions. | P0       |
| FR-4.2 | The system shall block or clearly flag any generated structure that fails a hard compliance rule, rather than presenting it as viable.                                                                                                                                          | P0       |
| FR-4.3 | The system shall log every compliance check performed against a structure, for audit purposes.                                                                                                                                                                                  | P0       |
| FR-4.4 | The system shall support jurisdiction-specific rule updates without requiring redeployment of the core model.                                                                                                                                                                   | P1       |

### 8.5 Visualization Layer

| ID     | Requirement                                                                                                                                                                                    | Priority |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-5.1 | The system shall automatically generate a capital-flow diagram for each structure, showing entities, their jurisdictions, direction of capital flow, and points requiring regulatory approval. | P0       |
| FR-5.2 | The system shall allow diagrams to be exported as image and PDF, suitable for inclusion in client-facing materials.                                                                            | P0       |
| FR-5.3 | The system shall allow basic manual adjustment of diagram layout (entity position, labelling) before export.                                                                                   | P1       |
| FR-5.4 | The system shall support export of the full structuring output (text + diagram) as a formatted memo document.                                                                                  | P1       |

### 8.6 Human in Loop Overview & Output Delivery

| ID     | Requirement                                                                                                                                                      | Priority |
|--------|------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-6.1 | The system shall route newly generated structures through a human in loop queue before they are marked as validated, during the MVP and early-validation phases. | P0       |
| FR-6.2 | The system shall visibly distinguish expert-validated output from unvalidated / in- review output to the end user.                                               | P0       |

Confidential — Page 18 of 28

Sententia.aiProduct Requirements Document**CONFIDENTIAL PROPERTY OF SENTENTIA.AI**

| ID     | Requirement                                                                                                                                                        | Priority |
|--------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| FR-6.3 | The system shall capture expert feedback (corrections, approvals, rejections) in a structured form usable for model and rules improvement.                         | P0       |
| FR-6.4 | The system shall display a standard disclaimer on every output clarifying that it is an analytical aid, not a substitute for independent legal advice or sign-off. | P0       |

### 8.7 Administration & Access Control

| ID     | Requirement                                                                                                           | Priority |
|--------|-----------------------------------------------------------------------------------------------------------------------|----------|
| FR-7.1 | The system shall support role-based access control (e.g., associate, partner/reviewer, compliance officer, admin).    | P0       |
| FR-7.2 | The system shall support firm-level workspaces so that scenarios and outputs are scoped to the correct client/matter. | P0       |
| FR-7.3 | The system shall maintain an audit log of who generated, viewed, edited, or exported each structuring output.         | P0       |
| FR-7.4 | The system shall support single sign-on (SSO) for enterprise/law-firm customers.                                      | P1       |

Confidential — Page 19 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 9. Non-Functional Requirements

| Category                | Requirement                                                                                                                                                                             |
|-------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Legal Accuracy          | Every structure and compliance claim must be traceable to a cited regulatory source, and must pass through expert validation before being marked as validated for client- facing use.   |
| Security & Data Privacy | Client and matter data must be encrypted in transit and at rest, logically segregated by firm/workspace, and never used to train shared models without explicit, opt-in client consent. |
| Auditability            | Every generated output, compliance check, and expert edit must be logged with a timestamp and actor, and retrievable for audit or malpractice-defense purposes.                         |
| Explainability          | Outputs must show their reasoning and cited sources, not just a conclusion — consistent with how a first-pass associate memo would be reviewed.                                         |
| Performance             | A structuring scenario should return a first draft of alternatives within a target of under 5 minutes for the MVP corridor.                                                             |
| Availability            | Production system uptime target of 99.5% during business hours across supported time zones, once past pilot phase.                                                                      |
| Regulatory Currency     | The legal knowledge layer must flag when source material may be stale and support rapid re-indexing after a regulatory change.                                                          |

Confidential — Page 20 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## --- 10. System Architecture Overview ---

Sententia.ai is organized into four interconnected layers:

- **Legal Knowledge Layer** — A structured, versioned repository of statutory provisions, regulations, and policy frameworks.
- **LLM Processing Layer** — The core language model that interprets scenario inputs and drafts candidate structures.
- **Compliance Validation Layer** — A rule-based engine that checks generated structures against regulatory conditions and blocks or flags non-compliant options.
- **Visualization Layer** — Converts structuring output into capital-flow diagrams.

Training and refinement approach: the model combines general language modelling with domain-specific rule frameworks, optimized for extracting regulatory conditions from statutory text, mapping relationships between legal requirements, identifying relevant regimes based on scenario inputs, and generating structured advisory output. Rule-based modules encode specific legal requirements to keep outputs consistent with statutory constraints, rather than relying on the language model alone.

---

Confidential — Page 21 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 11. Data Sources & Data Strategy ---

The legal knowledge layer that powers the AI model's generation of cross-border fund investment structures is deliberately multi-sourced and continuously refreshed. It draws on the following categories of primary and secondary materials, each selected and weighted for relevance to multi-jurisdictional fund flows, FDI/FEMA compliance, tax-efficient structuring, and regulatory risk mitigation:

- **Primary statutory texts and subordinate regulations** – Including the Foreign Exchange Management Act, 1999 and its rules/regulations, the Companies Act, 2013, the Income-tax Act, 1961 (and corresponding foreign tax codes), the Foreign Contribution (Regulation) Act, 2011, securities laws, and any sector-specific statutes that govern the underlying asset class or educational/operational activity in the Indian jurisdiction. The AI model systematically incorporates the full corpus of primary and secondary regulatory and legal sources from every other jurisdiction participating in the transaction corridor (for example, Delaware LLC statutes, U.S. federal securities and tax rules, or equivalent legislation in any additional source or intermediate jurisdiction), ensuring that the generated structure remains coherent across the entire cross-border chain.
- **Government policy documents and notifications** – Contemporaneous FDI policy circulars, Press Notes, Consolidated FDI Policy editions, RBI Master Directions, and equivalent policy instruments issued by the host-country government that shape the permissible investment corridors, sectoral caps, and entry routes.
- **Regulatory guidance and interpretative materials issued by competent authorities** – RBI FAQs, SEBI circulars and informal guidance, FEMA compounding orders, U.S. Treasury/IRS notices, OFAC sanctions lists, and analogous guidance from other corridor regulators, ensuring the model reflects current administrative practice rather than solely black-letter law.
- **International tax treaties and related instruments** – The full text of applicable Double Taxation Avoidance Agreements (DTAAs), Multilateral Instrument (MLI) provisions, OECD and UN Model Convention commentaries, and any competent-authority arrangements that affect withholding tax, permanent-establishment risk, and treaty-shopping defences in the relevant investment corridor.
- **Authoritative legal commentary and academic analysis** – Leading treatises, peer-reviewed journal articles, and practitioner monographs on cross-border private equity, venture capital, and impact-fund structuring, used to surface nuanced interpretive positions and emerging doctrinal trends.
- **Structuring precedents derived from legal practice** – Anonymised term-sheet patterns, SHA and SHA-side-letter formulations, escrow and consulting-agreement architectures, and valuation/exit mechanics that have been successfully deployed in comparable cross-border education or social-sector fund investments, incorporated only where sourceable under applicable professional-conduct and confidentiality rules.
- **Human-in-the-Loop review, analysis and correction** – Performed by qualified Transactions Attorneys (engaged through partner law firms or independent practitioners) who examine every Hypothetical Fund Investment Illustrative example model-generated fund investment structure for legal correctness, regulatory completeness, tax efficiency and commercial practicality; their marked-up outputs and risk notes are systematically re-ingested to refine both the rule-based compliance engine and the underlying model weights.

*Data licensing, sourcing rights, and client-confidentiality boundaries need explicit legal review before*

---

Confidential — Page 22 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 12. Human in Loop Approval

Legal accuracy remains the product's core credibility requirement.

Within the integrated deployment at the host law firm, every AI-generated structure, regulatory analysis, and explanatory output is subject to mandatory Human-in-the-Loop Approval by the firm's Transactions Team before any client-facing use or downstream action.

The Transactions Team (comprising specialists in corporate law, international taxation, regulatory compliance, and fund structuring) evaluates:

- The legal correctness of the proposed structures;
- The completeness of the regulatory analysis; and
- The clarity of the explanations provided.

Approved outputs, together with any required amendments or risk notes, are fed back into both the rule-based compliance engine and the iterative model-refinement loop (Section 8.6, FR-6.3).

This firm-controlled approval gate ensures that sententia.ai functions strictly as a decision-support tool under the professional oversight of the law firm's Transactions Team.

![Flowchart of the Human in Loop Approval process.](f0b7aaa539a2f77c98d53ed6c1c2366b_img.jpg)

```
graph TD; A["AI-generated output  
Structures, analysis, explanations"] --> B["Transactions team review  
Legal correctness, completeness, clarity"]; B --> C["Needs amendment"]; B --> D["Approved"]; C --> B; C --> E["Feedback loop  
Compliance engine & model refinement"]; D --> F["Client-facing use  
Or downstream action"];
```

The flowchart illustrates the Human in Loop Approval process. It begins with 'AI-generated output' (Structures, analysis, explanations) in a dark grey box. An arrow points down to 'Transactions team review' (Legal correctness, completeness, clarity) in a dark grey box. From the review box, two paths emerge: one to 'Needs amendment' (Amber box) and another to 'Approved' (Green box). A feedback loop arrow returns from 'Needs amendment' to the 'Transactions team review' box. From 'Needs amendment', an arrow points down to 'Feedback loop' (Compliance engine & model refinement) in a dark grey box. From 'Approved', an arrow points down to 'Client-facing use' (Or downstream action) in a green box.

Flowchart of the Human in Loop Approval process.

Amber = requires amendment · Green = approved for downstream use

Confidential — Page 23 of 28

Sententia.ai

Product Requirements Document

CONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 13. Competitive Landscape

Most legal AI tools active in cross-border practice today cluster into two categories, neither of which is purpose-built for transactional structuring:

| Category                                      | Representative Approach & Gap                                                                                                                                                                                                                  |
|-----------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| General-purpose legal research / drafting AI  | Optimized for case law search, contract review, and memo drafting across broad practice areas. Strong at retrieval, weak at generating multiple ranked, compliance-checked structuring alternatives with auto-generated capital-flow diagrams. |
| Contract lifecycle & workflow platforms       | Strong at negotiation, redlining, and multi-jurisdiction workflow coordination for existing agreements. Not designed to originate new investment structures from a blank scenario.                                                             |
| Multi-model / translation- accuracy platforms | Address cross-border risk at the language and terminology-consistency layer (e.g., running text through multiple models to catch translation drift). Valuable, but adjacent — not a structuring-generation or compliance-mapping tool.         |

sententia.ai’s differentiation is depth, not breadth: a rule-based compliance engine purpose-built for cross-border fund structuring, auto-generated capital-flow diagrams as a first-class output (not a bolt-on), and a mandatory expert-validation loop that directly targets the institutional-trust gap identified in Section 3.4 — the 34% firm-wide vs. 69% individual adoption split. As broad legal-AI platforms add generic “structuring” features, this compliance-engine rigor and diagram-generation depth is the moat to defend.

Confidential — Page 24 of 28

Sententia.ai

Product Requirements Document

CONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 14. Success Metrics / KPIs

| Metric                          | MVP Target (indicative)                                                                                                                                                             |
|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Time to first structuring draft | Under 5 minutes, vs. multi-day baseline for manual research.                                                                                                                        |
| Expert-validation pass rate     | Track % of generated structures accepted without material correction; target improvement quarter over quarter.                                                                      |
| User-reported time saved        | Self-reported hours saved per structuring query, collected via design-partner feedback; benchmark against the ~240 hrs/year industry expectation (Thomson Reuters Institute, 2025). |
| Compliance-flag accuracy        | Rate of true positive vs. false positive/negative compliance flags, validated against expert review.                                                                                |

*These are indicative starting targets for the MVP phase; final targets should be agreed with design partners once baseline data is available.*

Confidential — Page 25 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 15. Roadmap ---

| Phase              | Timeframe & Focus                                                                                                                                                                         |
|--------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Phase 0 — MVP      | 0–6 months. Structured scenario intake (capital origin, target jurisdiction, sector, size, regulatory constraints, investor profile; core 4-layer architecture; expert-validated outputs. |
| Phase 1 — Expand   | 6–12 months. Additional jurisdictions and investor profiles; hardened compliance engine; move from pilot to paid seats.                                                                   |
| Phase 2 — Broaden  | 12–24 months. Tax structuring, M&A and PE transaction-planning use cases; API access for fund administrators and fintech.                                                                 |
| Phase 3 — Platform | 24+ months. Comprehensive AI platform for transactional legal practice, including automated legal memo drafting.                                                                          |

---

Confidential — Page 26 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 16. Risks & Mitigations

| Risk                                                                                   | Mitigation                                                                                                                                                                                                |
|----------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| <b>Model generates a legally incorrect or non-compliant structure.</b>                 | Rule-based compliance validation layer (Section 8.4) plus mandatory expert review before any output is marked validated (Section 8.6).                                                                    |
| <b>Unauthorized practice of law (UPL) exposure.</b>                                    | Position and market Sententia.ai explicitly as an analytical aid for licensed professionals, with disclaimers on every output (FR-6.4); route all client-facing use through a reviewing lawyer at launch. |
| <b>Regulatory source material becomes stale.</b>                                       | Versioned knowledge base with source dating and staleness flags (FR-2.2, FR- 2.3); defined re-indexing process after known regulatory changes.                                                            |
| <b>Client confidentiality / data leakage across firms.</b>                             | Workspace-level data segregation, encryption at rest and in transit, and no default use of client data for shared model training (Section 9).                                                             |
| <b>Slow enterprise sales cycles at law firms.</b>                                      | Prioritize design-partner pilots and in-house counsel / family office buyers alongside law firms to diversify early revenue.                                                                              |
| <b>Competitive pressure from broad legal-AI platforms adding structuring features.</b> | Maintain depth advantage: compliance-engine rigor and auto-generated capital-flow diagrams purpose-built for structuring, not bolted onto a general research tool (Section 13).                           |

Confidential — Page 27 of 28

Sententia.aiProduct Requirements DocumentCONFIDENTIAL PROPERTY OF SENTENTIA.AI

## 17. Glossary ---

| Term         | Definition                                                              |
|--------------|-------------------------------------------------------------------------|
| <b>FDI</b>   | Foreign Direct Investment.                                              |
| <b>FEMA</b>  | Foreign Exchange Management Act (India).                                |
| <b>RBI</b>   | Reserve Bank of India.                                                  |
| <b>SEBI</b>  | Securities and Exchange Board of India.                                 |
| <b>FCRA</b>  | Foreign Contribution (Regulation) Act (India).                          |
| <b>AIF</b>   | Alternative Investment Fund.                                            |
| <b>SPV</b>   | Special Purpose Vehicle.                                                |
| <b>UPL</b>   | Unauthorized Practice of Law.                                           |
| <b>CAGR</b>  | Compound Annual Growth Rate.                                            |
| <b>ManCo</b> | Management Company (third-party fund administration/compliance entity). |

---

Confidential — Page 28 of 28