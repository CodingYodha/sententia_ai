import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ── Cloudflare Pages compatibility ────────────────────────────────────────
  // next-on-pages requires no standalone output — Pages handles serving.
  // Images: use unoptimized for Cloudflare (no Next.js image lambda).
  images: {
    unoptimized: true,
  },

  // ── Environment variables exposed to the browser ──────────────────────────
  // Explicitly list here so they're statically inlined at build time.
  // Values are set in Cloudflare Pages → Settings → Environment Variables.
  env: {
    NEXT_PUBLIC_API_URL:              process.env.NEXT_PUBLIC_API_URL              ?? "http://localhost:8000",
    NEXT_PUBLIC_SUPABASE_URL:         process.env.NEXT_PUBLIC_SUPABASE_URL         ?? "",
    NEXT_PUBLIC_SUPABASE_ANON_KEY:    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY    ?? "",
  },

  // ── Headers — security + CORS ─────────────────────────────────────────────
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options",   value: "nosniff" },
          { key: "X-Frame-Options",           value: "SAMEORIGIN" },
          { key: "Referrer-Policy",           value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy",        value: "camera=(), microphone=(), geolocation=()" },
        ],
      },
    ];
  },
};

export default nextConfig;
