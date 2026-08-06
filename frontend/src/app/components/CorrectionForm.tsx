"use client";

/**
 * CorrectionForm — FR-6.3
 *
 * Structured reviewer correction form. Uses typed enum fields (not free text)
 * so corrections can later feed model/rule refinement pipelines.
 *
 * Posts to POST /api/review/correction.
 */

import { useState } from "react";
import { useAuth } from "./AuthContext";

import { apiReviewCorrection } from "@/lib/api";

// ── Correction types ───────────────────────────────────────────────────────────

const CORRECTION_TYPES = [
  { value: "jurisdiction_error",    label: "Wrong jurisdiction recommended" },
  { value: "ownership_threshold",   label: "Ownership threshold % is wrong" },
  { value: "regulatory_gap",        label: "Missing regulatory requirement" },
  { value: "tax_issue",             label: "Tax treatment incorrect" },
  { value: "structure_type_wrong",  label: "SPV/Direct/JV choice wrong" },
  { value: "risk_severity_wrong",   label: "Risk severity misjudged" },
  { value: "missing_touchpoint",    label: "Compliance touchpoint omitted" },
  { value: "citation_error",        label: "Source citation wrong/hallucinated" },
  { value: "treaty_benefit_wrong",  label: "Treaty benefit analysis incorrect" },
  { value: "gaar_issue",            label: "GAAR/anti-avoidance flag missed" },
  { value: "other",                 label: "Other (explain in notes)" },
] as const;

const SEVERITY_OPTIONS = [
  { value: "low",      label: "Low — minor inaccuracy",        color: "#34d399" },
  { value: "medium",   label: "Medium — material error",       color: "#f59e0b" },
  { value: "high",     label: "High — significant issue",      color: "#f87171" },
  { value: "critical", label: "Critical — compliance risk",    color: "#ef4444" },
] as const;

// Common affected fields by category
const FIELD_SUGGESTIONS = [
  "ownership_chain",
  "architecture_description",
  "compliance_touchpoints[0].requirement",
  "compliance_touchpoints[0].timing",
  "identified_risks[0].severity",
  "identified_risks[0].description",
  "cited_sources[0]",
  "jurisdictions_involved",
  "regulatory_confidence",
  "rationale",
];

// ── Props ──────────────────────────────────────────────────────────────────────

interface CorrectionFormProps {
  reviewQueueId: string;
  structureId: string;
  structureName?: string;
  onSuccess?: (correctionId: string) => void;
  onCancel?: () => void;
}

// ── Component ──────────────────────────────────────────────────────────────────

export function CorrectionForm({
  reviewQueueId,
  structureId,
  structureName,
  onSuccess,
  onCancel,
}: CorrectionFormProps) {
  const { accessToken } = useAuth();

  const [correctionType,  setCT]   = useState("");
  const [affectedField,   setAF]   = useState("");
  const [originalValue,   setOV]   = useState("");
  const [correctedValue,  setCV]   = useState("");
  const [jurisdiction,    setJur]  = useState("");
  const [severity,        setSev]  = useState<"low"|"medium"|"high"|"critical">("medium");
  const [notes,           setNotes]= useState("");
  const [submitting,      setSub]  = useState(false);
  const [error,           setErr]  = useState<string | null>(null);
  const [success,         setSucc] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!correctionType || !affectedField || !correctedValue) {
      setErr("Correction type, affected field, and corrected value are required.");
      return;
    }
    setSub(true); setErr(null);

    try {
      const data = await apiReviewCorrection({
        review_queue_id: reviewQueueId,
        structure_id:    structureId,
        correction_type: correctionType,
        affected_field:  affectedField,
        original_value:  originalValue || null,
        corrected_value: correctedValue,
        jurisdiction:    jurisdiction || null,
        severity,
        notes:           notes || null,
      }, accessToken);

      setSucc(`Correction recorded: ${data.correction_id}`);
      onSuccess?.(data.correction_id);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Submission failed");
    } finally {
      setSub(false);
    }
  }

  const fieldStyle: React.CSSProperties = {
    width: "100%", padding: "9px 12px", borderRadius: "8px", fontSize: "13px",
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)",
    color: "#f1f1f8", outline: "none",
  };
  const selectStyle: React.CSSProperties = {
    ...fieldStyle,
    background: "rgba(15,15,24,0.9)",
    cursor: "pointer",
  };

  function Label({ children, required }: { children: React.ReactNode; required?: boolean }) {
    return (
      <label className="block text-xs font-semibold uppercase tracking-widest mb-1" style={{ color: "#64748b" }}>
        {children}{required && <span style={{ color: "#f87171" }}> *</span>}
      </label>
    );
  }

  if (success) {
    return (
      <div className="rounded-xl p-5 text-center" style={{ background: "rgba(52,211,153,0.06)", border: "1px solid rgba(52,211,153,0.2)" }}>
        <p className="text-sm font-semibold mb-1" style={{ color: "#34d399" }}>✓ Correction Recorded</p>
        <p className="text-xs mb-3" style={{ color: "#6ee7b7" }}>{success}</p>
        <button onClick={onCancel} className="text-xs underline" style={{ color: "#64748b", background: "none", border: "none", cursor: "pointer" }}>
          Close
        </button>
      </div>
    );
  }

  return (
    <div
      className="rounded-xl p-5"
      style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.08)" }}
    >
      <div className="flex items-center justify-between mb-4">
        <div>
          <p className="text-sm font-semibold" style={{ color: "#c7d2fe" }}>Add Structured Correction</p>
          {structureName && (
            <p className="text-xs mt-0.5" style={{ color: "#64748b" }}>{structureName}</p>
          )}
        </div>
        <span
          className="text-xs px-2 py-1 rounded-full"
          style={{ background: "rgba(99,102,241,0.1)", color: "#818cf8", border: "1px solid rgba(99,102,241,0.2)" }}
        >
          FR-6.3
        </span>
      </div>

      <form onSubmit={handleSubmit} noValidate>
        <div className="space-y-4">

          {/* Correction type */}
          <div>
            <Label required>Correction Type</Label>
            <select
              id="select-correction-type"
              value={correctionType}
              onChange={(e) => setCT(e.target.value)}
              style={selectStyle}
            >
              <option value="">Select type…</option>
              {CORRECTION_TYPES.map((ct) => (
                <option key={ct.value} value={ct.value}>{ct.label}</option>
              ))}
            </select>
          </div>

          {/* Affected field */}
          <div>
            <Label required>Affected Field</Label>
            <input
              id="input-affected-field"
              type="text"
              list="field-suggestions"
              value={affectedField}
              onChange={(e) => setAF(e.target.value)}
              placeholder="e.g. ownership_chain, compliance_touchpoints[0].requirement"
              style={fieldStyle}
            />
            <datalist id="field-suggestions">
              {FIELD_SUGGESTIONS.map((f) => <option key={f} value={f}/>)}
            </datalist>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Original (LLM) value */}
            <div>
              <Label>LLM's Incorrect Value</Label>
              <textarea
                value={originalValue}
                onChange={(e) => setOV(e.target.value)}
                placeholder="What the LLM said…"
                rows={2}
                style={{ ...fieldStyle, resize: "vertical" }}
              />
            </div>

            {/* Corrected value */}
            <div>
              <Label required>Correct Value</Label>
              <textarea
                id="input-corrected-value"
                value={correctedValue}
                onChange={(e) => setCV(e.target.value)}
                placeholder="What it should be…"
                rows={2}
                style={{ ...fieldStyle, resize: "vertical" }}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Jurisdiction */}
            <div>
              <Label>Jurisdiction</Label>
              <input
                type="text"
                value={jurisdiction}
                onChange={(e) => setJur(e.target.value)}
                placeholder="e.g. India, Singapore"
                style={fieldStyle}
              />
            </div>

            {/* Severity */}
            <div>
              <Label required>Severity</Label>
              <select
                id="select-severity"
                value={severity}
                onChange={(e) => setSev(e.target.value as typeof severity)}
                style={selectStyle}
              >
                {SEVERITY_OPTIONS.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Notes (optional) */}
          <div>
            <Label>Notes <span style={{ color: "#475569", fontWeight: 400, textTransform: "none", letterSpacing: 0 }}>(optional context)</span></Label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Any additional context — this supplements the structured fields above."
              rows={2}
              maxLength={1000}
              style={{ ...fieldStyle, resize: "vertical" }}
            />
          </div>

          {/* Error */}
          {error && (
            <p className="text-xs" style={{ color: "#f87171" }}>⚠ {error}</p>
          )}

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              id="btn-submit-correction"
              type="submit"
              disabled={submitting}
              className="flex-1 py-2.5 rounded-xl text-sm font-semibold transition-all"
              style={{
                background: "rgba(99,102,241,0.15)",
                border:     "1.5px solid rgba(99,102,241,0.35)",
                color:      "#818cf8",
                cursor:     submitting ? "not-allowed" : "pointer",
              }}
            >
              {submitting ? "Submitting…" : "Record Correction"}
            </button>
            {onCancel && (
              <button
                type="button"
                onClick={onCancel}
                className="px-4 py-2.5 rounded-xl text-sm"
                style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)", color: "#64748b", cursor: "pointer" }}
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      </form>
    </div>
  );
}
