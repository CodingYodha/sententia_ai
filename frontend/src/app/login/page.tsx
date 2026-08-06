"use client";

/**
 * Login page — email/password + Google OAuth sign-in and sign-up.
 * Redirects authenticated users to /intake immediately.
 * PRD FR-7.1: Supabase Auth wiring.
 */

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../components/AuthContext";

type Mode = "signin" | "signup" | "reset";

export default function LoginPage() {
  const router = useRouter();
  const { session, loading, signInWithEmail, signInWithGoogle, signUp, resetPassword, error: authError } = useAuth();

  const [mode,      setMode]     = useState<Mode>("signin");
  const [email,     setEmail]    = useState("");
  const [password,  setPassword] = useState("");
  const [fullName,  setFN]       = useState("");
  const [submitting, setSub]     = useState(false);
  const [localErr,  setLocalErr] = useState<string | null>(null);
  const [resetSent, setResetSent]= useState(false);

  // Redirect already-authenticated users
  useEffect(() => {
    if (!loading && session) router.replace("/intake");
  }, [session, loading, router]);

  const error = localErr || authError;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLocalErr(null);
    setSub(true);

    if (mode === "reset") {
      const err = await resetPassword(email);
      if (!err) setResetSent(true);
      else setLocalErr(err);
      setSub(false);
      return;
    }

    const err =
      mode === "signin"
        ? await signInWithEmail(email, password)
        : await signUp(email, password, fullName);

    if (err) setLocalErr(err);
    setSub(false);
  }

  async function handleGoogle() {
    setLocalErr(null);
    setSub(true);
    const err = await signInWithGoogle();
    if (err) { setLocalErr(err); setSub(false); }
  }

  const inputStyle: React.CSSProperties = {
    width: "100%", padding: "11px 14px", borderRadius: "10px", fontSize: "14px",
    background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)",
    color: "#f1f1f8", outline: "none",
  };

  if (loading) return null;

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{
        background: `
          radial-gradient(ellipse 60% 40% at 50% -10%, rgba(99,102,241,0.18) 0%, transparent 70%),
          #0a0a0f
        `,
      }}
    >
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8">
          <div
            className="w-12 h-12 rounded-2xl flex items-center justify-center mb-4"
            style={{ background: "rgba(99,102,241,0.15)", border: "1px solid rgba(99,102,241,0.3)", boxShadow: "0 0 32px rgba(99,102,241,0.2)" }}
          >
            <svg width="22" height="22" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <path d="M6 24L16 8L26 24" stroke="#818cf8" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M9.5 19h13" stroke="#6366f1" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <h1 className="text-xl font-bold" style={{ color: "#f1f1f8" }}>
            Sententia<span style={{ color: "#818cf8" }}>.ai</span>
          </h1>
          <p className="text-sm mt-1" style={{ color: "#64748b" }}>
            Cross-Border Fund Structuring Platform
          </p>
        </div>

        {/* Card */}
        <div
          className="rounded-2xl p-8"
          style={{
            background:  "rgba(255,255,255,0.025)",
            border:      "1px solid rgba(255,255,255,0.08)",
            boxShadow:   "0 8px 48px rgba(0,0,0,0.5)",
          }}
        >
          {/* Mode tabs */}
          <div className="flex gap-1 mb-6 p-1 rounded-xl" style={{ background: "rgba(255,255,255,0.04)" }}>
            {(["signin", "signup"] as const).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setLocalErr(null); setResetSent(false); }}
                className="flex-1 py-2 rounded-lg text-sm font-medium transition-all"
                style={{
                  background: mode === m ? "rgba(99,102,241,0.2)" : "transparent",
                  color:      mode === m ? "#818cf8" : "#64748b",
                  border:     mode === m ? "1px solid rgba(99,102,241,0.3)" : "1px solid transparent",
                }}
              >
                {m === "signin" ? "Sign In" : "Create Account"}
              </button>
            ))}
          </div>

          {/* Password reset success */}
          {resetSent && (
            <div
              className="rounded-xl p-4 mb-5 text-sm text-center"
              style={{ background: "rgba(52,211,153,0.07)", border: "1px solid rgba(52,211,153,0.2)", color: "#6ee7b7" }}
            >
              Reset link sent — check your email.
              <button className="block mx-auto mt-2 underline text-xs" style={{ color: "#64748b" }} onClick={() => { setMode("signin"); setResetSent(false); }}>
                Back to Sign In
              </button>
            </div>
          )}

          {/* Form */}
          {!resetSent && (
            <form onSubmit={handleSubmit} noValidate>
              <div className="space-y-4">

                {/* Full name — sign up only */}
                {mode === "signup" && (
                  <div>
                    <label className="block text-xs font-semibold uppercase tracking-widest mb-1.5" style={{ color: "#64748b" }}>
                      Full Name
                    </label>
                    <input
                      id="input-full-name"
                      type="text"
                      autoComplete="name"
                      value={fullName}
                      onChange={(e) => setFN(e.target.value)}
                      placeholder="Your name"
                      style={inputStyle}
                    />
                  </div>
                )}

                {/* Email */}
                <div>
                  <label className="block text-xs font-semibold uppercase tracking-widest mb-1.5" style={{ color: "#64748b" }}>
                    Work Email <span style={{ color: "#f87171" }}>*</span>
                  </label>
                  <input
                    id="input-email"
                    type="email"
                    autoComplete="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@lawfirm.com"
                    style={inputStyle}
                  />
                </div>

                {/* Password — not shown in reset mode */}
                {mode !== "reset" && (
                  <div>
                    <div className="flex items-center justify-between mb-1.5">
                      <label className="text-xs font-semibold uppercase tracking-widest" style={{ color: "#64748b" }}>
                        Password <span style={{ color: "#f87171" }}>*</span>
                      </label>
                      {mode === "signin" && (
                        <button
                          type="button"
                          onClick={() => setMode("reset")}
                          className="text-xs underline"
                          style={{ color: "#64748b", background: "none", border: "none", cursor: "pointer" }}
                        >
                          Forgot?
                        </button>
                      )}
                    </div>
                    <input
                      id="input-password"
                      type="password"
                      autoComplete={mode === "signin" ? "current-password" : "new-password"}
                      required
                      minLength={8}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder={mode === "signup" ? "Min. 8 characters" : "Your password"}
                      style={inputStyle}
                    />
                  </div>
                )}

                {/* Error */}
                {error && (
                  <div className="rounded-lg p-3 text-xs" style={{ background: "rgba(248,113,113,0.07)", border: "1px solid rgba(248,113,113,0.2)", color: "#fca5a5" }}>
                    {error}
                  </div>
                )}

                {/* Submit */}
                <button
                  id="btn-auth-submit"
                  type="submit"
                  disabled={submitting || !email}
                  className="w-full py-3 rounded-xl text-sm font-semibold transition-all"
                  style={{
                    background:  submitting ? "rgba(99,102,241,0.1)" : "rgba(99,102,241,0.2)",
                    border:      "1.5px solid rgba(99,102,241,0.4)",
                    color:       "#a5b4fc",
                    cursor:      submitting ? "not-allowed" : "pointer",
                    boxShadow:   "0 0 20px rgba(99,102,241,0.12)",
                  }}
                >
                  {submitting ? "…" : mode === "signin" ? "Sign In" : mode === "signup" ? "Create Account" : "Send Reset Link"}
                </button>
              </div>
            </form>
          )}

          {/* Google OAuth — not on reset */}
          {mode !== "reset" && !resetSent && (
            <>
              <div className="flex items-center gap-3 my-5">
                <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.07)" }}/>
                <span className="text-xs" style={{ color: "#475569" }}>or</span>
                <div className="flex-1 h-px" style={{ background: "rgba(255,255,255,0.07)" }}/>
              </div>

              <button
                id="btn-google-oauth"
                onClick={handleGoogle}
                disabled={submitting}
                className="w-full flex items-center justify-center gap-3 py-3 rounded-xl text-sm font-medium transition-all"
                style={{
                  background: "rgba(255,255,255,0.04)",
                  border:     "1px solid rgba(255,255,255,0.1)",
                  color:      "#cbd5e1",
                  cursor:     submitting ? "not-allowed" : "pointer",
                }}
                onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)"; }}
                onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.04)"; }}
              >
                {/* Google icon */}
                <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </button>
            </>
          )}
        </div>

        {/* Legal note */}
        <p className="text-center text-xs mt-6" style={{ color: "#475569" }}>
          By signing in you agree to our Terms of Service and Privacy Policy.
          <br />
          All activity is logged per FR-7.3.
        </p>
      </div>
    </div>
  );
}
