"use client";

/**
 * OAuth callback handler — /auth/callback
 *
 * Supabase redirects here after Google OAuth completes.
 * The Supabase client detects the session from the URL hash automatically
 * (detectSessionInUrl: true). We just wait for the session, then redirect.
 */

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../components/AuthContext";

export default function AuthCallbackPage() {
  const router = useRouter();
  const { session, loading } = useAuth();
  const [exchangeStarted, setExchangeStarted] = useState(false);

  useEffect(() => {
    // Prevent premature redirect if Supabase is still exchanging the PKCE code in the background
    if (typeof window !== "undefined" && window.location.search.includes("code=")) {
      setExchangeStarted(true);
    }
    
    // Only redirect if auth context has finished loading AND we aren't waiting on a code exchange that hasn't fired yet
    if (!loading) {
      if (session) {
        router.replace("/intake");
      } else if (!exchangeStarted) {
        router.replace("/login");
      }
    }
  }, [session, loading, router, exchangeStarted]);

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
