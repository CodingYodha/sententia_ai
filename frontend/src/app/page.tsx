"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { DiagramPanel, type DiagramData } from "./components/DiagramPanel";
import { apiDiagramGenerate } from "@/lib/api";

// ── Illustrative Demo Structure ──────────────────────────────────────────────
const DEMO_STRUCTURE = {
  rank: 1,
  name: "US PE Fund → Mauritius SPV → India OpCo (FDI Corridor)",
  structure_type: "spv_corridor",
  architecture_description: "Tax-efficient cross-border FDI vehicle utilizing Mauritius Category 1 Global Business License (GBL) for Indian portfolio investment under DTAA Amendment Article 13.",
  ownership_chain: "US LP Investors (100%) → US PE Fund LP → Mauritius SPV (100%) → India Tech OpCo",
  jurisdictions_involved: ["United States", "Mauritius", "India"],
  mermaid_diagram: `graph TD
    A["US PE Fund LP<br/><span style='font-size:11px;opacity:0.8;font-weight:normal'>[United States]</span>"]
    B["Mauritius SPV<br/><span style='font-size:11px;opacity:0.8;font-weight:normal'>[Category 1 GBL]</span>"]
    C["India Tech OpCo<br/><span style='font-size:11px;opacity:0.8;font-weight:normal'>[India - Private Limited]</span>"]
    A -->|"100% Equity / Capital"| B
    B -->|"100% FDI / CCPS"| C
    classDef originNode fill:#f5f5f4,stroke:#292524,color:#0c0a09,stroke-width:2px,rx:8px,ry:8px
    classDef spvNode fill:#f0fdf4,stroke:#16a34a,color:#14532d,stroke-width:2px,rx:8px,ry:8px
    classDef targetNode fill:#eff6ff,stroke:#2563eb,color:#1e3a8a,stroke-width:2px,rx:8px,ry:8px
    class A originNode
    class B spvNode
    class C targetNode`,
  compliance_touchpoints: [
    {
      jurisdiction: "India",
      requirement: "FEMA (Non-Debt Instruments) Rules 2019 — Form FC-GPR filing within 30 days of allotment.",
      timing: "post-issuance",
      authority: "Reserve Bank of India (RBI)",
    },
    {
      jurisdiction: "Mauritius",
      requirement: "FSC Substance Requirement — minimum annual expenditure & local management board.",
      timing: "ongoing",
      authority: "Financial Services Commission (FSC)",
    },
    {
      jurisdiction: "Bilateral",
      requirement: "India-Mauritius DTAA Principal Purpose Test (PPT) — BEPS Action 6 compliance.",
      timing: "structuring",
      authority: "CBDT / Income Tax Dept",
    },
  ],
  cited_sources: ["FEMA NDI Rules 2019", "India-Mauritius DTAA Protocol 2024", "OECD BEPS Action 6"],
  identified_risks: [
    "GAAR scrutiny if commercial substance in Mauritius is deemed insufficient.",
  ],
  rationale: "Optimizes capital deployment with established double taxation treaty benefits and clear FDI approval pathways.",
  estimated_setup_complexity: "medium",
  regulatory_confidence: "high",
};

export default function HomePage() {
  const [diagram, setDiagram] = useState<DiagramData | null>(null);
  const [loadingDiagram, setLoadingDiagram] = useState(false);

  useEffect(() => {
    async function loadDemoDiagram() {
      setLoadingDiagram(true);
      try {
        const data = await apiDiagramGenerate(DEMO_STRUCTURE);
        setDiagram(data);
      } catch {
        // Fallback to local rendering if API is sleeping
        setDiagram({
          mermaid_syntax: DEMO_STRUCTURE.mermaid_diagram,
          entity_count: 3,
          edge_count: 2,
          regulatory_checkpoint_count: 3,
          jurisdictions: DEMO_STRUCTURE.jurisdictions_involved,
          structure_name: DEMO_STRUCTURE.name,
          generation_warnings: [],
        });
      } finally {
        setLoadingDiagram(false);
      }
    }
    loadDemoDiagram();
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-between px-6 py-16 max-w-6xl mx-auto space-y-20 relative z-10">
      {/* ── Hero Header Section ── */}
      <section className="text-center pt-12 space-y-6 max-w-4xl relative">
        {/* Pastel Orb Backdrop behind hero */}
        <div
          className="absolute -top-12 left-1/2 -translate-x-1/2 w-96 h-96 rounded-full pointer-events-none -z-10"
          style={{
            background: "radial-gradient(circle, rgba(200,184,224,0.3) 0%, rgba(167,229,211,0.2) 45%, transparent 70%)",
            filter: "blur(60px)",
          }}
        />

        {/* Logo Badge Icon */}
        <div
          className="mx-auto w-16 h-16 rounded-full flex items-center justify-center transition-transform hover:scale-105 duration-300"
          style={{
            background: "#292524",
            boxShadow: "0 8px 24px rgba(0,0,0,0.12)",
          }}
        >
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M6 24L16 8L26 24" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M9.5 19h13" stroke="#f4c5a8" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>

        <h1 className="text-5xl sm:text-7xl font-editorial-display tracking-tight text-stone-900 leading-[1.06]">
          Sententia.ai
        </h1>

        <p className="text-xl sm:text-2xl font-editorial-body text-stone-700 max-w-2xl mx-auto leading-relaxed">
          AI-Powered Cross-Border Fund Structuring &amp; Regulatory Compliance Engine
        </p>

        <p className="text-sm sm:text-base font-editorial-body text-stone-500 max-w-2xl mx-auto leading-normal">
          Automate legal entity architectures, evaluate multi-jurisdictional FDI, tax, and bilateral treaty constraints, and export audit-ready ownership diagrams.
        </p>

        {/* CTA Buttons (Pill geometry from design.md) */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-6">
          <Link
            href="/intake"
            className="btn-primary"
          >
            <span>Start New Scenario</span>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </Link>

          <Link
            href="/review"
            className="btn-outline"
          >
            Review Queue
          </Link>
        </div>
      </section>

      {/* ── Feature Highlights Grid ── */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full pt-4">
        <div className="card-editorial p-7 space-y-3.5 hover:translate-y-[-2px]">
          <div className="w-9 h-9 rounded-full bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-800 font-mono text-xs font-semibold">
            01
          </div>
          <h3 className="text-lg font-editorial-display text-stone-900 font-normal">Multi-Jurisdiction Structuring</h3>
          <p className="text-sm font-editorial-body text-stone-600 leading-relaxed">
            Generate ranked, compliant fund structures across US, EU, GIFT City, Singapore, Mauritius, and India corridors.
          </p>
        </div>

        <div className="card-editorial p-7 space-y-3.5 hover:translate-y-[-2px]">
          <div className="w-9 h-9 rounded-full bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-800 font-mono text-xs font-semibold">
            02
          </div>
          <h3 className="text-lg font-editorial-display text-stone-900 font-normal">Deterministic Compliance Engine</h3>
          <p className="text-sm font-editorial-body text-stone-600 leading-relaxed">
            Validate investments against FEMA NDI Rules, OECD BEPS MLI, DTAA protocols, and sectoral caps with cited legal authorities.
          </p>
        </div>

        <div className="card-editorial p-7 space-y-3.5 hover:translate-y-[-2px]">
          <div className="w-9 h-9 rounded-full bg-stone-100 border border-stone-200 flex items-center justify-center text-stone-800 font-mono text-xs font-semibold">
            03
          </div>
          <h3 className="text-lg font-editorial-display text-stone-900 font-normal">Audit-Ready Diagrams &amp; Review</h3>
          <p className="text-sm font-editorial-body text-stone-600 leading-relaxed">
            Interactive Mermaid ownership graphs with high-res PNG &amp; PDF export, plus expert-in-the-loop audit logging.
          </p>
        </div>
      </section>

      {/* ── Live Diagram Engine Demo ── */}
      <section className="w-full space-y-5 pt-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-editorial-display text-stone-900">Architecture Visualization Engine</h2>
            <p className="text-xs font-editorial-body text-stone-500 mt-1">Sample ownership flow with client-side PNG/PDF diagram rendering</p>
          </div>
          <span className="badge-pill">
            Interactive Preview
          </span>
        </div>

        {loadingDiagram ? (
          <div className="card-editorial p-12 flex items-center justify-center gap-3">
            <svg className="animate-spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#292524" strokeWidth="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <span className="text-sm font-editorial-body text-stone-600">Rendering ownership diagram…</span>
          </div>
        ) : diagram ? (
          <DiagramPanel diagram={diagram} isIllustrative={true} />
        ) : null}
      </section>

      {/* ── Editorial Footer ── */}
      <footer className="w-full text-center border-t border-stone-200 pt-10 pb-6 text-xs font-editorial-body text-stone-500">
        Sententia.ai · AI Cross-Border Fund Structuring Platform · Multi-Jurisdictional Compliance Engine
      </footer>
    </main>
  );
}
