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
    <div className="min-h-screen pt-24 pb-16 px-4">
      <div className="max-w-3xl mx-auto">
        <div className="mb-8">
          <h1
            className="text-3xl font-bold mb-2"
            style={{
              background: "linear-gradient(135deg, #f1f1f8 30%, #f59e0b 100%)",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
            }}
          >
            Admin Dashboard
          </h1>
          <div
            className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs"
            style={{ background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.2)", color: "#f59e0b" }}
          >
            ⚠ Auth stub — full wiring in Prompt 9
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
          {cards.map(({ label, value, color }) => (
            <div
              key={label}
              className="rounded-xl px-5 py-4"
              style={{ background: "rgba(255,255,255,0.025)", border: "1px solid rgba(255,255,255,0.07)" }}
            >
              <p className="text-xs" style={{ color: "#64748b" }}>{label}</p>
              <p className="text-sm font-semibold mt-0.5" style={{ color }}>{value}</p>
            </div>
          ))}
        </div>

        <div
          className="rounded-xl p-5"
          style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}
        >
          <p className="text-xs font-semibold uppercase tracking-widest mb-3" style={{ color: "#64748b" }}>Prompt 9 — Auth Wiring Checklist</p>
          {[
            "Replace localStorage role stub with JWT from auth provider",
            "Wire review queue to real user identities",
            "Add rate-limiting middleware per user",
            "Implement audit log viewer with filter/export",
            "Add SSO / SAML integration for enterprise users",
          ].map((item, i) => (
            <div key={i} className="flex items-center gap-2 py-1.5 text-sm" style={{ color: "#64748b" }}>
              <span style={{ color: "#475569" }}>□</span>
              {item}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
