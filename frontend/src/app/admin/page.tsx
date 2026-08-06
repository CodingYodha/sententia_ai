"use client";

/**
 * Admin page — stub for Prompt 9 full auth wiring.
 * Shows system stats and links to audit log.
 * Accessible only to admin role.
 */

import { useRole } from "../components/RBACContext";

export default function AdminPage() {
  const { can, role } = useRole();

  if (!can("admin:read")) {
    return (
      <div className="min-h-screen pt-28 flex flex-col items-center justify-center px-4">
        <div
          className="max-w-md w-full rounded-2xl p-10 text-center"
          style={{ background: "rgba(245,158,11,0.05)", border: "1px solid rgba(245,158,11,0.2)" }}
        >
          <p className="text-base font-semibold mb-2" style={{ color: "#f59e0b" }}>Admin Access Required</p>
          <p className="text-sm mb-4" style={{ color: "#94a3b8" }}>
            Switch to Admin role in the navigation to access this page.
            <br />
            <span className="text-xs" style={{ color: "#64748b" }}>
              (Full auth wiring ships in Prompt 9)
            </span>
          </p>
          <p className="text-xs" style={{ color: "#64748b" }}>
            Current role: <strong style={{ color: "#818cf8" }}>{role}</strong>
          </p>
        </div>
      </div>
    );
  }

  const cards = [
    { label: "Auth Provider",    value: "Stub (Prompt 9)",    color: "#f59e0b" },
    { label: "RAG Corpus",       value: "Qdrant (local)",     color: "#818cf8" },
    { label: "Audit Log",        value: "Supabase audit_log", color: "#34d399" },
    { label: "OPA Policies",     value: "3 corridors loaded", color: "#818cf8" },
    { label: "LLM Fallback",     value: "OpenRouter → Groq",  color: "#94a3b8" },
    { label: "Diagram Engine",   value: "Mermaid.js v11",     color: "#818cf8" },
  ];

  return (
    <div className="min-h-screen pt-24 pb-16 px-4 relative z-10">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h1 className="text-4xl font-editorial-display text-stone-900 mb-3">
            Admin Dashboard
          </h1>
          <div className="badge-pill bg-amber-50 text-amber-800 border-amber-200">
            ⚠ Auth stub — full wiring in Prompt 9
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          {cards.map(({ label, value, color }) => (
            <div
              key={label}
              className="card-editorial px-6 py-5"
            >
              <p className="text-xs font-semibold uppercase tracking-wider text-stone-500 mb-1">{label}</p>
              <p className="text-base font-editorial-display font-medium text-stone-900">{value}</p>
            </div>
          ))}
        </div>

        <div className="card-editorial p-6">
          <p className="text-xs font-semibold uppercase tracking-widest mb-4 text-stone-500">Prompt 9 — Auth Wiring Checklist</p>
          {[
            "Replace localStorage role stub with JWT from auth provider",
            "Wire review queue to real user identities",
            "Add rate-limiting middleware per user",
            "Implement audit log viewer with filter/export",
            "Add SSO / SAML integration for enterprise users",
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2.5 py-2 text-sm font-editorial-body text-stone-700 border-b border-stone-100 last:border-0">
              <span className="text-stone-400 font-bold">□</span>
              {item}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
