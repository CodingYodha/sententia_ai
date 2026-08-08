"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { DiagramPanel, type DiagramData } from "./components/DiagramPanel";
import { apiDiagramGenerate } from "@/lib/api";

const DEMO_STRUCTURE = {
  rank: 1,
  name: "PropCo–OpCo Dual Vehicle Structure (Project Ananta)",
  structure_type: "spv_layered",
  architecture_description: "FDI-compliant K-12 school structuring: for-profit PropCo leases campus real estate to non-profit school trust, and for-profit OpCo provides educational services.",
  ownership_chain: "USA Investors (MGF/AEP) → Indian WOS (PropCo & OpCo) → Ananta Education Trust",
  jurisdictions_involved: ["United States", "India"],
  mermaid_diagram: `flowchart TB
    subgraph USA
    direction LR
    MGF["Meridian Grace<br/>Foundation (MGF)"]
    AEP["Atlas Education<br/>Partners LLC (AEP)"]
    MGF -.-> AEP
    end

    subgraph INDIA
    direction TB
    PROP["Meridian Campus<br/>Infrastructure Pvt. Ltd.<br/>('PropCo')"]
    OPCO["Ananta Educare<br/>Pvt. Ltd.<br/>('OpCo')"]
    AET["Ananta Education Trust<br/>('AET')"]
    SCHOOL(("Ananta International School"))
    PROP -->|"Registered Lease Deed"| AET
    OPCO -->|"Management Agreement"| AET
    AET -.-> SCHOOL
    end

    MGF -->|"FDI: Equity + CCPS"| PROP
    AEP -->|"FDI: Equity Shares"| OPCO`,
  compliance_touchpoints: [
    {
      jurisdiction: "India",
      requirement: "FEMA NDI Rules Schedule I — Real Estate Lease Rental Exemption",
      timing: "structuring",
      authority: "DPIIT / RBI",
    },
    {
      jurisdiction: "India",
      requirement: "CBSE Affiliation Bye-Laws — Non-Profit Mandate",
      timing: "pre-closing",
      authority: "CBSE",
    },
    {
      jurisdiction: "Bilateral",
      requirement: "India-US DTAA Article 10 — 15% Dividend Rate",
      timing: "repatriation",
      authority: "CBDT / IRS",
    },
  ],
  cited_sources: ["FEMA NDI Rules 2019", "CBSE Bye-Laws", "Modern Dental College (2016)", "Islamic Academy (2003)"],
  identified_risks: ["GAAR scrutiny on arm's-length rent rates"],
  rationale: "Optimizes cross-border capital deployment into Indian education sector while isolating non-profit school operating entity.",
  estimated_setup_complexity: "medium",
  regulatory_confidence: "high",
};

export default function HomePage() {
  const [diagram, setDiagram] = useState<DiagramData | null>(null);

  useEffect(() => {
    const cleanSyntax = DEMO_STRUCTURE.mermaid_diagram
      .replace(/^---[\s\S]*?---\s*/, '')
      .replace(/-\.\s*"([^"]+)"\s*\.-\s*>/g, '-.-|"$1"|')
      .replace(/-\.\s*"([^"]+)"\s*\.->/g, '-.-|"$1"|')
      .trim();

    setDiagram({
      mermaid_syntax: cleanSyntax,
      entity_count: 5,
      edge_count: 4,
      regulatory_checkpoint_count: 3,
      jurisdictions: DEMO_STRUCTURE.jurisdictions_involved,
      structure_name: DEMO_STRUCTURE.name,
      generation_warnings: [],
    });
  }, []);


  return (
    <main className="min-h-screen flex flex-col items-center justify-between px-6 py-12 max-w-6xl mx-auto space-y-16 relative z-10">
      {/* Hero Header Section */}
      <section className="text-center pt-8 space-y-4 max-w-4xl relative">
        <h1 className="text-5xl sm:text-7xl font-editorial-display tracking-tight text-stone-900 leading-tight">
          Sententia.ai
        </h1>

        <p className="text-lg font-serif italic text-stone-600 font-normal tracking-wide">
          Transactional Thinking, Done Right.
        </p>

        <div className="pt-6 space-y-3">
          <h2 className="text-2xl sm:text-3xl font-editorial-display text-stone-900 font-semibold max-w-3xl mx-auto leading-snug">
            AI-Powered Cross-Border Fund Structuring &amp; Regulatory Compliance Engine
          </h2>
          <p className="text-sm sm:text-base font-editorial-body text-stone-600 max-w-2xl mx-auto leading-relaxed">
            Automate legal entity architectures, evaluate multi-jurisdictional FDI, tax, and bilateral treaty constraints, and export audit-ready ownership diagrams.
          </p>
        </div>

        {/* CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-6">
          <Link href="/intake" className="btn-primary">
            <span>Start New Scenario</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </Link>

          <Link href="/review" className="btn-outline">
            Review Queue
          </Link>
        </div>
      </section>

      {/* 3 Feature Cards matching Image 1 */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full">
        <div className="card-editorial p-7 space-y-4 bg-white border border-stone-200 rounded-2xl shadow-sm hover:shadow-md transition-all">
          <div className="w-10 h-10 rounded-xl bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-800">
            🏛️
          </div>
          <h3 className="text-lg font-editorial-display text-stone-900 font-semibold">Multi-Jurisdiction Structuring</h3>
          <p className="text-sm font-editorial-body text-stone-600 leading-relaxed">
            Transaction to compose funding capacity allocations with structured corporate entities and legal structures.
          </p>
        </div>

        <div className="card-editorial p-7 space-y-4 bg-white border border-stone-200 rounded-2xl shadow-sm hover:shadow-md transition-all">
          <div className="w-10 h-10 rounded-xl bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-800">
            ⚙️
          </div>
          <h3 className="text-lg font-editorial-display text-stone-900 font-semibold">Deterministic Compliance Engine</h3>
          <p className="text-sm font-editorial-body text-stone-600 leading-relaxed">
            Deterministic compliance engine to evaluate and cross-reference regulatory policy constraints.
          </p>
        </div>

        <div className="card-editorial p-7 space-y-4 bg-white border border-stone-200 rounded-2xl shadow-sm hover:shadow-md transition-all">
          <div className="w-10 h-10 rounded-xl bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-800">
            👤
          </div>
          <h3 className="text-lg font-editorial-display text-stone-900 font-semibold">Audit-Ready Diagrams &amp; Review</h3>
          <p className="text-sm font-editorial-body text-stone-600 leading-relaxed">
            Develop grand audit or cross-word compliance diagrams, and instantly render professional diagrams.
          </p>
        </div>
      </section>

      {/* Interactive Diagram Demo */}
      <section className="w-full space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-editorial-display text-stone-900 font-semibold">Sample Deal Architecture</h2>
          <span className="badge-pill bg-stone-100 text-stone-700 text-xs px-3 py-1 font-mono">
            Interactive Preview
          </span>
        </div>
        {diagram && <DiagramPanel diagram={diagram} isIllustrative={true} />}
      </section>

      {/* Footer */}
      <footer className="w-full text-center border-t border-stone-200 pt-8 pb-4 text-xs font-editorial-body text-stone-500">
        Sententia.ai · AI Cross-Border Fund Structuring Platform · Transactional Thinking, Done Right.
      </footer>
    </main>
  );
}
