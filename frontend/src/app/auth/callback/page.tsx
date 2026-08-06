"use client";

/**
 * OAuth callback handler — /auth/callback
 *
 * Supabase redirects here after Google OAuth completes.
 * The Supabase client detects the session from the URL hash automatically
 * (detectSessionInUrl: true). We just wait for the session, then redirect.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../components/AuthContext";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { session, loading } = useAuth();

  useEffect(() => {
    if (!loading) {
      router.replace(session ? "/intake" : "/login");
    }
  }, [session, loading, router]);

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
        <p className="text-sm" style={{ color: "#64748b" }}>Completing sign-in…</p>
      </div>
    </div>
  );
}
