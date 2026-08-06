"use client";

/**
 * Intake page — multi-step wizard:
 *
 * Step 1: Scenario form (FR-1.1 fields) + optional document upload
 * Step 2: Document extraction preview (confirm extracted UBO data)
 * Step 3: Generate structures → results
 *
 * Client-side validation: required fields, numeric ranges.
 * Server-side validation: FastAPI 422 errors surfaced inline.
 */

import { useRef, useState } from "react";
import { useAuth } from "../components/AuthContext";
import { useRouter } from "next/navigation";
import { useRole } from "../components/RBACContext";

import { apiIntakeDocument, apiIntakeScenario, apiStructuresGenerate } from "@/lib/api";

// ── Types ──────────────────────────────────────────────────────────────────────

interface ScenarioFormData {
  investor_name:    string;
  origin_jurisdiction: string;
  target_jurisdiction: string;
  spv_jurisdiction: string;
  sector:           string;
  investment_amount_usd: string;
  equity_pct:       string;
  has_us_persons_in_fund: boolean;
  is_prohibited_sector:   boolean;
  prior_govt_approval_obtained: boolean;
  additional_context: string;
}

interface FormErrors { [key: string]: string }

interface ExtractionPreview {
  scenario_id?: string;
  ubo_info?: {
    ownership_chain_summary: string;
    ultimate_beneficial_owners: Array<{
      name: string;
      jurisdiction: string;
      entity_type: string;
      ownership_pct: number;
    }>;
  };
  raw_preview?: string;
}

// ── Constants ──────────────────────────────────────────────────────────────────

const SECTORS = [
  "Technology & Software", "Financial Services", "Infrastructure", "Real Estate",
  "Healthcare & Pharma", "Energy & Renewables", "Manufacturing", "E-Commerce & Retail",
  "Defence & Aerospace", "Agriculture & Food", "Telecom & Media", "Other",
];

const JURISDICTIONS = [
  "China (PRC)", "India", "Singapore", "United States", "United Kingdom",
  "Germany", "France", "Netherlands", "Luxembourg", "Cayman Islands",
  "Mauritius", "UAE (Dubai)", "Japan", "South Korea", "Brazil", "Australia",
  "Hong Kong", "British Virgin Islands", "Cyprus", "Switzerland", "Other",
];

const INITIAL: ScenarioFormData = {
  investor_name: "", origin_jurisdiction: "", target_jurisdiction: "",
  spv_jurisdiction: "", sector: "", investment_amount_usd: "", equity_pct: "",
  has_us_persons_in_fund: false, is_prohibited_sector: false,
  prior_govt_approval_obtained: false, additional_context: "",
};

// ── Validation ─────────────────────────────────────────────────────────────────

function validate(data: ScenarioFormData): FormErrors {
  const errs: FormErrors = {};
  if (!data.investor_name.trim())          errs.investor_name    = "Investor name is required";
  if (!data.origin_jurisdiction.trim())    errs.origin_jurisdiction = "Origin jurisdiction is required";
  if (!data.target_jurisdiction.trim())    errs.target_jurisdiction = "Target jurisdiction is required";
  if (!data.sector.trim())                 errs.sector           = "Sector is required";
  if (!data.investment_amount_usd.trim())  errs.investment_amount_usd = "Investment amount is required";
  else if (isNaN(Number(data.investment_amount_usd)) || Number(data.investment_amount_usd) <= 0)
    errs.investment_amount_usd = "Must be a positive number";
  if (data.equity_pct.trim()) {
    const n = Number(data.equity_pct);
    if (isNaN(n) || n < 0 || n > 100) errs.equity_pct = "Must be between 0 and 100";
  }
  return errs;
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function FieldError({ msg }: { msg?: string }) {
  if (!msg) return null;
  return <p className="text-xs mt-1" style={{ color: "#f87171" }}>{msg}</p>;
}

function FormLabel({ children, required }: { children: React.ReactNode; required?: boolean }) {
  return (
    <label className="block text-xs font-semibold uppercase tracking-widest mb-1.5" style={{ color: "#64748b" }}>
      {children}{required && <span style={{ color: "#f87171" }}> *</span>}
    </label>
  );
}

function inputStyle(hasError?: boolean): React.CSSProperties {
  return {
    background: "rgba(255,255,255,0.04)",
    border: `1px solid ${hasError ? "rgba(248,113,113,0.5)" : "rgba(255,255,255,0.1)"}`,
    color: "#f1f1f8",
    outline: "none",
    width: "100%",
    borderRadius: "10px",
    padding: "10px 14px",
    fontSize: "14px",
    transition: "border-color 0.2s",
  };
}

function selectStyle(hasError?: boolean): React.CSSProperties {
  return {
    ...inputStyle(hasError),
    background: "rgba(15,15,24,0.9)",
    cursor: "pointer",
  };
}

function StepDot({ n, label, step }: { n: number; label: string; step: number }) {
  const done    = step > n;
  const current = step === n;
  return (
    <div className="flex items-center gap-2">
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold"
        style={{
          background: done ? "rgba(52,211,153,0.15)" : current ? "rgba(99,102,241,0.2)" : "rgba(255,255,255,0.05)",
          border:     done ? "1px solid rgba(52,211,153,0.4)" : current ? "1.5px solid rgba(99,102,241,0.5)" : "1px solid rgba(255,255,255,0.08)",
          color:      done ? "#34d399" : current ? "#818cf8" : "#64748b",
        }}
      >
        {done ? "✓" : n}
      </div>
      <span className="text-xs font-medium hidden sm:block" style={{ color: current ? "#f1f1f8" : "#64748b" }}>
        {label}
      </span>
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      className="rounded-2xl p-6"
      style={{
        background: "rgba(255,255,255,0.025)",
        border: "1px solid rgba(255,255,255,0.07)",
        boxShadow: "0 4px 32px rgba(0,0,0,0.3)",
      }}
    >
      {children}
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

type Step = 1 | 2 | 3;

export default function IntakePage() {
  const { can } = useRole();
  const router  = useRouter();
  const { accessToken } = useAuth();

  const [step, setStep]             = useState<Step>(1);
  const [form, setForm]             = useState<ScenarioFormData>(INITIAL);
  const [errors, setErrors]         = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);

  // Document upload state
  const [uploadFile, setUploadFile]       = useState<File | null>(null);
  const [uploading, setUploading]         = useState(false);
  const [extraction, setExtraction]       = useState<ExtractionPreview | null>(null);
  const [uploadError, setUploadError]     = useState<string | null>(null);
  const [dragOver, setDragOver]           = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  // Generation state
  const [generating, setGenerating]       = useState(false);
  const [genError, setGenError]           = useState<string | null>(null);
  const [scenarioId, setScenarioId]       = useState<string | null>(null);

  if (!can("intake:submit")) {
    return (
      <div className="pt-28 flex flex-col items-center justify-center min-h-screen" style={{ color: "#64748b" }}>
        <p className="text-lg">Access Denied — intake requires Associate role or higher.</p>
      </div>
    );
  }

  // ── Form helpers ────────────────────────────────────────────────────────────

  function setField(k: keyof ScenarioFormData, v: string | boolean) {
    setForm((f) => ({ ...f, [k]: v }));
    setErrors((e) => { const n = { ...e }; delete n[k]; return n; });
  }

  function handleCheckbox(k: keyof ScenarioFormData) {
    setField(k, !form[k as keyof typeof form]);
  }

  // ── Document upload ─────────────────────────────────────────────────────────

  async function uploadDocument(file: File) {
    setUploading(true);
    setUploadError(null);
    try {
      const data = await apiIntakeDocument(file);
      setExtraction(data);
    } catch (e) {
      setUploadError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  function handleFileDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) { setUploadFile(file); uploadDocument(file); }
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) { setUploadFile(file); uploadDocument(file); }
  }

  // ── Submit scenario form ────────────────────────────────────────────────────

  async function handleSubmitForm(e: React.FormEvent) {
    e.preventDefault();
    const errs = validate(form);
    if (Object.keys(errs).length > 0) { setErrors(errs); return; }
    setServerError(null);

    // If document was uploaded and extraction is pending, go to step 2 for confirmation
    if (uploadFile && extraction) { setStep(2); return; }
    // Otherwise go straight to generation
    await generateStructures();
  }

  // ── Generate structures ─────────────────────────────────────────────────────

  async function generateStructures() {
    if (!can("structures:generate")) { setGenError("Insufficient permissions."); return; }
    setGenerating(true);
    setGenError(null);
    setStep(3);

    try {
      // Build scenario payload matching ScenarioCreate Pydantic schema
      const regulatory_constraints = [];
      if (form.has_us_persons_in_fund) regulatory_constraints.push("fund_has_us_persons");
      if (form.is_prohibited_sector) regulatory_constraints.push("prohibited_sector");
      if (form.prior_govt_approval_obtained) regulatory_constraints.push("prior_govt_approval_obtained");

      const scenarioPayload = {
        investor_name: form.investor_name, // Sent to backend, though backend needs it added to schema
        capital_origin: form.origin_jurisdiction,
        target_jurisdiction: form.target_jurisdiction,
        spv_jurisdiction: form.spv_jurisdiction || undefined,
        sector: form.sector,
        investment_amount_usd: Number(form.investment_amount_usd),
        equity_pct: form.equity_pct ? Number(form.equity_pct) : undefined,
        investment_structure_type: "direct_fdi", // Default as frontend lacks this field
        regulatory_constraints,
        notes: form.additional_context || undefined,
      };

      // Step A: Submit scenario to intake endpoint
      let sid: string;
      try {
        const intakeData = await apiIntakeScenario(scenarioPayload);
        sid = intakeData.scenario_id ?? crypto.randomUUID();
      } catch {
        sid = crypto.randomUUID();
      }
      setScenarioId(sid);

      // Step B: Generate structures
      const genData = await apiStructuresGenerate(scenarioPayload, 3, accessToken);

      // Store in sessionStorage for results page
      sessionStorage.setItem("sententia_results", JSON.stringify({
        scenarioId: sid,
        scenario: scenarioPayload,
        ...genData,
      }));

      // Navigate to results
      router.push("/results");

    } catch (e) {
      setGenError(e instanceof Error ? e.message : "Generation failed");
      setGenerating(false);
      setStep(1);
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-2xl mx-auto">

        {/* Page header */}
        <div className="mb-8">
          <h1
            className="text-3xl font-bold mb-2"
            style={{
              background: "linear-gradient(135deg, #f1f1f8 30%, #818cf8 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            New Scenario
          </h1>
          <p className="text-sm" style={{ color: "#64748b" }}>
            Structure a cross-border FDI scenario and generate compliance-aware structuring alternatives.
          </p>
        </div>

        {/* Step indicator */}
        <div className="flex items-center gap-4 mb-8">
          <StepDot n={1} label="Scenario Details" step={step} />
          <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)" }} />
          <StepDot n={2} label="Document Review" step={step} />
          <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.06)" }} />
          <StepDot n={3} label="Generating…" step={step} />
        </div>

        {/* ── STEP 1: SCENARIO FORM ── */}
        {step === 1 && (
          <form onSubmit={handleSubmitForm} noValidate>
            <div className="space-y-5">

              {/* Investor / Entity */}
              <Card>
                <h2 className="text-sm font-semibold mb-4" style={{ color: "#818cf8" }}>Investor Details</h2>
                <div>
                  <FormLabel required>Investor / Entity Name</FormLabel>
                  <input
                    id="input-investor-name"
                    type="text"
                    value={form.investor_name}
                    onChange={(e) => setField("investor_name", e.target.value)}
                    placeholder="e.g. HSG Capital Fund I LP"
                    style={inputStyle(!!errors.investor_name)}
                  />
                  <FieldError msg={errors.investor_name} />
                </div>
              </Card>

              {/* Jurisdictions */}
              <Card>
                <h2 className="text-sm font-semibold mb-4" style={{ color: "#818cf8" }}>Jurisdictions</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <FormLabel required>Origin Jurisdiction</FormLabel>
                    <input
                      id="input-origin-jurisdiction"
                      type="text"
                      list="jur-list"
                      value={form.origin_jurisdiction}
                      onChange={(e) => setField("origin_jurisdiction", e.target.value)}
                      placeholder="e.g. China (PRC)"
                      style={inputStyle(!!errors.origin_jurisdiction)}
                    />
                    <datalist id="jur-list">
                      {JURISDICTIONS.map((j) => <option key={j} value={j} />)}
                    </datalist>
                    <FieldError msg={errors.origin_jurisdiction} />
                  </div>
                  <div>
                    <FormLabel required>Target Jurisdiction</FormLabel>
                    <input
                      id="input-target-jurisdiction"
                      type="text"
                      list="jur-list"
                      value={form.target_jurisdiction}
                      onChange={(e) => setField("target_jurisdiction", e.target.value)}
                      placeholder="e.g. India"
                      style={inputStyle(!!errors.target_jurisdiction)}
                    />
                    <FieldError msg={errors.target_jurisdiction} />
                  </div>
                  <div className="sm:col-span-2">
                    <FormLabel>SPV / Intermediate Jurisdiction (optional)</FormLabel>
                    <input
                      id="input-spv-jurisdiction"
                      type="text"
                      list="jur-list"
                      value={form.spv_jurisdiction}
                      onChange={(e) => setField("spv_jurisdiction", e.target.value)}
                      placeholder="e.g. Singapore — leave blank to let the AI suggest"
                      style={inputStyle()}
                    />
                  </div>
                </div>
              </Card>

              {/* Deal Parameters */}
              <Card>
                <h2 className="text-sm font-semibold mb-4" style={{ color: "#818cf8" }}>Deal Parameters</h2>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <FormLabel required>Sector</FormLabel>
                    <select
                      id="select-sector"
                      value={form.sector}
                      onChange={(e) => setField("sector", e.target.value)}
                      style={selectStyle(!!errors.sector)}
                    >
                      <option value="">Select sector…</option>
                      {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                    <FieldError msg={errors.sector} />
                  </div>
                  <div>
                    <FormLabel required>Investment Amount (USD)</FormLabel>
                    <input
                      id="input-investment-amount"
                      type="number"
                      min="0"
                      value={form.investment_amount_usd}
                      onChange={(e) => setField("investment_amount_usd", e.target.value)}
                      placeholder="e.g. 50000000"
                      style={inputStyle(!!errors.investment_amount_usd)}
                    />
                    <FieldError msg={errors.investment_amount_usd} />
                  </div>
                  <div>
                    <FormLabel>Equity % (optional)</FormLabel>
                    <input
                      id="input-equity-pct"
                      type="number"
                      min="0"
                      max="100"
                      step="0.1"
                      value={form.equity_pct}
                      onChange={(e) => setField("equity_pct", e.target.value)}
                      placeholder="e.g. 74"
                      style={inputStyle(!!errors.equity_pct)}
                    />
                    <FieldError msg={errors.equity_pct} />
                  </div>
                </div>

                {/* Booleans */}
                <div className="mt-4 space-y-3">
                  {[
                    { key: "has_us_persons_in_fund" as const, label: "Fund has US persons (CFIUS / FBAR implications)" },
                    { key: "is_prohibited_sector" as const,   label: "Target sector is potentially restricted / dual-use" },
                    { key: "prior_govt_approval_obtained" as const, label: "Prior government approval already obtained" },
                  ].map(({ key, label }) => (
                    <label key={key} className="flex items-center gap-3 cursor-pointer">
                      <div
                        className="w-5 h-5 rounded flex items-center justify-center shrink-0"
                        style={{
                          background: form[key] ? "rgba(99,102,241,0.2)" : "rgba(255,255,255,0.04)",
                          border: form[key] ? "1.5px solid #6366f1" : "1px solid rgba(255,255,255,0.12)",
                        }}
                        onClick={() => handleCheckbox(key)}
                      >
                        {form[key] && (
                          <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="#818cf8" strokeWidth="2.5">
                            <polyline points="2 6 5 9 10 3"/>
                          </svg>
                        )}
                      </div>
                      <input type="checkbox" className="sr-only" checked={form[key]} onChange={() => handleCheckbox(key)} />
                      <span className="text-sm" style={{ color: "#94a3b8" }}>{label}</span>
                    </label>
                  ))}
                </div>
              </Card>

              {/* Additional context */}
              <Card>
                <h2 className="text-sm font-semibold mb-4" style={{ color: "#818cf8" }}>Additional Context</h2>
                <textarea
                  id="input-additional-context"
                  value={form.additional_context}
                  onChange={(e) => setField("additional_context", e.target.value)}
                  placeholder="Any specific structuring constraints, existing relationships, preferred holding jurisdictions, or other context for the AI…"
                  rows={3}
                  style={{ ...inputStyle(), resize: "vertical" }}
                />
              </Card>

              {/* Document upload */}
              <Card>
                <h2 className="text-sm font-semibold mb-1" style={{ color: "#818cf8" }}>Upload Document <span style={{ color: "#64748b", fontWeight: 400 }}>(optional)</span></h2>
                <p className="text-xs mb-4" style={{ color: "#64748b" }}>
                  Upload a term sheet, cap table, or UBO disclosure for automated extraction. Supported: PDF, DOCX, TXT.
                </p>
                <div
                  className="rounded-xl border-2 border-dashed p-6 text-center transition-all cursor-pointer"
                  style={{
                    borderColor: dragOver ? "rgba(99,102,241,0.5)" : "rgba(255,255,255,0.1)",
                    background:  dragOver ? "rgba(99,102,241,0.05)" : "transparent",
                  }}
                  onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={handleFileDrop}
                  onClick={() => fileRef.current?.click()}
                >
                  <input ref={fileRef} type="file" accept=".pdf,.docx,.txt" className="sr-only" onChange={handleFileSelect} />
                  {uploading ? (
                    <p className="text-sm" style={{ color: "#818cf8" }}>Uploading and extracting…</p>
                  ) : uploadFile ? (
                    <div>
                      <p className="text-sm font-medium" style={{ color: "#34d399" }}>✓ {uploadFile.name}</p>
                      <p className="text-xs mt-1" style={{ color: "#64748b" }}>Click to replace</p>
                    </div>
                  ) : (
                    <div>
                      <svg width="24" height="24" className="mx-auto mb-2" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="1.5" aria-hidden="true">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
                      </svg>
                      <p className="text-sm" style={{ color: "#64748b" }}>Drag & drop or <span style={{ color: "#818cf8" }}>browse</span></p>
                      <p className="text-xs mt-1" style={{ color: "#475569" }}>PDF, DOCX, TXT — max 10 MB</p>
                    </div>
                  )}
                </div>
                {uploadError && <p className="text-xs mt-2" style={{ color: "#f87171" }}>⚠ {uploadError}</p>}
              </Card>

              {/* Server error */}
              {serverError && (
                <div className="rounded-xl p-4 text-sm" style={{ background: "rgba(248,113,113,0.07)", border: "1px solid rgba(248,113,113,0.2)", color: "#fca5a5" }}>
                  {serverError}
                </div>
              )}

              {/* Submit */}
              <button
                id="btn-submit-scenario"
                type="submit"
                className="w-full py-3.5 rounded-xl text-sm font-semibold transition-all"
                style={{
                  background: "linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(99,102,241,0.12) 100%)",
                  border: "1.5px solid rgba(99,102,241,0.4)",
                  color: "#a5b4fc",
                  cursor: "pointer",
                  boxShadow: "0 0 20px rgba(99,102,241,0.15)",
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(99,102,241,0.3)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "linear-gradient(135deg, rgba(99,102,241,0.25) 0%, rgba(99,102,241,0.12) 100%)"; }}
              >
                {uploadFile && extraction ? "Review Extracted Data →" : "Generate Structures →"}
              </button>
            </div>
          </form>
        )}

        {/* ── STEP 2: EXTRACTION PREVIEW ── */}
        {step === 2 && extraction && (
          <div className="space-y-5">
            <Card>
              <h2 className="text-base font-semibold mb-4" style={{ color: "#818cf8" }}>
                Extracted Document Data — Confirm Before Generation
              </h2>

              {extraction.ubo_info && (
                <div className="mb-4">
                  <p className="text-xs font-semibold uppercase tracking-widest mb-2" style={{ color: "#64748b" }}>
                    Ownership Chain Summary
                  </p>
                  <p className="text-sm leading-relaxed" style={{ color: "#cbd5e1" }}>
                    {extraction.ubo_info.ownership_chain_summary || "—"}
                  </p>
                </div>
              )}

              {(extraction.ubo_info?.ultimate_beneficial_owners?.length ?? 0) > 0 && (
                <div>
                  <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#64748b" }}>
                    UBO Entities
                  </p>
                  <div className="space-y-2">
                    {(extraction.ubo_info?.ultimate_beneficial_owners ?? []).map((ubo, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between px-4 py-3 rounded-xl"
                        style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)" }}
                      >
                        <div>
                          <p className="text-sm font-medium" style={{ color: "#f1f1f8" }}>{ubo.name}</p>
                          <p className="text-xs" style={{ color: "#64748b" }}>{ubo.jurisdiction} · {ubo.entity_type}</p>
                        </div>
                        <span className="text-sm font-bold" style={{ color: "#818cf8" }}>{ubo.ownership_pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {!extraction.ubo_info && extraction.raw_preview && (
                <pre className="text-xs overflow-auto max-h-48" style={{ color: "#94a3b8", lineHeight: 1.6 }}>
                  {extraction.raw_preview}
                </pre>
              )}
            </Card>

            <div className="flex gap-3">
              <button
                onClick={() => setStep(1)}
                className="flex-1 py-3 rounded-xl text-sm font-medium"
                style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", color: "#94a3b8", cursor: "pointer" }}
              >
                ← Back
              </button>
              <button
                id="btn-confirm-extraction"
                onClick={generateStructures}
                className="flex-1 py-3 rounded-xl text-sm font-semibold"
                style={{
                  background: "rgba(99,102,241,0.2)",
                  border: "1.5px solid rgba(99,102,241,0.4)",
                  color: "#a5b4fc",
                  cursor: "pointer",
                }}
              >
                Confirm & Generate →
              </button>
            </div>
          </div>
        )}

        {/* ── STEP 3: GENERATING ── */}
        {step === 3 && (
          <Card>
            <div className="flex flex-col items-center gap-6 py-8">
              {genError ? (
                <div className="text-center">
                  <p className="text-base font-semibold mb-2" style={{ color: "#f87171" }}>Generation Failed</p>
                  <p className="text-sm mb-5" style={{ color: "#94a3b8" }}>{genError}</p>
                  <button
                    onClick={() => { setStep(1); setGenError(null); }}
                    className="px-5 py-2.5 rounded-xl text-sm font-medium"
                    style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", color: "#818cf8", cursor: "pointer" }}
                  >
                    ← Try Again
                  </button>
                </div>
              ) : (
                <>
                  <div
                    className="w-16 h-16 rounded-2xl flex items-center justify-center"
                    style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.25)" }}
                  >
                    <svg className="animate-spin" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="2">
                      <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
                    </svg>
                  </div>
                  <div className="text-center">
                    <p className="text-base font-semibold mb-1" style={{ color: "#f1f1f8" }}>Generating Structures…</p>
                    <p className="text-sm" style={{ color: "#64748b" }}>
                      Querying RAG corpus · Running LLM cascade · Evaluating compliance
                    </p>
                  </div>
                  <div className="w-full max-w-xs">
                    <div className="h-1 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                      <div
                        className="h-full rounded-full"
                        style={{
                          background: "linear-gradient(90deg, #6366f1, #818cf8)",
                          animation: "progress-indeterminate 1.5s ease-in-out infinite",
                          width: "60%",
                        }}
                      />
                    </div>
                  </div>
                </>
              )}
            </div>
          </Card>
        )}
      </div>

      <style jsx>{`
        @keyframes progress-indeterminate {
          0%   { transform: translateX(-100%); }
          100% { transform: translateX(260%); }
        }
      `}</style>
    </div>
  );
}
