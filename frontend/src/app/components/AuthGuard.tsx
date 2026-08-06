"use client";

/**
 * AuthGuard — Redirects unauthenticated users to /login.
 * Reads auth state from AuthContext, shows a loading spinner during hydration.
 * Used by wrapping page content that requires a valid Supabase session.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "./AuthContext";
import type { AppRole } from "./AuthContext";

interface AuthGuardProps {
  children: React.ReactNode;
  /** If provided, redirect to /login if user's role is not in this list */
  requiredRoles?: AppRole[];
  /** If true, renders children immediately (public page) */
  isPublic?: boolean;
}

export function AuthGuard({ children, requiredRoles, isPublic = false }: AuthGuardProps) {
  const { session, profile, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading || isPublic) return;
    if (!session) { router.replace("/login"); return; }
    if (requiredRoles && profile && !requiredRoles.includes(profile.role)) {
      router.replace("/"); // Redirect to dashboard on insufficient role
    }
  }, [session, profile, loading, router, requiredRoles, isPublic]);

  if (isPublic) return <>{children}</>;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div
            className="w-12 h-12 rounded-xl flex items-center justify-center"
            style={{ background: "rgba(99,102,241,0.1)", border: "1px solid rgba(99,102,241,0.2)" }}
          >
            <svg className="animate-spin" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#818cf8" strokeWidth="2">
              <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
            </svg>
          </div>
          <p className="text-sm" style={{ color: "#64748b" }}>Authenticating…</p>
        </div>
      </div>
    );
  }

  if (!session) return null; // Will redirect via useEffect

  if (requiredRoles && profile && !requiredRoles.includes(profile.role)) {
    return (
      <div className="min-h-screen pt-28 flex flex-col items-center justify-center px-4">
        <div
          className="max-w-md w-full rounded-2xl p-10 text-center"
          style={{ background: "rgba(248,113,113,0.05)", border: "1px solid rgba(248,113,113,0.2)" }}
        >
          <p className="text-base font-semibold mb-2" style={{ color: "#f87171" }}>Insufficient Permissions</p>
          <p className="text-sm" style={{ color: "#94a3b8" }}>
            This page requires role: <strong>{requiredRoles.join(" or ")}</strong>.<br />
            Your role: <strong style={{ color: "#818cf8" }}>{profile.role}</strong>.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
