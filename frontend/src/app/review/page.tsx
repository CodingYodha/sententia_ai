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

import { apiReviewQueueList } from "@/lib/api";

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
      const data = await apiReviewQueueList(100, accessToken);
      setQueue(data);
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
    <div className="min-h-screen pt-22 pb-16 px-4 relative z-10">
      <div className="max-w-4xl mx-auto">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-editorial-display text-stone-900 mb-2">
            Review Queue
          </h1>
          <p className="text-sm font-editorial-body text-stone-600">
            Expert validation decisions — all review actions are recorded in the audit log.
          </p>
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          {([
            { key: "approve", label: "Validated",   color: "#15803d", bg: "#f0fdf4", border: "#bbf7d0" },
            { key: "flag",    label: "Flagged",      color: "#b45309", bg: "#fffbeb", border: "#fde68a" },
            { key: "reject",  label: "Rejected",     color: "#b91c1c", bg: "#fef2f2", border: "#fecaca" },
          ] as const).map(({ key, label, color, bg, border }) => (
            <div
              key={key}
              className="rounded-2xl px-5 py-4 text-center card-editorial"
              style={{ background: bg, borderColor: border }}
            >
              <p className="text-3xl font-editorial-display font-medium" style={{ color }}>{counts[key]}</p>
              <p className="text-xs font-semibold uppercase tracking-wider mt-1 text-stone-600">{label}</p>
            </div>
          ))}
        </div>

        {/* Filter tabs + refresh */}
        <div className="flex items-center justify-between mb-6 flex-wrap gap-2">
          <div className="flex gap-1.5">
            {(["all", "approve", "flag", "reject"] as const).map((f) => (
              <button
                key={f}
                onClick={() => setFilter(f)}
                className="px-3.5 py-1.5 rounded-full text-xs font-medium capitalize transition-all"
                style={{
                  background: filter === f ? "#0c0a09" : "#f0efed",
                  color:      filter === f ? "#ffffff" : "#4e4e4e",
                  fontWeight: filter === f ? 600 : 500,
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
            className="btn-outline text-xs px-3.5 py-1.5 h-auto"
          >
            {loading ? "Loading…" : "↺ Refresh"}
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="rounded-2xl p-4 mb-4 text-sm bg-red-50 border border-red-200 text-red-700 font-medium">
            {error}
          </div>
        )}

        {/* Queue list */}
        {loading ? (
          <div className="card-editorial flex items-center justify-center py-16 gap-3 text-stone-600">
            <svg className="animate-spin" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
            <span className="text-sm font-editorial-body">Loading queue…</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="card-editorial p-12 text-center">
            <p className="text-lg font-editorial-display font-medium text-stone-900 mb-2">No review actions yet</p>
            <p className="text-sm font-editorial-body text-stone-500">
              Generate and review structures from the{" "}
              <button
                onClick={() => router.push("/results")}
                className="text-stone-900 font-semibold underline hover:text-stone-700"
              >
                Results
              </button>{" "}
              page to populate this queue.
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {filtered.map((item) => {
              return (
                <div
                  key={item.review_id}
                  className="card-editorial p-5"
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-3 mb-1.5 flex-wrap">
                        {/* FR-6.2: visual distinction badge */}
                        <ReviewStatusBadge status={item.action as ReviewStatus} />
                        <span className="text-base font-editorial-display font-medium text-stone-900 truncate">
                          {item.structure_name ?? item.structure_id}
                        </span>
                      </div>
                      <div className="flex items-center gap-3 text-xs font-editorial-body text-stone-500 flex-wrap">
                        <span>Rank: #{item.structure_id.split("rank")[1] ?? "?"}</span>
                        {item.scenario_id && <span>Scenario: {item.scenario_id.slice(0, 8)}…</span>}
                        <span>By: {item.reviewer_role}</span>
                        <span>{formatDate(item.created_at)}</span>
                      </div>
                      {item.notes && (
                        <p className="mt-2 text-xs italic font-editorial-body text-stone-600">
                          "{item.notes}"
                        </p>
                      )}
                    </div>

                    {/* Actions column */}
                    <div className="shrink-0 text-right flex flex-col items-end gap-2">
                      <span className="text-xs font-mono text-stone-400">
                        {item.review_id.slice(0, 8)}
                      </span>
                      {can("review:write") && (
                        <button
                          onClick={() => setCorrection(item)}
                          className="btn-outline text-xs px-3 py-1 h-auto"
                        >
                          Correct / Re-evaluate
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
