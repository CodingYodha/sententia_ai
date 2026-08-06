/**
 * Sententia.ai — Supabase browser client singleton.
 *
 * Import this everywhere in the frontend — never call createClient() directly.
 * Uses the public anon key (safe for browser). Service-role key stays server-side.
 */

import { createClient, SupabaseClient } from "@supabase/supabase-js";

const supabaseUrl  = process.env.NEXT_PUBLIC_SUPABASE_URL  ?? "";
const supabaseAnon = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

// ── Dev guard ──────────────────────────────────────────────────────────────────
const _isDev = typeof window !== "undefined" && !supabaseUrl;
if (_isDev) {
  console.warn(
    "[Sententia] NEXT_PUBLIC_SUPABASE_URL not set — " +
    "auth features will run in mock mode. Add it to .env.local."
  );
}

export const supabase: SupabaseClient = supabaseUrl
  ? createClient(supabaseUrl, supabaseAnon, {
      auth: {
        persistSession:       true,
        autoRefreshToken:     true,
        detectSessionInUrl:   true,
        storageKey:           "sententia_auth",
      },
    })
  : // Mock client for dev without Supabase — auth calls are no-ops
    ({
      auth: {
        getSession: async () => ({ data: { session: null }, error: null }),
        onAuthStateChange: () => ({ data: { subscription: { unsubscribe: () => {} } } }),
        signInWithPassword: async () => ({ data: {}, error: { message: "Supabase not configured" } }),
        signInWithOAuth: async () => ({ data: {}, error: { message: "Supabase not configured" } }),
        signUp: async () => ({ data: {}, error: { message: "Supabase not configured" } }),
        signOut: async () => ({ error: null }),
        resetPasswordForEmail: async () => ({ data: {}, error: null }),
      },
      table: () => ({ select: () => ({ eq: () => ({ single: () => ({ execute: async () => ({ data: null }) }) }) }) }),
    } as unknown as SupabaseClient);

export type { Session, User } from "@supabase/supabase-js";
