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
      className="fixed top-0 inset-x-0 z-50 flex items-center justify-between px-6 h-16"
      style={{
        background:    "rgba(245, 245, 245, 0.92)",
        backdropFilter:"blur(12px)",
        borderBottom:  "1px solid #e7e5e4",
      }}
    >
      {/* Logo */}
      <Link href="/" className="flex items-center shrink-0 group">
        <span className="text-lg font-editorial-display font-semibold tracking-tight" style={{ color: "#0c0a09" }}>
          Sententia<span style={{ color: "#777169", fontFamily: "var(--font-sans-family)", fontSize: "14px", fontWeight: 500 }}>.ai</span>
        </span>
      </Link>


      {/* Nav links */}
      <div className="flex items-center gap-1.5">
        {links.map((link) => {
          if (link.perm && !can(link.perm)) return null;
          const active = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className="px-3.5 py-1.5 rounded-full text-sm font-medium transition-all"
              style={{
                color:      active ? "#0c0a09" : "#4e4e4e",
                background: active ? "#f0efed" : "transparent",
                fontWeight: active ? 600 : 500,
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
            <span className="text-xs hidden md:block" style={{ color: "#777169" }}>
              {profile.email}
            </span>
            <button
              id="btn-sign-out"
              onClick={handleSignOut}
              disabled={signingOut}
              className="px-3.5 py-1.5 rounded-full text-xs font-medium transition-all"
              style={{
                background: "#f0efed",
                border:     "1px solid #e7e5e4",
                color:      "#292524",
                cursor:     signingOut ? "not-allowed" : "pointer",
              }}
            >
              {signingOut ? "…" : "Sign Out"}
            </button>
          </>
        ) : isLoggedIn ? (
          // Session but profile not yet loaded
          <span className="text-xs" style={{ color: "#777169" }}>Loading…</span>
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
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#777169" strokeWidth="2" aria-hidden="true">
                    <polyline points="6 9 12 15 18 9"/>
                  </svg>
                </button>

                {rolePicker && (
                  <div
                    className="absolute right-0 mt-2 w-56 rounded-2xl overflow-hidden p-1.5"
                    style={{
                      background: "#ffffff",
                      border:     "1px solid #e7e5e4",
                      boxShadow:  "0 12px 32px rgba(0,0,0,0.08)",
                    }}
                  >
                    <div className="px-3 py-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400 border-b border-stone-100 mb-1">
                      Dev mode role switcher
                    </div>
                    {ALL_ROLES.map((r) => (
                      <button
                        key={r}
                        onClick={() => { setRole(r); setRolePicker(false); }}
                        className="w-full flex items-center justify-between px-3 py-2 rounded-xl text-xs hover:bg-stone-100 transition-colors"
                        style={{ color: r === role ? "#0c0a09" : "#4e4e4e" }}
                      >
                        <RoleBadge role={r} />
                        {r === role && (
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#0c0a09" strokeWidth="2.5">
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
              className="btn-primary"
            >
              Sign In
            </Link>
          </>
        )}
      </div>
    </nav>
  );
}
