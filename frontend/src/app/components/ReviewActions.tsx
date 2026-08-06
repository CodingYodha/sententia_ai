"use client";

/**
 * ReviewActions — Approve / Flag / Reject buttons for reviewer/admin roles.
 * Writes to POST /api/review/action and shows outcome badge.
 * PRD FR-6.2: visual distinction between expert-validated and in-review output.
 */

import { useState } from "react";
import { useAuth } from "./AuthContext";

import { apiReviewAction } from "../lib/api";

export type ReviewStatus = "pending" | "approve" | "flag" | "reject";

interface ReviewActionsProps {
  structureId: string;
  scenarioId?: string;
  alternativeRank?: number;
  structureName?: string;
  reviewerRole?: string;
  initialStatus?: ReviewStatus;
  onActionComplete?: (action: ReviewStatus) => void;
}

const ACTION_CFG = {
  approve: {
    label: "Approve",
    icon: "✓",
    bg:     "rgba(52,211,153,0.1)",
    border: "rgba(52,211,153,0.25)",
    color:  "#34d399",
    hoverBg:"rgba(52,211,153,0.2)",
  },
  flag: {
    label: "Flag",
    icon: "⚑",
    bg:     "rgba(245,158,11,0.1)",
    border: "rgba(245,158,11,0.25)",
    color:  "#f59e0b",
    hoverBg:"rgba(245,158,11,0.2)",
  },
  reject: {
    label: "Reject",
    icon: "✕",
    bg:     "rgba(248,113,113,0.08)",
    border: "rgba(248,113,113,0.22)",
    color:  "#f87171",
    hoverBg:"rgba(248,113,113,0.18)",
  },
} as const;

const STATUS_BADGES: Record<ReviewStatus, { label: string; color: string; bg: string }> = {
  pending: { label: "In Review",          color: "#94a3b8", bg: "rgba(148,163,184,0.1)" },
  approve: { label: "✓ Expert Validated", color: "#34d399", bg: "rgba(52,211,153,0.1)"  },
  flag:    { label: "⚑ Flagged",          color: "#f59e0b", bg: "rgba(245,158,11,0.1)"  },
  reject:  { label: "✕ Rejected",         color: "#f87171", bg: "rgba(248,113,113,0.1)" },
};

export function ReviewStatusBadge({ status }: { status: ReviewStatus }) {
  const cfg = STATUS_BADGES[status];
  return (
    <span
      className="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold"
      style={{ background: cfg.bg, color: cfg.color }}
    >
      {cfg.label}
    </span>
  );
}

export function ReviewActions({
  structureId,
  scenarioId,
  alternativeRank,
  structureName,
  reviewerRole = "reviewer",
  initialStatus = "pending",
  onActionComplete,
}: ReviewActionsProps) {
  const [status, setStatus]         = useState<ReviewStatus>(initialStatus);
  const [loading, setLoading]       = useState<string | null>(null);
  const [error, setError]           = useState<string | null>(null);
  const [notesOpen, setNotesOpen]   = useState(false);
  const [notes, setNotes]           = useState("");
  const [pendingAction, setPending] = useState<"approve" | "flag" | "reject" | null>(null);
  const { accessToken }             = useAuth();

  async function submitAction(action: "approve" | "flag" | "reject", notesText: string) {
    setLoading(action);
    setError(null);
    try {
      await apiReviewAction({
        structure_id: structureId,
        scenario_id: scenarioId,
        alternative_rank: alternativeRank,
        structure_name: structureName,
        action,
        notes: notesText || null,
        reviewer_role: reviewerRole,
      }, accessToken);
      setStatus(action);
      onActionComplete?.(action);
      setNotesOpen(false);
      setNotes("");
      setPending(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review action failed");
    } finally {
      setLoading(null);
    }
  }

  function handleClick(action: "approve" | "flag" | "reject") {
    setPending(action);
    setNotesOpen(true);
  }

  // Already actioned — show badge + undo
  if (status !== "pending") {
    return (
      <div className="flex items-center gap-3 flex-wrap">
        <ReviewStatusBadge status={status} />
        <button
          onClick={() => setStatus("pending")}
          className="text-xs underline"
          style={{ color: "#64748b" }}
        >
          Undo
        </button>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2 flex-wrap">
        {(["approve", "flag", "reject"] as const).map((action) => {
          const cfg = ACTION_CFG[action];
          const isLoading = loading === action;
          return (
            <button
              key={action}
              id={`btn-review-${action}-${structureId}`}
              onClick={() => handleClick(action)}
              disabled={!!loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: cfg.bg,
                border: `1px solid ${cfg.border}`,
                color: cfg.color,
                opacity: loading && !isLoading ? 0.5 : 1,
                cursor: loading ? "not-allowed" : "pointer",
              }}
              onMouseEnter={(e) => { if (!loading) (e.currentTarget as HTMLButtonElement).style.background = cfg.hoverBg; }}
              onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = cfg.bg; }}
            >
              <span>{isLoading ? "…" : cfg.icon}</span>
              {cfg.label}
            </button>
          );
        })}
      </div>

      {/* Notes modal */}
      {notesOpen && pendingAction && (
        <div
          className="mt-3 rounded-xl p-4"
          style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.09)",
          }}
        >
          <p className="text-xs font-medium mb-2" style={{ color: "#94a3b8" }}>
            Notes for {pendingAction} (optional)
          </p>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Add notes for audit log…"
            rows={2}
            className="w-full rounded-lg px-3 py-2 text-xs resize-none"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "#f1f1f8",
              outline: "none",
            }}
          />
          <div className="flex gap-2 mt-2">
            <button
              onClick={() => submitAction(pendingAction, notes)}
              disabled={!!loading}
              className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all"
              style={{
                background: ACTION_CFG[pendingAction].bg,
                border: `1px solid ${ACTION_CFG[pendingAction].border}`,
                color: ACTION_CFG[pendingAction].color,
                cursor: loading ? "not-allowed" : "pointer",
              }}
            >
              {loading ? "Submitting…" : `Confirm ${pendingAction}`}
            </button>
            <button
              onClick={() => { setNotesOpen(false); setPending(null); }}
              className="px-3 py-1.5 rounded-lg text-xs"
              style={{ color: "#64748b" }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {error && (
        <p className="mt-2 text-xs" style={{ color: "#f87171" }}>⚠ {error}</p>
      )}
    </div>
  );
}
