# Simulation Template Folder: Diagram & Document Pairing Reference

This document serves as the persistent reference mapping each Mermaid diagram file (`.mmd`) in `simulation_template_folder` to its corresponding structure markdown (`.md`) specification document, detailing exact entity flows, tax mechanics, and legal provisions.

---

## 1. Pairing Matrix Overview

| Diagram File | Paired Structure Markdown File | Key Topic / Section |
| :--- | :--- | :--- |
| [`diagram1.mmd`](file:///e:/MNLU_sententia_AI/simulation_template_folder/diagram1.mmd) | [`datalab-output-Project_Ananta_Structuring_Note.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/datalab-output-Project_Ananta_Structuring_Note.md) | **Primary Structure & Investment Flow** (Section 3) |
| [`diagram2.mmd`](file:///e:/MNLU_sententia_AI/simulation_template_folder/diagram2.mmd) | [`datalab-output-Project_Ananta_Structuring_Note.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/datalab-output-Project_Ananta_Structuring_Note.md)<br>& [`PropCO-Opco Transaction Structure.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/PropCO-Opco%20Transaction%20Structure.md) | **Repatriation, Tax Withholding & Cash Flows** (Sections 4 & 7 / Section 6) |
| [`diagram3.mmd`](file:///e:/MNLU_sententia_AI/simulation_template_folder/diagram3.mmd) | [`datalab-output-Project_Ananta_Structuring_Note.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/datalab-output-Project_Ananta_Structuring_Note.md) | **Alternative Delaware Joint Venture (JV LLC) Model** (Section 8) |

---

## 2. Detailed Technical Mapping

### A. [`diagram1.mmd`](file:///e:/MNLU_sententia_AI/simulation_template_folder/diagram1.mmd) — Primary Investment & Entity Relationship Flow
* **Corresponding Document:** [`datalab-output-Project_Ananta_Structuring_Note.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/datalab-output-Project_Ananta_Structuring_Note.md) *(Section 3, Lines 61–99)*
* **Supporting Document:** [`PropCO-Opco Transaction Structure.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/PropCO-Opco%20Transaction%20Structure.md) *(Sections 1, 3 & 4)*
* **Mapped Flow Details:**
  * **USA Investors:** `MGF` (Meridian Grace Foundation, 501(c)(3)) and `AEP` (Atlas Education Partners LLC) co-investing under a Term Sheet.
  * **FDI Inflows:**
    * `MGF` → `PROP` (*Meridian Campus Infrastructure Pvt. Ltd.*, Indian WOS) via incorporation equity + CCPS capex tranche.
    * `AEP` → `OPCO` (*Ananta Educare Pvt. Ltd.*, ESC) via equity shares based on FMV valuation and FC-GPR reporting.
  * **Indian Operating & Contractual Layer:**
    * `PROP` → `AET` (*Ananta Education Trust*) via registered long-term Lease Deed for the campus.
    * `OPCO` → `AET` via Management & Consultancy Agreement.
    * `AET` operates `SCHOOL` (*Ananta International School, Pune*, CBSE affiliated).

---

### B. [`diagram2.mmd`](file:///e:/MNLU_sententia_AI/simulation_template_folder/diagram2.mmd) — Capital Repatriation & Cash Flow Mechanics
* **Corresponding Document:** [`datalab-output-Project_Ananta_Structuring_Note.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/datalab-output-Project_Ananta_Structuring_Note.md) *(Section 4 & Section 7)*
* **Corresponding Document:** [`PropCO-Opco Transaction Structure.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/PropCO-Opco%20Transaction%20Structure.md) *(Section 6)*
* **Mapped Flow Details:**
  * **School Fee Collections:** `FUNDS` flow into `AET`, permitting a 6–15% "reasonable surplus" (per *Islamic Academy of Education* Supreme Court precedent).
  * **Domestic Inter-Entity Payments:**
    * `AET` → `PROP`: Lease Rental subject to 10% TDS (Section 194-I) + 18% GST.
    * `AET` → `OPCO`: Consultancy fees subject to arm's-length transfer pricing + 18% GST.
  * **Cross-Border Repatriation:**
    * `PROP` → `MGF` & `OPCO` → `AEP`: Dividends repatriated under Article 10(2) of the India-US DTAA (15% withholding rate for $\ge 10\%$ voting stock).

---

### C. [`diagram3.mmd`](file:///e:/MNLU_sententia_AI/simulation_template_folder/diagram3.mmd) — Alternative Delaware Joint Venture (JV LLC) Model
* **Corresponding Document:** [`datalab-output-Project_Ananta_Structuring_Note.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/datalab-output-Project_Ananta_Structuring_Note.md) *(Section 8 & Section 11)*
* **Mapped Flow Details:**
  * **Delaware SPV:** `MGF` and `AEP` capitalize a joint Delaware entity: `Meridian-Atlas Education JV LLC` (`JV`).
  * **Unified FDI Tranche:** `JV` serves as the sole FDI conduit into both `PROP` and `OPCO`.
  * **Pooled Returns:** Dividends from `PROP` and `OPCO` flow up to `JV`, which distributes returns to `MGF` and `AEP` based on the JV Operating Agreement.

---

## 3. Related Precursor & Specification Documents

* **[`datalab-output-PRF India Structure Deck (1) (1).pdf.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/datalab-output-PRF%20India%20Structure%20Deck%20(1)%20(1).pdf.md):** The underlying real-world legal deck (*Project Rescue Foundation / Devaraj Educare / Jireh School*) from which Project Ananta was adapted.
* **[`datalab-output-Sententia AI PRD.md`](file:///e:/MNLU_sententia_AI/simulation_template_folder/datalab-output-Sententia%20AI%20PRD.md):** Defines Section 8.5 ("Visualization Layer") requirements for Sententia.ai to dynamically generate Mermaid diagrams (`diagram1.mmd`, `diagram2.mmd`, `diagram3.mmd`) from scenario inputs.
