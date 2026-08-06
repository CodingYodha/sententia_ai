"use client";

/**
 * Results page — Displays 2-4 generated structuring alternatives side-by-side
 * (PRD FR-3.5). Reads generation output from sessionStorage, runs compliance
 * evaluation per alternative, and renders StructureCard with banners.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { StructureCard, type StructuringAlternative, type ComplianceResult } from "../components/StructureCard";
import { ComplianceBanner } from "../components/ComplianceBanner";
import { DisclaimerBanner } from "../components/DisclaimerBanner";
import { AuthGuard } from "../components/AuthGuard";
import { useAuth } from "../components/AuthContext";

import { apiComplianceEvaluate, apiStructuresGenerate } from "@/lib/api";

interface StoredResults {
  scenarioId: string;
  scenario: Record<string, unknown>;
  alternatives: StructuringAlternative[];
  general_analysis: string;
  recommended_alternative_rank: number;
  disclaimer: string;
  rag_sources_used: number;
  llm_provider_used: string;
  rag_corpus_coverage: string;
  generation_time_ms?: number;
}

export default function ResultsPage() {
  const router = useRouter();
  const { accessToken } = useAuth();

  const [results, setResults]                 = useState<StoredResults | null>(null);
  const [complianceMap, setComplianceMap]     = useState<Record<number, ComplianceResult>>({});
  const [complianceLoading, setCompLoading]   = useState(false);
  const [loadError, setLoadError]             = useState<string | null>(null);
  const [retrying, setRetrying]               = useState(false);
  const [retryError, setRetryError]           = useState<string | null>(null);

  // ── Read results from sessionStorage ────────────────────────────────────────
  useEffect(() => {
    const raw = sessionStorage.getItem("sententia_results");
    if (!raw) { setLoadError("No results found — please generate a scenario first."); return; }
    try {
      const parsed: StoredResults = JSON.parse(raw);
      setResults(parsed);
      evaluateCompliance(parsed);
    } catch {
      setLoadError("Failed to parse stored results.");
    }
  }, []);

  // ── Evaluate compliance for each alternative ─────────────────────────────────
  async function evaluateCompliance(data: StoredResults) {
    setCompLoading(true);
    const map: Record<number, ComplianceResult> = {};

    await Promise.all(
      data.alternatives.map(async (alt) => {
        try {
          const res = await apiComplianceEvaluate(data.scenario, alt);
          map[alt.rank] = res;
        } catch {
          // Non-fatal: compliance result just won't show
        }
      })
    );

    setComplianceMap(map);
    setCompLoading(false);
  }

  async function retryGeneration() {
    if (!results) return;
    setRetrying(true);
    setRetryError(null);
    try {
      const genData = await apiStructuresGenerate(results.scenario, 3, accessToken);
      const nextResults = {
        scenarioId: results.scenarioId,
        scenario: results.scenario,
        ...genData,
      };
      sessionStorage.setItem("sententia_results", JSON.stringify(nextResults));
      setResults(nextResults);
      setComplianceMap({});
      await evaluateCompliance(nextResults);
    } catch (e) {
      setRetryError(e instanceof Error ? e.message : "Retry failed");
    } finally {
      setRetrying(false);
    }
  }

  // ── Loading / error states ────────────────────────────────────────────────────
  if (loadError) {
    return (
      <div className="min-h-screen pt-24 flex flex-col items-center justify-center px-4">
        <div
          className="max-w-md w-full rounded-2xl p-8 text-center"
          style={{ background: "rgba(248,113,113,0.06)", border: "1px solid rgba(248,113,113,0.2)" }}
        >
          <p className="text-base font-semibold mb-2" style={{ color: "#f87171" }}>No Results</p>
          <p className="text-sm mb-6" style={{ color: "#fca5a5" }}>{loadError}</p>
          <button
            onClick={() => router.push("/intake")}
            className="px-5 py-2.5 rounded-xl text-sm font-medium"
            style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8", cursor: "pointer" }}
          >
            ← New Scenario
          </button>
        </div>
      </div>
    );
  }

  if (!results) {
    return (
      <div className="min-h-screen pt-24 flex items-center justify-center">
        <div className="flex items-center gap-3" style={{ color: "#818cf8" }}>
          <svg className="animate-spin" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
          </svg>
          <span className="text-sm">Loading results…</span>
        </div>
      </div>
    );
  }

  const hasAnyIllustrative = Object.values(complianceMap).some((c) => !c.is_rule_validated);
  const hasAnyBlocked      = Object.values(complianceMap).some((c) => c.is_rule_validated && !c.is_allowed);
  const isIllustrative     = results.llm_provider_used === "illustrative" || results.llm_provider_used === "degraded_fallback" || results.llm_provider_used === "none";

  // Human-readable provider label
  const providerLabel = isIllustrative
    ? "Illustrative"
    : results.llm_provider_used.replace(/_/g, " ").replace("groq ", "").replace("openrouter ", "");

  return (
    <div className="min-h-screen pt-22 pb-16">
      {/* ── Page header ── */}
      <div
        className="px-6 py-5"
        style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", background: "rgba(255,255,255,0.01)" }}
      >
        <div className="max-w-screen-xl mx-auto">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <button
                  onClick={() => router.push("/intake")}
                  className="text-xs px-2.5 py-1 rounded-lg"
                  style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#64748b", cursor: "pointer" }}
                >
                  ← New Scenario
                </button>
                <span className="text-xs font-mono" style={{ color: "#475569" }}>
                  ID: {results.scenarioId?.slice(0, 8)}…
                </span>
              </div>
              <h1 className="text-2xl font-bold" style={{ color: "#f1f1f8" }}>
                Structuring Alternatives
              </h1>
              <p className="text-sm mt-1" style={{ color: "#64748b" }}>
                {results.alternatives.length} alternatives ·{" "}
                <span style={{ color: isIllustrative ? "#f59e0b" : "#34d399" }}>
                  {isIllustrative ? "⚡ Illustrative" : `⚡ ${providerLabel}`}
                </span>
                {" "}· {results.rag_sources_used} RAG sources · {results.rag_corpus_coverage} coverage
              </p>
            </div>

            {/* Meta badges */}
            <div className="flex items-center gap-2 flex-wrap">
              {complianceLoading && (
                <span className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full" style={{ background: "rgba(99,102,241,0.1)", color: "#818cf8" }}>
                  <svg className="animate-spin" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                    <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                  </svg>
                  Evaluating compliance…
                </span>
              )}
              {results.generation_time_ms && (
                <span className="text-xs px-3 py-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.04)", color: "#64748b" }}>
                  ⚡ {(results.generation_time_ms / 1000).toFixed(1)}s
                </span>
              )}
            </div>
          </div>

          {/* General analysis — only show for real LLM generations */}
          {!isIllustrative && results.general_analysis && (
            <div className="mt-4 max-w-3xl">
              <p className="text-sm leading-relaxed" style={{ color: "#94a3b8" }}>
                {results.general_analysis}
              </p>
            </div>
          )}

          {/* Page-level banners */}
          <div className="mt-4 space-y-3">
            {isIllustrative && (
              <div
                className="flex items-start gap-3 rounded-xl px-4 py-3 text-sm"
                style={{ background: "rgba(245,158,11,0.07)", border: "1px solid rgba(245,158,11,0.2)" }}
              >
                <span style={{ color: "#f59e0b", fontSize: "16px", lineHeight: 1.4 }}>⚡</span>
                <div>
                  <p className="font-semibold mb-0.5" style={{ color: "#fbbf24" }}>Illustrative Structures</p>
                  <p style={{ color: "#94a3b8" }}>
                    These alternatives are based on general cross-border FDI patterns.
                    For AI-powered analysis tailored to your specific corridor, please retry the scenario.
                    Always verify with qualified local counsel before acting.
                  </p>
                </div>
              </div>
            )}
            {hasAnyIllustrative && !isIllustrative && (
              <ComplianceBanner
                type="WARNING"
                label="Compliance evaluated via AI — not hard-coded policy rules"
                message="Compliance analysis used AI reasoning rather than deterministic Rego rules. Treat as guidance only. Always verify with qualified local counsel before making any investment or structuring decision."
              />
            )}
            {hasAnyBlocked && (
              <ComplianceBanner
                type="BLOCKED"
                label="One or more structures have compliance blocks"
                message="At least one alternative was blocked by deterministic Rego policy rules. Review the specific violations in the Compliance tab of the affected card."
              />
            )}
          </div>
        </div>
      </div>

      {/* ── Structure cards — side-by-side (FR-3.5) ── */}
      <div className="px-4 pt-6 pb-4 max-w-screen-xl mx-auto">
        <div
          className="grid gap-5"
          style={{
            gridTemplateColumns: `repeat(${Math.min(results.alternatives.length, 3)}, minmax(0, 1fr))`,
          }}
        >
          {results.alternatives.map((alt) => (
            <StructureCard
              key={alt.rank}
              alternative={alt}
              complianceResult={complianceMap[alt.rank]}
              scenarioId={results.scenarioId}
              isRecommended={alt.rank === results.recommended_alternative_rank}
            />
          ))}
        </div>

        {/* FR-6.4: Disclaimer — must appear on every output view */}
        <DisclaimerBanner className="mt-6 rounded-xl" />
      </div>
    </div>
  );
}
