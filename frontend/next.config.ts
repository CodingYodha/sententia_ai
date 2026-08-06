import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // ── Static export for Cloudflare Pages ────────────────────────────────────
  // All pages are pre-rendered (○ static) — no server runtime needed.
  // Cloudflare Pages serves the `out/` directory directly via its CDN.
  output: "export",

  // ── Images: no Next.js image optimizer in static export ───────────────────
  images: {
    unoptimized: true,
  },

  // ── Environment variables inlined at build time ───────────────────────────
  env: {
    NEXT_PUBLIC_API_URL:           process.env.NEXT_PUBLIC_API_URL           ?? "http://localhost:8000",
    NEXT_PUBLIC_SUPABASE_URL:      process.env.NEXT_PUBLIC_SUPABASE_URL      ?? "",
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  },
};

export default nextConfig;
