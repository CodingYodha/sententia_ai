"use client";

/**
 * AuthContext — Supabase Auth session + user profile state.
 *
 * Provides:
 *   - session / user from Supabase Auth
 *   - profile (role, workspace) from public.users table
 *   - loading / error states
 *   - signIn / signUp / signOut / signInWithGoogle helpers
 *   - access_token for backend API calls (Authorization: Bearer)
 *
 * The RBACContext (Prompt 8) now reads role from profile instead of localStorage.
 * The role-switcher in NavigationBar is REMOVED in favour of real auth roles.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import type { Session, User } from "@supabase/supabase-js";
import { supabase } from "../../lib/supabaseClient";

// ── Types ──────────────────────────────────────────────────────────────────────

export type AppRole = "associate" | "reviewer" | "compliance_officer" | "admin";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string | null;
  role: AppRole;
  firm_workspace_id: string | null;
  is_active: boolean;
}

interface AuthContextValue {
  session:      Session | null;
  user:         User    | null;
  profile:      UserProfile | null;
  loading:      boolean;
  error:        string | null;
  accessToken:  string | null;

  signInWithEmail:   (email: string, password: string) => Promise<string | null>;
  signInWithGoogle:  () => Promise<string | null>;
  signUp:            (email: string, password: string, fullName?: string) => Promise<string | null>;
  signOut:           () => Promise<void>;
  resetPassword:     (email: string) => Promise<string | null>;
}

// ── Context ────────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue>({
  session: null, user: null, profile: null, loading: true,
  error: null, accessToken: null,
  signInWithEmail: async () => null,
  signInWithGoogle: async () => null,
  signUp: async () => null,
  signOut: async () => {},
  resetPassword: async () => null,
});

// ── Provider ───────────────────────────────────────────────────────────────────

async function fetchProfile(userId: string): Promise<UserProfile | null> {
  try {
    const { data, error } = await supabase
      .from("users")
      .select("id, email, full_name, role, firm_workspace_id, is_active")
      .eq("id", userId)
      .single();
    if (error || !data) return null;
    return data as UserProfile;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [session,     setSession]     = useState<Session | null>(null);
  const [user,        setUser]        = useState<User | null>(null);
  const [profile,     setProfile]     = useState<UserProfile | null>(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState<string | null>(null);
  const [accessToken, setAccessToken] = useState<string | null>(null);

  // Load initial session + subscribe to auth changes
  useEffect(() => {
    let mounted = true;

    async function init() {
      const { data: { session: s } } = await supabase.auth.getSession();
      if (!mounted) return;
      setSession(s);
      setUser(s?.user ?? null);
      setAccessToken(s?.access_token ?? null);
      if (s?.user) {
        const p = await fetchProfile(s.user.id);
        if (mounted) setProfile(p);
      }
      setLoading(false);
    }
    init();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (event, s) => {
      if (!mounted) return;
      setSession(s);
      setUser(s?.user ?? null);
      setAccessToken(s?.access_token ?? null);
      if (s?.user) {
        const p = await fetchProfile(s.user.id);
        if (mounted) setProfile(p);
      } else {
        setProfile(null);
      }
      setLoading(false);
    });

    return () => { mounted = false; subscription.unsubscribe(); };
  }, []);

  const signInWithEmail = useCallback(async (email: string, password: string) => {
    setError(null);
    const { error: e } = await supabase.auth.signInWithPassword({ email, password });
    if (e) { setError(e.message); return e.message; }
    return null;
  }, []);

  const signInWithGoogle = useCallback(async () => {
    setError(null);
    const { error: e } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (e) { setError(e.message); return e.message; }
    return null;
  }, []);

  const signUp = useCallback(async (email: string, password: string, fullName?: string) => {
    setError(null);
    const { error: e } = await supabase.auth.signUp({
      email,
      password,
      options: { data: { full_name: fullName } },
    });
    if (e) { setError(e.message); return e.message; }
    return null;
  }, []);

  const signOut = useCallback(async () => {
    await supabase.auth.signOut();
    setProfile(null);
  }, []);

  const resetPassword = useCallback(async (email: string) => {
    const { error: e } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${window.location.origin}/auth/reset`,
    });
    if (e) { setError(e.message); return e.message; }
    return null;
  }, []);

  return (
    <AuthContext.Provider value={{
      session, user, profile, loading, error, accessToken,
      signInWithEmail, signInWithGoogle, signUp, signOut, resetPassword,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  return useContext(AuthContext);
}
