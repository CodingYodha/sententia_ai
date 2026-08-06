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
    width: "100%", padding: "12px 16px", borderRadius: "12px", fontSize: "14px",
    background: "#ffffff", border: "1px solid #d6d3d1",
    color: "#0c0a09", outline: "none",
  };

  if (loading) return null;

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-12 relative z-10"
    >
      <div className="w-full max-w-md">

        {/* Logo */}
        <div className="flex flex-col items-center mb-8 text-center">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-4 bg-stone-900 shadow-md">
            <svg width="22" height="22" viewBox="0 0 32 32" fill="none" aria-hidden="true">
              <path d="M6 24L16 8L26 24" stroke="#ffffff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M9.5 19h13" stroke="#d6d3d1" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </div>
          <h1 className="text-3xl font-editorial-display text-stone-900">
            Sententia<span className="text-stone-500">.ai</span>
          </h1>
          <p className="text-sm font-editorial-body text-stone-600 mt-1">
            Cross-Border Fund Structuring Platform
          </p>
        </div>

        {/* Card */}
        <div className="card-editorial p-8 shadow-sm">
          {/* Mode tabs */}
          <div className="flex gap-1.5 mb-6 p-1 rounded-full bg-stone-100">
            {(["signin", "signup"] as const).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setLocalErr(null); setResetSent(false); }}
                className="flex-1 py-2 rounded-full text-xs font-semibold transition-all"
                style={{
                  background: mode === m ? "#0c0a09" : "transparent",
                  color:      mode === m ? "#ffffff" : "#777169",
                }}
              >
                {m === "signin" ? "Sign In" : "Create Account"}
              </button>
            ))}
          </div>

          {/* Password reset success */}
          {resetSent && (
            <div className="rounded-2xl p-4 mb-5 text-sm text-center bg-emerald-50 border border-emerald-200 text-emerald-800 font-medium">
              Reset link sent — check your email.
              <button className="block mx-auto mt-2 underline text-xs text-stone-600" onClick={() => { setMode("signin"); setResetSent(false); }}>
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
                    <label className="block text-xs font-semibold uppercase tracking-widest mb-1.5 text-stone-600">
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
                  <label className="block text-xs font-semibold uppercase tracking-widest mb-1.5 text-stone-600">
                    Work Email <span className="text-red-500">*</span>
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
                      <label className="text-xs font-semibold uppercase tracking-widest text-stone-600">
                        Password <span className="text-red-500">*</span>
                      </label>
                      {mode === "signin" && (
                        <button
                          type="button"
                          onClick={() => setMode("reset")}
                          className="text-xs underline text-stone-500 hover:text-stone-900"
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
                  <div className="rounded-xl p-3 text-xs bg-red-50 border border-red-200 text-red-700 font-medium">
                    {error}
                  </div>
                )}

                {/* Submit */}
                <button
                  id="btn-auth-submit"
                  type="submit"
                  disabled={submitting || !email}
                  className="btn-primary w-full py-3.5 text-sm font-semibold justify-center mt-2"
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
                <div className="flex-1 h-px bg-stone-200" />
                <span className="text-xs font-editorial-body text-stone-400">or</span>
                <div className="flex-1 h-px bg-stone-200" />
              </div>

              <button
                id="btn-google-oauth"
                onClick={handleGoogle}
                disabled={submitting}
                className="btn-outline w-full justify-center py-3 text-sm"
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
        <p className="text-center text-xs font-editorial-body text-stone-500 mt-6 leading-relaxed">
          By signing in you agree to our Terms of Service and Privacy Policy.
          <br />
          All activity is logged per FR-7.3.
        </p>
      </div>
    </div>
  );
}
