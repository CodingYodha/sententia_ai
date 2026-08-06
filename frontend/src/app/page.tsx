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
    A["US PE Fund LP\\n[United States]"]
    B["Mauritius SPV\\n[Category 1 GBL]"]
    C["India Tech OpCo\\n[India - Private Limited]"]
    A -->|"100% Equity / Capital"| B
    B -->|"100% FDI / Compulsory Convertible Preference Shares"| C
    classDef originNode fill:#1e3a5f,stroke:#4a9eff,color:#fff,stroke-width:2px
    classDef spvNode fill:#3d2c5e,stroke:#a855f7,color:#fff,stroke-width:2px
    classDef targetNode fill:#1b4332,stroke:#40916c,color:#d8f3dc,stroke-width:2px
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
    <main className="min-h-screen flex flex-col items-center justify-between px-6 py-12 max-w-6xl mx-auto space-y-16">
      {/* ── Hero Header Section ── */}
      <section className="text-center pt-8 space-y-6 max-w-3xl">
        {/* Logo Icon */}
        <div
          className="mx-auto w-20 h-20 rounded-3xl flex items-center justify-center transition-transform hover:scale-105 duration-300"
          style={{
            background: "linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(168,85,247,0.1) 100%)",
            border: "1px solid rgba(129,140,248,0.35)",
            boxShadow: "0 0 50px rgba(99,102,241,0.25)",
          }}
        >
          <svg width="40" height="40" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M6 24L16 8L26 24" stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M9.5 19h13" stroke="#c084fc" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>

        <h1
          className="text-5xl sm:text-6xl font-extrabold tracking-tight"
          style={{
            background: "linear-gradient(135deg, #ffffff 20%, #c084fc 60%, #818cf8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Sententia.ai
        </h1>

        <p className="text-xl sm:text-2xl font-medium text-slate-300 leading-relaxed">
          AI-Powered Cross-Border Fund Structuring &amp; Regulatory Compliance Engine
        </p>

        <p className="text-sm sm:text-base text-slate-400 max-w-2xl mx-auto leading-normal">
          Automate legal entity architectures, evaluate multi-jurisdictional FDI, tax, and bilateral treaty constraints, and export audit-ready ownership diagrams.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 pt-4">
          <Link
            href="/intake"
            className="px-8 py-4 rounded-xl text-base font-semibold text-white transition-all duration-200 hover:shadow-lg flex items-center gap-2"
            style={{
              background: "linear-gradient(135deg, #6366f1 0%, #a855f7 100%)",
              boxShadow: "0 4px 20px rgba(99,102,241,0.4)",
            }}
          >
            <span>Start New Scenario</span>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <path d="M5 12h14M12 5l7 7-7 7" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </Link>

          <Link
            href="/review"
            className="px-8 py-4 rounded-xl text-base font-semibold transition-all duration-200"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.12)",
              color: "#e2e8f0",
            }}
          >
            Review Queue
          </Link>
        </div>
      </section>

      {/* ── Feature Highlights Grid ── */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full pt-4">
        <div
          className="p-6 rounded-2xl space-y-3 transition-all hover:translate-y-[-2px]"
          style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center text-indigo-400 font-bold">
            01
          </div>
          <h3 className="text-lg font-semibold text-slate-100">Multi-Jurisdiction Structuring</h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Generate ranked, compliant fund structures across US, EU, GIFT City, Singapore, Mauritius, and India corridors.
          </p>
        </div>

        <div
          className="p-6 rounded-2xl space-y-3 transition-all hover:translate-y-[-2px]"
          style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          <div className="w-10 h-10 rounded-xl bg-purple-500/20 flex items-center justify-center text-purple-400 font-bold">
            02
          </div>
          <h3 className="text-lg font-semibold text-slate-100">Deterministic Compliance Engine</h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Validate investments against FEMA NDI Rules, OECD BEPS MLI, DTAA protocols, and sectoral caps with cited legal authorities.
          </p>
        </div>

        <div
          className="p-6 rounded-2xl space-y-3 transition-all hover:translate-y-[-2px]"
          style={{
            background: "rgba(255,255,255,0.02)",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center text-emerald-400 font-bold">
            03
          </div>
          <h3 className="text-lg font-semibold text-slate-100">Audit-Ready Diagrams &amp; Review</h3>
          <p className="text-xs sm:text-sm text-slate-400 leading-relaxed">
            Interactive Mermaid ownership graphs with high-res PNG &amp; PDF export, plus expert-in-the-loop audit logging.
          </p>
        </div>
      </section>

      {/* ── Live Diagram Engine Demo ── */}
      <section className="w-full space-y-4 pt-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-100">Architecture Visualization Engine</h2>
            <p className="text-xs text-slate-400">Sample ownership flow with client-side PNG/PDF diagram rendering</p>
          </div>
          <span className="px-3 py-1 rounded-full text-xs font-mono bg-purple-500/10 border border-purple-500/30 text-purple-300">
            Interactive Preview
          </span>
        </div>

        {loadingDiagram ? (
          <div className="rounded-2xl p-12 flex items-center justify-center gap-3 bg-white/5 border border-white/10">
            <svg className="animate-spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <span className="text-sm text-indigo-300">Rendering ownership diagram…</span>
          </div>
        ) : diagram ? (
          <DiagramPanel diagram={diagram} isIllustrative={true} />
        ) : null}
      </section>

      {/* ── Footer ── */}
      <footer className="w-full text-center border-t border-white/5 pt-8 pb-4 text-xs text-slate-500">
        Sententia.ai · AI Cross-Border Fund Structuring Platform · Multi-Jurisdictional Compliance Engine
      </footer>
    </main>
  );
}
