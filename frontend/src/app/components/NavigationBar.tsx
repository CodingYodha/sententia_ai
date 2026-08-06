"use client";

/**
 * NavigationBar — Top navigation with real auth state + RBAC-aware links.
 *
 * When Supabase is configured and user is logged in:
 *   - Shows user email + real role badge (immutable)
 *   - Sign Out button
 *   - Dispatches "sententia:profile" event so RBACContext reads real role
 *
 * When running without Supabase (dev/demo mode):
 *   - Shows dev-mode role switcher (localStorage stub)
 */

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "./AuthContext";
import { RoleBadge, useRole, type Role } from "./RBACContext";

const ALL_ROLES: Role[] = ["associate", "reviewer", "compliance_officer", "admin"];

export function NavigationBar() {
  const pathname  = usePathname();
  const router    = useRouter();
  const { session, profile, signOut } = useAuth();
  const { role, setRole, can, isDevMode } = useRole();
  const [rolePicker, setRolePicker] = useState(false);
  const [signingOut, setSO]         = useState(false);

  // Bridge: dispatch profile event so RBACContext reads the real role
  useEffect(() => {
    if (profile?.role) {
      window.dispatchEvent(
        new CustomEvent("sententia:profile", { detail: { role: profile.role } })
      );
    }
  }, [profile?.role]);

  const isLoggedIn = !!session;

  const links = [
    { href: "/",        label: "Dashboard",     always: true },
    { href: "/intake",  label: "New Scenario",  perm: "intake:submit"    as const },
    { href: "/review",  label: "Review Queue",  perm: "review:read"      as const },
    { href: "/admin",   label: "Admin",         perm: "admin:read"       as const },
  ];

  async function handleSignOut() {
    setSO(true);
    await signOut();
    router.replace("/login");
  }

  return (
    <nav
      className="fixed top-0 inset-x-0 z-50 flex items-center justify-between px-6 h-14"
      style={{
        background:    "rgba(10,10,15,0.88)",
        backdropFilter:"blur(12px)",
        borderBottom:  "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center gap-2.5 shrink-0">
        <span
          className="w-7 h-7 rounded-lg flex items-center justify-center"
          style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)" }}
        >
          <svg width="14" height="14" viewBox="0 0 32 32" fill="none" aria-hidden="true">
            <path d="M6 24L16 8L26 24" stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
            <path d="M9.5 19h13" stroke="#6366f1" strokeWidth="2" strokeLinecap="round"/>
          </svg>
        </span>
        <span className="text-sm font-semibold" style={{ color: "#f1f1f8" }}>
          Sententia<span style={{ color: "#818cf8" }}>.ai</span>
        </span>
      </Link>

      {/* Nav links */}
      <div className="flex items-center gap-1">
        {links.map((link) => {
          if (link.perm && !can(link.perm)) return null;
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="px-3 py-1.5 rounded-lg text-sm font-medium transition-all"
              style={{
                color:      active ? "#818cf8" : "#64748b",
                background: active ? "rgba(99,102,241,0.1)" : "transparent",
              }}
            >
              {link.label}
            </Link>
          );
        })}
      </div>

      {/* Right: auth state */}
      <div className="flex items-center gap-3 shrink-0">

        {/* Authenticated user */}
        {isLoggedIn && profile ? (
          <>
            <RoleBadge role={profile.role as Role} />
            <span className="text-xs hidden md:block" style={{ color: "#475569" }}>
              {profile.email}
            </span>
            <button
              id="btn-sign-out"
              onClick={handleSignOut}
              disabled={signingOut}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
              style={{
                background: "rgba(248,113,113,0.07)",
                border:     "1px solid rgba(248,113,113,0.18)",
                color:      "#f87171",
                cursor:     signingOut ? "not-allowed" : "pointer",
              }}
            >
              {signingOut ? "…" : "Sign Out"}
            </button>
          </>
        ) : isLoggedIn ? (
          // Session but profile not yet loaded
          <span className="text-xs" style={{ color: "#64748b" }}>Loading…</span>
        ) : (
          // Not logged in
          <>
            {/* Dev-mode role switcher (visible only when no real auth) */}
            {isDevMode && (
              <div className="relative">
                <button
                  id="btn-dev-role-picker"
                  onClick={() => setRolePicker((v) => !v)}
                  className="flex items-center gap-1.5"
                  title="Dev mode — switch role (replaced by real auth in prod)"
                >
                  <RoleBadge role={role} />
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#64748b" strokeWidth="2" aria-hidden="true">
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </button>

                {rolePicker && (
                  <div
                    className="absolute right-0 mt-2 w-52 rounded-xl overflow-hidden"
                    style={{
                      background: "rgba(15,15,24,0.97)",
                      border:     "1px solid rgba(255,255,255,0.1)",
                      boxShadow:  "0 8px 32px rgba(0,0,0,0.5)",
                    }}
                  >
                    <div className="px-3 py-2 text-xs" style={{ color: "#64748b", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                      Dev mode role switcher
                    </div>
                    {ALL_ROLES.map((r) => (
                      <button
                        key={r}
                        onClick={() => { setRole(r); setRolePicker(false); }}
                        className="w-full flex items-center justify-between px-3 py-2 text-sm hover:bg-white/5 transition-colors"
                        style={{ color: r === role ? "#818cf8" : "#94a3b8" }}
                      >
                        <RoleBadge role={r} />
                        {r === role && (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="2.5">
                            <polyline points="20 6 9 17 4 12"/>
                          </svg>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}

            <Link
              href="/login"
              id="btn-sign-in"
              className="px-3 py-1.5 rounded-lg text-xs font-semibold"
              style={{
                background: "rgba(99,102,241,0.15)",
                border:     "1px solid rgba(99,102,241,0.3)",
                color:      "#818cf8",
              }}
            >
              Sign In
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
