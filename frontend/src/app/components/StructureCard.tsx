"use client";

/**
 * StructureCard — Displays one StructuringAlternative with:
 *   - Tabbed interface: Overview | Diagram | Compliance | Risks
 *   - Embedded Mermaid diagram with export
 *   - Compliance banner (amber/green/red) based on is_rule_validated + is_allowed
 *   - Compliance touchpoints with timing badges
 *   - Risk severity grid
 *   - Review actions (reviewer/admin only)
 *   - Expert-validated / In-review badge (FR-6.2)
 */

import { useCallback, useEffect, useState } from "react";
import { ComplianceBanner, CompliancePill } from "./ComplianceBanner";
import { DiagramPanel, type DiagramData } from "./DiagramPanel";
import { ReviewActions, ReviewStatusBadge, type ReviewStatus } from "./ReviewActions";
import { useRole } from "./RBACContext";

import { apiDiagramGenerate } from "@/lib/api";

// ── Types pulled from backend schemas ─────────────────────────────────────────

interface ComplianceTouchpoint {
  jurisdiction: string;
  requirement: string;
  timing: string;
  authority: string;
  notes?: string;
}

interface IdentifiedRisk {
  risk_type: string;
  description: string;
  severity: "high" | "medium" | "low";
  mitigation: string;
}

export interface ImplementationStep {
  step_number: number;
  phase: string;
  title: string;
  description: string;
  key_deliverables: string[];
  estimated_timeline: string;
}

export interface StructuringAlternative {
  rank: number;
  name: string;
  structure_type: string;
  architecture_description: string;
  ownership_chain: string;
  jurisdictions_involved: string[];
  mermaid_diagram: string;
  compliance_touchpoints: ComplianceTouchpoint[];
  cited_sources: string[];
  identified_risks: IdentifiedRisk[];
  implementation_steps?: ImplementationStep[];
  rationale: string;
  estimated_setup_complexity: "low" | "medium" | "high";
  regulatory_confidence: "high" | "medium" | "low";
}

export interface ComplianceResult {
  is_rule_validated: boolean;
  is_allowed?: boolean;
  corridor_id?: string;
  violations?: string[];
  ui_banner?: { type: string; label: string; message: string };
  general_analysis?: string;
  risk_summary?: string;
  overall_confidence?: string;
  compliance_score?: number;
  rules_checked?: number;
  required_filings?: string[];
  blocking_issues?: any[];
  warning_issues?: any[];
  jurisdiction_breakdown?: any[];
}



// ── Sub-components ────────────────────────────────────────────────────────────

const TIMING_COLORS: Record<string, { bg: string; color: string }> = {
  "pre-signing":  { bg: "rgba(129,140,248,0.12)", color: "#818cf8" },
  "pre-closing":  { bg: "rgba(99,102,241,0.1)",   color: "#6366f1" },
  "at-closing":   { bg: "rgba(52,211,153,0.1)",   color: "#34d399" },
  "post-closing": { bg: "rgba(148,163,184,0.1)",  color: "#94a3b8" },
  "ongoing":      { bg: "rgba(100,116,139,0.1)",  color: "#64748b" },
};

const SEVERITY_CFG: Record<string, { bg: string; color: string; label: string }> = {
  high:   { bg: "rgba(248,113,113,0.1)", color: "#f87171", label: "High"   },
  medium: { bg: "rgba(245,158,11,0.1)",  color: "#f59e0b", label: "Medium" },
  low:    { bg: "rgba(52,211,153,0.1)",  color: "#34d399", label: "Low"    },
};

const COMPLEXITY_CFG = {
  low:    { color: "#34d399", label: "Low complexity"    },
  medium: { color: "#f59e0b", label: "Medium complexity" },
  high:   { color: "#f87171", label: "High complexity"   },
};

const CONFIDENCE_CFG = {
  high:   { color: "#34d399", label: "High confidence"   },
  medium: { color: "#f59e0b", label: "Medium confidence" },
  low:    { color: "#f87171", label: "Low confidence"    },
};

type Tab = "overview" | "diagram" | "compliance" | "risks" | "steps";

// ── Main component ────────────────────────────────────────────────────────────

interface StructureCardProps {
  alternative: StructuringAlternative;
  complianceResult?: ComplianceResult;
  scenarioId?: string;
  isRecommended?: boolean;
}

export function StructureCard({
  alternative,
  complianceResult,
  scenarioId,
  isRecommended,
}: StructureCardProps) {
  const { can, role } = useRole();
  const [tab, setTab]         = useState<Tab>("overview");
  const [diagram, setDiagram] = useState<DiagramData | null>(null);
  const [diagLoading, setDL]  = useState(false);
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>("pending");

  // Derive structure ID (deterministic from scenario + rank)
  const structureId = `${scenarioId ?? "demo"}-rank${alternative.rank}`;

  const isIllustrative = complianceResult ? !complianceResult.is_rule_validated : false;
  const bannerType = !complianceResult
    ? null
    : !complianceResult.is_rule_validated
    ? "WARNING"
    : complianceResult.is_allowed
    ? "VALIDATED"
    : "BLOCKED";

  // Lazy-load or initialize the diagram when the Diagram tab is first opened
  const loadDiagram = useCallback(async () => {
    if (diagram || diagLoading) return;

    if (alternative.mermaid_diagram) {
      // Clean frontmatter & normalize non-standard dotted syntax
      const cleanSyntax = alternative.mermaid_diagram
        .replace(/^---[\s\S]*?---\s*/, '')
        .replace(/-\.\s*"([^"]+)"\s*\.-\s*>/g, '-.-|"$1"|')
        .replace(/-\.\s*"([^"]+)"\s*\.->/g, '-.-|"$1"|')
        .trim();

      setDiagram({
        mermaid_syntax: cleanSyntax,
        entity_count: 5,
        edge_count: 4,
        regulatory_checkpoint_count: alternative.compliance_touchpoints?.length || 0,
        jurisdictions: alternative.jurisdictions_involved || [],
        structure_name: alternative.name,
        generation_warnings: [],
      });
      return;
    }

    setDL(true);
    try {
      const data = await apiDiagramGenerate(alternative);
      setDiagram(data);
    } catch {
      /* diagram will just not render */
    } finally {
      setDL(false);
    }
  }, [alternative, diagram, diagLoading]);


  useEffect(() => {
    if (tab === "diagram") loadDiagram();
  }, [tab, loadDiagram]);

  const tabs: { id: Tab; label: string; count?: number }[] = [
    { id: "overview",   label: "Overview" },
    { id: "diagram",    label: "Diagram" },
    { id: "compliance", label: "Compliance", count: alternative.compliance_touchpoints.length },
    { id: "risks",      label: "Risks",      count: alternative.identified_risks.length },
    { id: "steps",      label: "Steps",      count: alternative.implementation_steps?.length || 0 },
  ];

  return (
    <div
      className="card-editorial flex flex-col overflow-hidden w-full"
      style={{
        border:      isRecommended ? "2px solid #292524" : "1px solid #e7e5e4",
        boxShadow:   isRecommended ? "0 8px 28px rgba(0,0,0,0.08)" : "0 4px 16px rgba(0,0,0,0.03)",
        minWidth:    0,
      }}
    >
      {/* ── Card header ── */}
      <div
        className="px-6 py-5"
        style={{ borderBottom: "1px solid #e7e5e4", background: "rgba(250,250,250,0.6)" }}
      >
        {/* Rank + recommended badge */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className="inline-flex items-center justify-center w-7 h-7 rounded-full text-xs font-bold"
              style={{ background: "#292524", color: "#ffffff" }}
            >
              #{alternative.rank}
            </span>
            {isRecommended && (
              <span
                className="badge-pill bg-stone-900 text-white border-stone-900"
              >
                ★ Recommended
              </span>
            )}
            {/* FR-6.2: expert-validated vs in-review badge */}
            <ReviewStatusBadge status={reviewStatus} />
          </div>
          <div className="flex items-center gap-2 flex-wrap shrink-0">
            {complianceResult && (
              <CompliancePill
                isRuleValidated={complianceResult.is_rule_validated}
                isAllowed={complianceResult.is_allowed}
              />
            )}
            <span className="text-xs font-semibold" style={{ color: COMPLEXITY_CFG[alternative.estimated_setup_complexity].color }}>
              {COMPLEXITY_CFG[alternative.estimated_setup_complexity].label}
            </span>
          </div>
        </div>

        <h3 className="text-lg font-editorial-display font-medium leading-tight mb-1 text-stone-900">
          {alternative.name}
        </h3>
        <p className="text-xs font-mono text-stone-500">
          {alternative.ownership_chain}
        </p>

        {/* Jurisdiction pills */}
        <div className="flex flex-wrap gap-1.5 mt-3">
          {alternative.jurisdictions_involved.map((j) => (
            <span
              key={j}
              className="badge-pill"
            >
              {j}
            </span>
          ))}
        </div>
      </div>

      {/* ── Compliance banner (full-width, unmissable) ── */}
      {bannerType && (
        <div className="px-6 pt-4">
          <ComplianceBanner
            type={bannerType as "WARNING" | "VALIDATED" | "BLOCKED"}
            label={complianceResult?.ui_banner?.label}
            message={complianceResult?.ui_banner?.message}
          />
        </div>
      )}

      {/* ── Tabs ── */}
      <div
        className="flex border-b px-6 pt-4 gap-1.5 bg-stone-50/50"
        style={{ borderColor: "#e7e5e4" }}
      >
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-medium rounded-t-xl transition-all"
            style={{
              color:      tab === t.id ? "#0c0a09" : "#777169",
              background: tab === t.id ? "#ffffff" : "transparent",
              borderBottom: tab === t.id ? "2px solid #0c0a09" : "2px solid transparent",
              fontWeight: tab === t.id ? 600 : 500,
              marginBottom: "-1px",
            }}
          >
            {t.label}
            {t.count !== undefined && (
              <span
                className="px-1.5 py-0.5 rounded-full text-[10px] font-bold"
                style={{
                  background: tab === t.id ? "#f0efed" : "#e7e5e4",
                  color:      tab === t.id ? "#0c0a09" : "#777169",
                }}
              >
                {t.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── Tab content ── */}
      <div className="flex-1 p-6 overflow-auto bg-white">

        {/* OVERVIEW */}
        {tab === "overview" && (
          <div className="space-y-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest mb-1.5 text-stone-500">Architecture</p>
              <p className="text-sm font-editorial-body text-stone-800 leading-relaxed">
                {alternative.architecture_description}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest mb-1.5 text-stone-500">Rationale</p>
              <p className="text-sm font-editorial-body text-stone-700 leading-relaxed">
                {alternative.rationale}
              </p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest mb-1.5 text-stone-500">Cited Sources</p>
              <ul className="space-y-1">
                {alternative.cited_sources.map((s, i) => (
                  <li key={i} className="flex items-center gap-2 text-sm font-editorial-body text-stone-700">
                    <span className="text-stone-400 font-bold">›</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex items-center gap-6 pt-3 border-t border-stone-100">
              <div>
                <p className="text-xs text-stone-500">Setup complexity</p>
                <p className="text-sm font-semibold" style={{ color: COMPLEXITY_CFG[alternative.estimated_setup_complexity].color }}>
                  {COMPLEXITY_CFG[alternative.estimated_setup_complexity].label}
                </p>
              </div>
              <div>
                <p className="text-xs text-stone-500">Regulatory confidence</p>
                <p className="text-sm font-semibold" style={{ color: CONFIDENCE_CFG[alternative.regulatory_confidence].color }}>
                  {CONFIDENCE_CFG[alternative.regulatory_confidence].label}
                </p>
              </div>
            </div>
          </div>
        )}

        {/* DIAGRAM */}
        {tab === "diagram" && (
          <div>
            {diagLoading && (
              <div className="flex items-center gap-3 py-8 justify-center text-stone-700">
                <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                </svg>
                <span className="text-sm font-editorial-body">Generating diagram…</span>
              </div>
            )}
            {diagram && !diagLoading && (
              <DiagramPanel diagram={diagram} isIllustrative={isIllustrative} />
            )}
            {!diagram && !diagLoading && (
              <button
                onClick={loadDiagram}
                className="w-full py-8 rounded-2xl text-sm btn-outline justify-center border-dashed"
              >
                ↺ Load Diagram
              </button>
            )}
          </div>
        )}

        {/* COMPLIANCE */}
        {tab === "compliance" && (
          <div className="space-y-3">
            {alternative.compliance_touchpoints.map((tp, i) => {
              const tc = TIMING_COLORS[tp.timing] ?? TIMING_COLORS["ongoing"];
              return (
                <div
                  key={i}
                  className="rounded-xl p-4 bg-stone-50 border border-stone-200"
                >
                  <div className="flex items-start justify-between gap-3 mb-2">
                    <span className="text-sm font-semibold text-stone-900">{tp.authority}</span>
                    <div className="flex items-center gap-2 shrink-0">
                      <span
                        className="px-2.5 py-0.5 rounded-full text-xs font-medium"
                        style={{ background: "#f0efed", color: "#292524" }}
                      >
                        {tp.timing}
                      </span>
                      <span className="badge-pill">
                        {tp.jurisdiction}
                      </span>
                    </div>
                  </div>
                  <p className="text-sm font-editorial-body text-stone-700">{tp.requirement}</p>
                  {tp.notes && (
                    <p className="text-xs mt-2 text-stone-500 font-editorial-body">{tp.notes}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* RISKS */}
        {tab === "risks" && (
          <div className="space-y-3">
            {alternative.identified_risks.map((risk, i) => {
              const sc = SEVERITY_CFG[risk.severity];
              return (
                <div
                  key={i}
                  className="rounded-xl p-4 bg-stone-50 border border-stone-200"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className="px-2.5 py-0.5 rounded-full text-xs font-semibold"
                      style={{ background: sc.bg, color: sc.color }}
                    >
                      {sc.label}
                    </span>
                    <span className="text-xs capitalize text-stone-500">
                      {risk.risk_type.replace("_", " ")}
                    </span>
                  </div>
                  <p className="text-sm font-editorial-body text-stone-800 mb-2">{risk.description}</p>
                  <div className="flex items-start gap-2 px-3 py-2 rounded-lg bg-emerald-50 border border-emerald-200">
                    <span className="text-emerald-700 text-xs font-bold">→</span>
                    <p className="text-xs font-editorial-body text-emerald-900">{risk.mitigation}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* IMPLEMENTATION STEPS */}
        {tab === "steps" && (
          <div className="space-y-3">
            {alternative.implementation_steps && alternative.implementation_steps.length > 0 ? (
              alternative.implementation_steps.map((step, i) => (
                <div
                  key={i}
                  className="rounded-xl p-4 bg-stone-50 border border-stone-200"
                >
                  <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold bg-stone-900 text-white">
                        #{step.step_number}
                      </span>
                      <span className="text-xs font-semibold uppercase tracking-wider text-stone-600">
                        {step.phase}
                      </span>
                    </div>
                    <span className="badge-pill">
                      🕒 {step.estimated_timeline}
                    </span>
                  </div>

                  <h4 className="text-sm font-semibold mb-1 text-stone-900">
                    {step.title}
                  </h4>

                  <p className="text-sm font-editorial-body text-stone-700 leading-relaxed mb-3">
                    {step.description}
                  </p>

                  {step.key_deliverables && step.key_deliverables.length > 0 && (
                    <div>
                      <p className="text-[11px] font-semibold uppercase tracking-wider mb-1.5 text-stone-500">
                        Key Deliverables &amp; Filings
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        {step.key_deliverables.map((d, j) => (
                          <span
                            key={j}
                            className="px-2.5 py-1 rounded-lg text-xs bg-white text-stone-700 border border-stone-200 flex items-center gap-1.5"
                          >
                            <span className="text-stone-500">📄</span> {d}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p className="text-sm py-4 text-center text-stone-500 font-editorial-body">
                No implementation steps available for this structure.
              </p>
            )}
          </div>
        )}
      </div>

      {/* ── Reviewer action strip (FR-6.2, role-gated) ── */}
      {can("review:write") && (
        <div
          className="px-6 py-4 bg-stone-50"
          style={{ borderTop: "1px solid #e7e5e4" }}
        >
          <p className="text-xs font-semibold uppercase tracking-widest mb-3 text-stone-500">
            Reviewer Decision
          </p>
          <ReviewActions
            structureId={structureId}
            scenarioId={scenarioId}
            alternativeRank={alternative.rank}
            structureName={alternative.name}
            reviewerRole={role}
            onActionComplete={setReviewStatus}
          />
        </div>
      )}
    </div>
  );
}
