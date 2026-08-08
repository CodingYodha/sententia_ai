"use client";

import { useRef, useState } from "react";
import { useAuth } from "../components/AuthContext";
import { useRouter } from "next/navigation";
import { useRole } from "../components/RBACContext";

import { apiIntakeDocument, apiIntakeScenario, apiStructuresGenerate } from "@/lib/api";

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

const SECTORS = [
  "Education (K-12 & Higher Ed)", "Technology & Software", "Financial Services", "Infrastructure", "Real Estate",
  "Healthcare & Pharma", "Energy & Renewables", "Manufacturing", "E-Commerce & Retail",
  "Defence & Aerospace", "Agriculture & Food", "Telecom & Media", "Other",
];

const JURISDICTIONS = [
  "United States", "India", "Singapore", "Delaware (US)", "United Kingdom",
  "Germany", "France", "Netherlands", "Luxembourg", "Cayman Islands",
  "Mauritius", "UAE (Dubai)", "Japan", "South Korea", "Brazil", "Australia",
  "Hong Kong", "British Virgin Islands", "Cyprus", "Switzerland", "Other",
];

const INITIAL: ScenarioFormData = {
  investor_name: "Meridian Grace Foundation & Atlas Education Partners",
  origin_jurisdiction: "United States",
  target_jurisdiction: "India",
  spv_jurisdiction: "Delaware (US)",
  sector: "Education (K-12 & Higher Ed)",
  investment_amount_usd: "3000000",
  equity_pct: "100",
  has_us_persons_in_fund: true,
  is_prohibited_sector: false,
  prior_govt_approval_obtained: false,
  additional_context: "Project Ananta — US-to-India FDI into K-12 school infrastructure (PropCo) and educational management services (OpCo).",
};

export default function IntakePage() {
  const { can } = useRole();
  const router  = useRouter();
  const { accessToken } = useAuth();

  const [form, setForm]             = useState<ScenarioFormData>(INITIAL);
  const [errors, setErrors]         = useState<FormErrors>({});
  const [serverError, setServerError] = useState<string | null>(null);

  // Document upload state
  const [uploadFile, setUploadFile]       = useState<File | null>(null);
  const [uploading, setUploading]         = useState(false);
  const [uploadError, setUploadError]     = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  function setField(k: keyof ScenarioFormData, v: string | boolean) {
    setForm((f) => ({ ...f, [k]: v }));
    setErrors((e) => { const n = { ...e }; delete n[k]; return n; });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setServerError(null);

    const scenarioPayload = {
      investor_name: form.investor_name || "Meridian Grace Foundation",
      capital_origin: form.origin_jurisdiction || "United States",
      target_jurisdiction: form.target_jurisdiction || "India",
      spv_jurisdiction: form.spv_jurisdiction || "Delaware (US)",
      sector: form.sector || "Education",
      investment_amount_usd: Number(form.investment_amount_usd) || 3000000,
      equity_pct: form.equity_pct ? Number(form.equity_pct) : 100,
      investment_structure_type: "spv_layered",
      regulatory_constraints: form.has_us_persons_in_fund ? ["fund_has_us_persons"] : [],
      notes: form.additional_context || "Project Ananta PropCo-OpCo Model",
    };

    // Store draft scenario payload in sessionStorage and navigate immediately to /results
    // The results page will handle the 5-8 second streaming reasoning feed!
    sessionStorage.setItem("sententia_draft_scenario", JSON.stringify(scenarioPayload));
    router.push("/results?generating=true");
  }

  return (
    <div className="min-h-screen pt-24 pb-16 px-4 bg-stone-50/50">
      <div className="max-w-3xl mx-auto space-y-6">

        {/* Page header */}
        <div>
          <h1 className="text-3xl font-editorial-display font-bold text-stone-900">
            New Scenario
          </h1>
          <p className="text-xs font-editorial-body text-stone-500 mt-1">
            Specify investor profile, jurisdictions, and deal parameters to run the structuring simulation.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Card 1: Investor Details */}
          <div className="bg-white rounded-2xl border border-stone-200 p-6 space-y-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-stone-700 font-mono">
              Investor Details
            </h2>
            <div>
              <label className="block text-xs font-medium text-stone-600 mb-1">
                Investor / Entity Name <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={form.investor_name}
                onChange={(e) => setField("investor_name", e.target.value)}
                placeholder="Director / Natural Address / Entity Name"
                className="w-full bg-stone-50 border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-stone-900 outline-none focus:border-stone-900 transition-colors"
              />
            </div>
            <label className="flex items-center gap-2 cursor-pointer pt-1">
              <input
                type="checkbox"
                checked={form.has_us_persons_in_fund}
                onChange={(e) => setField("has_us_persons_in_fund", e.target.checked)}
                className="rounded border-stone-300 text-stone-900 focus:ring-stone-900"
              />
              <span className="text-xs font-editorial-body text-stone-600">
                Structure Architecture (Include US Investor Compliance)
              </span>
            </label>
          </div>

          {/* Card 2: Jurisdictions */}
          <div className="bg-white rounded-2xl border border-stone-200 p-6 space-y-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-stone-700 font-mono">
              Jurisdictions
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="block text-xs font-medium text-stone-600 mb-1">
                  Origin <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.origin_jurisdiction}
                  onChange={(e) => setField("origin_jurisdiction", e.target.value)}
                  className="w-full bg-stone-50 border border-stone-200 rounded-xl px-3 py-2.5 text-sm text-stone-900 outline-none focus:border-stone-900"
                >
                  {JURISDICTIONS.map((j) => <option key={j} value={j}>{j}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-stone-600 mb-1">
                  Target <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.target_jurisdiction}
                  onChange={(e) => setField("target_jurisdiction", e.target.value)}
                  className="w-full bg-stone-50 border border-stone-200 rounded-xl px-3 py-2.5 text-sm text-stone-900 outline-none focus:border-stone-900"
                >
                  {JURISDICTIONS.map((j) => <option key={j} value={j}>{j}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-stone-600 mb-1">
                  SPV <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.spv_jurisdiction}
                  onChange={(e) => setField("spv_jurisdiction", e.target.value)}
                  className="w-full bg-stone-50 border border-stone-200 rounded-xl px-3 py-2.5 text-sm text-stone-900 outline-none focus:border-stone-900"
                >
                  {JURISDICTIONS.map((j) => <option key={j} value={j}>{j}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-600 mb-1">
                Goal / Structure Parameter
              </label>
              <input
                type="text"
                value="PropCo-OpCo FDI Lease & Educational Services Model"
                readOnly
                className="w-full bg-stone-100 border border-stone-200 rounded-xl px-4 py-2.5 text-xs text-stone-600 outline-none cursor-not-allowed font-mono"
              />
            </div>
          </div>

          {/* Card 3: Deal Parameters */}
          <div className="bg-white rounded-2xl border border-stone-200 p-6 space-y-4 shadow-sm">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-stone-700 font-mono">
              Deal Parameters
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-stone-600 mb-1">
                  Sector <span className="text-red-500">*</span>
                </label>
                <select
                  value={form.sector}
                  onChange={(e) => setField("sector", e.target.value)}
                  className="w-full bg-stone-50 border border-stone-200 rounded-xl px-3 py-2.5 text-sm text-stone-900 outline-none focus:border-stone-900"
                >
                  {SECTORS.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-stone-600 mb-1">
                  Investment Amount (USD) <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={form.investment_amount_usd}
                  onChange={(e) => setField("investment_amount_usd", e.target.value)}
                  placeholder="$3,000,000"
                  className="w-full bg-stone-50 border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-stone-900 outline-none focus:border-stone-900"
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-stone-600 mb-1">
                Additional Context / Notes
              </label>
              <textarea
                value={form.additional_context}
                onChange={(e) => setField("additional_context", e.target.value)}
                rows={2}
                placeholder="Project Ananta PropCo-OpCo structuring parameters"
                className="w-full bg-stone-50 border border-stone-200 rounded-xl px-4 py-2.5 text-sm text-stone-900 outline-none focus:border-stone-900 resize-none"
              />
            </div>
          </div>

          {/* Form Action Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={() => router.push("/")}
              className="px-6 py-2.5 rounded-xl border border-stone-200 text-sm font-medium text-stone-700 bg-white hover:bg-stone-50 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 rounded-xl text-sm font-medium text-white bg-stone-900 hover:bg-stone-800 transition-colors shadow-sm"
            >
              Generate Structure →
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
