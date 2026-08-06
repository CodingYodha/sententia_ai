"use client";

/**
 * Review Queue page — reviewer/admin only (RBAC-gated).
 *
 * Shows all recent review actions from GET /api/review/queue.
 * Allows re-review of pending items.
 * FR-6.2: visual distinction between expert-validated and in-review output.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useRole } from "../components/RBACContext";
import { ReviewStatusBadge, type ReviewStatus } from "../components/ReviewActions";
import { AuthGuard } from "../components/AuthGuard";
import { useAuth } from "../components/AuthContext";
import { CorrectionForm } from "../components/CorrectionForm";
import { DisclaimerBanner } from "../components/DisclaimerBanner";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface QueueItem {
  review_id: string;
  structure_id: string;
  scenario_id: string | null;
  structure_name: string | null;
  action: string;
  notes: string | null;
  reviewer_role: string;
  created_at: string;
}

function formatDate(iso: string) {
  try { return new Date(iso).toLocaleString(); }
  catch { return iso; }
}

const ACTION_COLORS: Record<string, { bg: string; color: string }> = {
  approve: { bg: "rgba(52,211,153,0.08)",  color: "#34d399" },
  flag:    { bg: "rgba(245,158,11,0.08)",  color: "#f59e0b" },
  reject:  { bg: "rgba(248,113,113,0.08)", color: "#f87171" },
};

export default function ReviewPage() {
  const { can, role } = useRole();
  const router = useRouter();
  const { accessToken, profile } = useAuth();

  const [queue, setQueue]               = useState<QueueItem[]>([]);
  const [loading, setLoading]           = useState(true);
  const [error, setError]               = useState<string | null>(null);
  const [filter, setFilter]             = useState<"all" | "approve" | "flag" | "reject">("all");
  const [correctionItem, setCorrection] = useState<QueueItem | null>(null);

  const fetchQueue = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/review/queue?limit=100`, {
        headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setQueue(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load queue");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (can("review:read")) fetchQueue(); }, [can]);

  // RBAC gate
  if (!can("review:read")) {
    return (
      <div className="min-h-screen pt-28 flex flex-col items-center justify-center px-4">
        <div
          className="max-w-md w-full rounded-2xl p-10 text-center"
          style={{ background: "rgba(248,113,113,0.05)", border: "1px solid rgba(248,113,113,0.2)" }}
        >
          <div
            className="w-14 h-14 rounded-xl mx-auto mb-4 flex items-center justify-center"
            style={{ background: "rgba(248,113,113,0.1)" }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#f87171" strokeWidth="2" aria-hidden="true">
              <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>
            </svg>
          </div>
          <p className="text-base font-semibold mb-1" style={{ color: "#fca5a5" }}>Access Restricted</p>
          <p className="text-sm mb-5" style={{ color: "#94a3b8" }}>
            Review Queue requires Reviewer or Admin role.
            Switch your role in the navigation to access this page.
          </p>
          <p className="text-xs" style={{ color: "#64748b" }}>
            Current role: <strong style={{ color: "#818cf8" }}>{role}</strong>
          </p>
        </div>
      </div>
    );
  }

  const filtered = filter === "all" ? queue : queue.filter((i) => i.action === filter);

  const counts = {
    approve: queue.filter((i) => i.action === "approve").length,
    flag:    queue.filter((i) => i.action === "flag").length,
    reject:  queue.filter((i) => i.action === "reject").length,
  };

  return (
    <div className="min-h-screen pt-22 pb-16 px-4">
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="mb-8">
          <h1
            className="text-3xl font-bold mb-2"
            style={{
              background: "linear-gradient(135deg, #f1f1f8 30%, #818cf8 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Review Queue
          </h1>
          <p className="text-sm" style={{ color: "#64748b" }}>
            Expert validation decisions — all review actions are recorded in the audit log.
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          {([
            { key: "approve", label: "Validated",   color: "#34d399", bg: "rgba(52,211,153,0.08)",  border: "rgba(52,211,153,0.2)"  },
            { key: "flag",    label: "Flagged",      color: "#f59e0b", bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.2)"  },
            { key: "reject",  label: "Rejected",     color: "#f87171", bg: "rgba(248,113,113,0.07)", border: "rgba(248,113,113,0.2)" },
          ] as const).map(({ key, label, color, bg, border }) => (
            <div
              key={key}
              className="rounded-xl px-4 py-4 text-center"
              style={{ background: bg, border: `1px solid ${border}` }}
            >
              <p className="text-2xl font-bold" style={{ color }}>{counts[key]}</p>
              <p className="text-xs mt-1" style={{ color: "#64748b" }}>{label}</p>
            </div>
          ))}
        </div>

        {/* Filter tabs + refresh */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex gap-1">
            {(["all", "approve", "flag", "reject"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-all"
                style={{
                  background: filter === f ? "rgba(99,102,241,0.12)" : "transparent",
                  color:      filter === f ? "#818cf8" : "#64748b",
                  border:     filter === f ? "1px solid rgba(99,102,241,0.25)" : "1px solid transparent",
                }}
              >
                {f === "all" ? `All (${queue.length})` : `${f} (${counts[f as keyof typeof counts] ?? 0})`}
              </button>
            ))}
          </div>
          <button
            id="btn-refresh-queue"
            onClick={fetchQueue}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              color: "#64748b",
              cursor: loading ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "Loading…" : "↺ Refresh"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-xl p-4 mb-4 text-sm" style={{ background: "rgba(248,113,113,0.07)", border: "1px solid rgba(248,113,113,0.2)", color: "#fca5a5" }}>
            {error}
          </div>
        )}

        {/* Queue list */}
        {loading ? (
          <div className="flex items-center justify-center py-16 gap-3" style={{ color: "#818cf8" }}>
            <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            <span className="text-sm">Loading queue…</span>
          </div>
        ) : filtered.length === 0 ? (
          <div
            className="rounded-2xl p-12 text-center"
            style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}
          >
            <p className="text-base font-medium mb-2" style={{ color: "#f1f1f8" }}>No review actions yet</p>
            <p className="text-sm" style={{ color: "#64748b" }}>
              Generate and review structures from the{" "}
              <button
                onClick={() => router.push("/results")}
                style={{ color: "#818cf8", cursor: "pointer", background: "none", border: "none" }}
              >
                Results
              </button>{" "}
              page to populate this queue.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filtered.map((item) => {
              const ac = ACTION_COLORS[item.action] ?? ACTION_COLORS.flag;
              return (
                <div
                  key={item.review_id}
                  className="rounded-xl px-5 py-4"
                  style={{
                    background: "rgba(255,255,255,0.025)",
                    border: "1px solid rgba(255,255,255,0.07)",
                  }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1 flex-wrap">
                        {/* FR-6.2: visual distinction badge */}
                        <ReviewStatusBadge status={item.action as ReviewStatus} />
                        <span className="text-sm font-semibold truncate" style={{ color: "#f1f1f8" }}>
                          {item.structure_name ?? item.structure_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs flex-wrap" style={{ color: "#64748b" }}>
                        <span>Rank: #{item.structure_id.split("rank")[1] ?? "?"}</span>
                        {item.scenario_id && <span>Scenario: {item.scenario_id.slice(0, 8)}…</span>}
                        <span>By: {item.reviewer_role}</span>
                        <span>{formatDate(item.created_at)}</span>
                      </div>
                      {item.notes && (
                        <p className="mt-2 text-xs italic" style={{ color: "#94a3b8" }}>
                          "{item.notes}"
                        </p>
                      )}
                    </div>

                    {/* Actions column */}
                    <div className="shrink-0 text-right flex flex-col items-end gap-2">
                      <span className="text-xs font-mono" style={{ color: "#475569" }}>
                        {item.review_id.slice(0, 8)}
                      </span>
                      {can("review:write") && (
                        <button
                          onClick={() => setCorrection(item)}
                          className="text-xs px-2.5 py-1 rounded-lg transition-all"
                          style={{
                            background: "rgba(99,102,241,0.08)",
                            border:     "1px solid rgba(99,102,241,0.2)",
                            color:      "#818cf8",
                            cursor:     "pointer",
                          }}
                        >
                          + Correction
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {/* FR-6.2 legend */}
        <div
          className="mt-8 rounded-xl px-5 py-4"
          style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.05)" }}
        >
          <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#64748b" }}>
            FR-6.2 — Review Status Legend
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div>
              <ReviewStatusBadge status="pending" />
              <p className="mt-1" style={{ color: "#64748b" }}>Not yet reviewed</p>
            </div>
            <div>
              <ReviewStatusBadge status="approve" />
              <p className="mt-1" style={{ color: "#64748b" }}>Expert-validated</p>
            </div>
            <div>
              <ReviewStatusBadge status="flag" />
              <p className="mt-1" style={{ color: "#64748b" }}>Needs attention</p>
            </div>
            <div>
              <ReviewStatusBadge status="reject" />
              <p className="mt-1" style={{ color: "#64748b" }}>Do not use</p>
            </div>
          </div>
        </div>

        {/* FR-6.4 Disclaimer */}
        <DisclaimerBanner className="mt-6 rounded-xl" />
      </div>

      {/* FR-6.3 Correction Form Modal */}
      {correctionItem && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(6px)" }}
          onClick={() => setCorrection(null)}
        >
          <div
            className="w-full max-w-2xl rounded-2xl p-6"
            style={{
              background: "rgba(14,14,22,0.98)",
              border: "1px solid rgba(99,102,241,0.25)",
              boxShadow: "0 16px 64px rgba(0,0,0,0.6)",
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <CorrectionForm
              reviewQueueId={correctionItem.review_id}
              structureId={correctionItem.structure_id}
              structureName={correctionItem.structure_name ?? undefined}
              onSuccess={() => {
                setCorrection(null);
                fetchQueue();
              }}
              onCancel={() => setCorrection(null)}
            />
          </div>
        </div>
      )}
    </div>
  );
}
