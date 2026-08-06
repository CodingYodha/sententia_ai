"use client";

import { useEffect, useState } from "react";
import { DiagramPanel, type DiagramData } from "./components/DiagramPanel";

// ─── Types ────────────────────────────────────────────────────────────────────
interface ServiceStatus {
  status: "ok" | "error";
  latency_ms: number | null;
}

interface HealthData {
  status: "ok" | "degraded";
  version: string;
  timestamp: string;
  services: {
    supabase: ServiceStatus;
    qdrant: ServiceStatus;
  };
}

type FetchState = "idle" | "loading" | "success" | "error";

// ─── Constants ────────────────────────────────────────────────────────────────
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ─── Sub-components ───────────────────────────────────────────────────────────
function StatusDot({ status }: { status: "ok" | "error" | "loading" }) {
  const colors: Record<string, string> = {
    ok:      "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.6)]",
    error:   "bg-red-400    shadow-[0_0_8px_rgba(248,113,113,0.6)]",
    loading: "bg-amber-400  shadow-[0_0_8px_rgba(251,191,36,0.6)]  animate-pulse",
  };
  return (
    <span
      className={`inline-block w-2.5 h-2.5 rounded-full ${colors[status]}`}
      aria-label={status}
    />
  );
}

function ServiceCard({
  name,
  service,
  loading,
}: {
  name: string;
  service?: ServiceStatus;
  loading: boolean;
}) {
  const status = loading ? "loading" : (service?.status ?? "error");
  return (
    <div
      className="flex items-center justify-between px-4 py-3 rounded-xl"
      style={{
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.07)",
      }}
    >
      <div className="flex items-center gap-3">
        <StatusDot status={status as "ok" | "error" | "loading"} />
        <span className="text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
          {name}
        </span>
      </div>
      {!loading && service && (
        <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
          {service.latency_ms !== null ? `${service.latency_ms} ms` : "—"}
        </span>
      )}
    </div>
  );
}

// ── Demo fixture (2-entity direct structure) shown when API is reachable ────
const DEMO_STRUCTURE = {
  rank: 1,
  name: "US PE Fund → Germany OpCo (Direct FDI)",
  structure_type: "direct_fdi",
  architecture_description: "Demo structure.",
  ownership_chain: "US PE Fund (100%) → Germany OpCo",
  jurisdictions_involved: ["United States", "Germany"],
  mermaid_diagram: `graph TD
    A["US PE Fund\\n[United States]"]
    B["Germany OpCo\\n[Germany]"]
    A -->|"Capital / 100% equity"| B
    classDef originNode fill:#1e3a5f,stroke:#4a9eff,color:#fff,stroke-width:2px
    classDef targetNode fill:#1b4332,stroke:#40916c,color:#d8f3dc,stroke-width:2px
    class A originNode
    class B targetNode`,
  compliance_touchpoints: [
    {
      jurisdiction: "Germany",
      requirement: "BAFA screening — acquisitions above 25% by non-EU acquirer",
      timing: "pre-signing",
      authority: "BAFA",
    },
  ],
  cited_sources: ["OECD MTC"],
  identified_risks: [],
  rationale: "Demo",
  estimated_setup_complexity: "low",
  regulatory_confidence: "medium",
};

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function HomePage() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [fetchState, setFetchState] = useState<FetchState>("idle");
  const [lastChecked, setLastChecked] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Diagram state
  const [diagram, setDiagram] = useState<DiagramData | null>(null);
  const [diagramState, setDiagramState] = useState<FetchState>("idle");
  const [diagramError, setDiagramError] = useState<string | null>(null);

  async function fetchDiagram() {
    setDiagramState("loading");
    setDiagramError(null);
    try {
      const res = await fetch(`${API_URL}/api/diagram/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ structure_json: DEMO_STRUCTURE }),
        cache: "no-store",
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: DiagramData = await res.json();
      setDiagram(data);
      setDiagramState("success");
    } catch (err) {
      setDiagramError(err instanceof Error ? err.message : "Diagram fetch failed");
      setDiagramState("error");
    }
  }

  async function checkHealth() {
    setFetchState("loading");
    setError(null);
    try {
      const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: HealthData = await res.json();
      setHealth(data);
      setFetchState("success");
      setLastChecked(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reach backend");
      setFetchState("error");
    }
  }

  useEffect(() => {
    checkHealth();
  }, []);

  // Fetch demo diagram once backend is confirmed healthy
  useEffect(() => {
    if (fetchState === "success" && diagramState === "idle") {
      fetchDiagram();
    }
  }, [fetchState, diagramState]);

  const isLoading = fetchState === "loading";
  const overallStatus = fetchState === "success" ? health?.status : fetchState === "error" ? "error" : "loading";

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-6 py-16">
      {/* ── Header ── */}
      <div className="text-center mb-16 space-y-4">
        {/* Logo mark */}
        <div
          className="mx-auto mb-6 w-16 h-16 rounded-2xl flex items-center justify-center"
          style={{
            background: "linear-gradient(135deg, rgba(99,102,241,0.2) 0%, rgba(99,102,241,0.05) 100%)",
            border: "1px solid rgba(99,102,241,0.3)",
            boxShadow: "var(--glow-brand)",
          }}
        >
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path d="M6 24L16 8L26 24" stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M9.5 19h13" stroke="#6366f1" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </div>

        <h1
          className="text-4xl font-bold tracking-tight"
          style={{
            background: "linear-gradient(135deg, #f1f1f8 30%, #818cf8 100%)",
            WebkitBackgroundClip: "text",
            WebkitTextFillColor: "transparent",
          }}
        >
          Sententia.ai
        </h1>
        <p className="text-lg max-w-md mx-auto" style={{ color: "var(--color-text-secondary)" }}>
          AI-powered cross-border fund structuring and compliance validation.
        </p>

        {/* Status badge */}
        <div className="flex justify-center mt-2">
          <span
            className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs font-medium"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.09)",
              color: "var(--color-text-muted)",
            }}
          >
            <StatusDot status={overallStatus as "ok" | "error" | "loading"} />
            {isLoading
              ? "Checking services…"
              : fetchState === "success"
              ? `Backend ${health?.status === "ok" ? "healthy" : "degraded"} · v${health?.version}`
              : "Backend unreachable"}
          </span>
        </div>
      </div>

      {/* ── Health Card ── */}
      <div
        className="w-full max-w-sm rounded-2xl p-6 space-y-3"
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid rgba(255,255,255,0.07)",
          boxShadow: "0 4px 40px rgba(0,0,0,0.4)",
        }}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-semibold uppercase tracking-widest" style={{ color: "var(--color-text-muted)" }}>
            Service Status
          </h2>
          {lastChecked && (
            <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
              {lastChecked}
            </span>
          )}
        </div>

        {/* API */}
        <div
          className="flex items-center justify-between px-4 py-3 rounded-xl"
          style={{
            background: "rgba(255,255,255,0.04)",
            border: "1px solid rgba(255,255,255,0.07)",
          }}
        >
          <div className="flex items-center gap-3">
            <StatusDot
              status={
                isLoading ? "loading"
                : fetchState === "success" ? "ok"
                : "error"
              }
            />
            <span className="text-sm font-medium" style={{ color: "var(--color-text-secondary)" }}>
              FastAPI backend
            </span>
          </div>
          <span className="text-xs" style={{ color: "var(--color-text-muted)" }}>
            {API_URL.replace("http://", "").replace("https://", "")}
          </span>
        </div>

        <ServiceCard
          name="Supabase (Postgres)"
          service={health?.services.supabase}
          loading={isLoading}
        />
        <ServiceCard
          name="Qdrant (vector DB)"
          service={health?.services.qdrant}
          loading={isLoading}
        />

        {/* Error message */}
        {fetchState === "error" && error && (
          <div
            className="mt-3 px-4 py-3 rounded-xl text-xs"
            style={{
              background: "rgba(248,113,113,0.08)",
              border: "1px solid rgba(248,113,113,0.2)",
              color: "var(--color-error)",
            }}
          >
            {error} — is the backend running on {API_URL}?
          </div>
        )}

        {/* Refresh button */}
        <button
          id="btn-refresh-health"
          onClick={checkHealth}
          disabled={isLoading}
          className="w-full mt-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200"
          style={{
            background: isLoading
              ? "rgba(99,102,241,0.1)"
              : "rgba(99,102,241,0.15)",
            border: "1px solid rgba(99,102,241,0.3)",
            color: isLoading ? "var(--color-text-muted)" : "#a5b4fc",
            cursor: isLoading ? "not-allowed" : "pointer",
          }}
          onMouseEnter={(e) => {
            if (!isLoading)
              (e.currentTarget as HTMLButtonElement).style.background =
                "rgba(99,102,241,0.25)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background =
              "rgba(99,102,241,0.15)";
          }}
        >
          {isLoading ? "Checking…" : "↻ Refresh"}
        </button>
      </div>

      {/* ── Diagram Demo Section ── */}
      <div className="w-full max-w-3xl mt-10">
        <div className="flex items-center justify-between mb-4">
          <h2
            className="text-sm font-semibold uppercase tracking-widest"
            style={{ color: "var(--color-text-muted)" }}
          >
            Structure Diagram Demo
          </h2>
          <button
            id="btn-generate-diagram"
            onClick={fetchDiagram}
            disabled={diagramState === "loading"}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: "rgba(99,102,241,0.12)",
              border: "1px solid rgba(99,102,241,0.25)",
              color: "#a5b4fc",
              cursor: diagramState === "loading" ? "not-allowed" : "pointer",
              opacity: diagramState === "loading" ? 0.6 : 1,
            }}
          >
            {diagramState === "loading" ? "Generating…" : "↺ Re-generate"}
          </button>
        </div>

        {diagramState === "idle" && (
          <div
            className="rounded-2xl p-8 text-center"
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
              Start the backend then click Refresh to auto-generate a diagram.
            </p>
          </div>
        )}

        {diagramState === "loading" && (
          <div
            className="rounded-2xl p-8 flex items-center justify-center gap-3"
            style={{
              background: "rgba(255,255,255,0.02)",
              border: "1px solid rgba(255,255,255,0.06)",
            }}
          >
            <svg
              className="animate-spin"
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#818cf8"
              strokeWidth="2"
            >
              <path d="M21 12a9 9 0 1 1-6.219-8.56" />
            </svg>
            <span className="text-sm" style={{ color: "#818cf8" }}>Generating diagram…</span>
          </div>
        )}

        {diagramState === "error" && (
          <div
            className="rounded-2xl p-5 text-sm"
            style={{
              background: "rgba(248,113,113,0.06)",
              border: "1px solid rgba(248,113,113,0.2)",
              color: "#fca5a5",
            }}
          >
            {diagramError} — ensure the backend is running and try Refresh.
          </div>
        )}

        {diagramState === "success" && diagram && (
          <DiagramPanel
            diagram={diagram}
            isIllustrative={false}
          />
        )}
      </div>

      {/* ── Footer ── */}
      <p className="mt-12 text-xs" style={{ color: "var(--color-text-muted)" }}>
        Sententia.ai MVP · Diagram Engine v1.0 · PNG &amp; PDF export client-side
      </p>
    </main>
  );
}
