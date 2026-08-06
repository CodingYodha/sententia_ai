#!/usr/bin/env python3
"""
Sententia.ai — Pre-Demo Pre-Warm Script (Prompt 10)
=====================================================

Runs 60-90 seconds before the demo to:
  1. Wake HF Spaces from cold start (can take 30-60s on free tier)
  2. Trigger Supabase connection pool (prevents idle-pause first-query lag)
  3. Trigger Qdrant client warm-up (index load into memory)
  4. Run one lightweight compliance check to confirm full pipeline
  5. Print a GO / NO-GO status for the demo

Usage:
    # Default (production HF Space):
    conda run -n iitr python scripts/prewarm.py --url https://YOUR-SPACE.hf.space

    # Local dev:
    conda run -n iitr python scripts/prewarm.py --url http://localhost:8000

Schedule for auto-warm before demos:
    # Linux/Mac cron (7 minutes before the hour):
    53 * * * * cd /path/to/sententia && conda run -n iitr python backend/scripts/prewarm.py --url https://YOUR-SPACE.hf.space

    # Windows Task Scheduler: run this script at a fixed time
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from datetime import datetime, timezone

try:
    import httpx
except ImportError:
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], check=True)
    import httpx

# ANSI colors
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

OK   = f"{GREEN}✓{RESET}"
WARN = f"{YELLOW}⚠{RESET}"
FAIL = f"{RED}✗{RESET}"


async def prewarm(base_url: str, max_wait_s: float = 90.0) -> bool:
    base_url = base_url.rstrip("/")
    all_ok = True

    print(f"\n{BOLD}{'='*55}")
    print(f"  Sententia.ai Pre-Demo Pre-Warm")
    print(f"  Target: {base_url}")
    print(f"  Time:   {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*55}{RESET}\n")

    async with httpx.AsyncClient() as client:

        # ── Step 1: HF Spaces wake-up (poll /health until 200) ───────────────
        print(f"  [1/5] Waking HF Space (cold start up to {max_wait_s:.0f}s)...")
        t0 = time.perf_counter()
        health_ok = False
        cold_ms = 0.0
        while (time.perf_counter() - t0) < max_wait_s:
            try:
                r = await client.get(f"{base_url}/health", timeout=10)
                cold_ms = (time.perf_counter() - t0) * 1000
                if r.status_code == 200:
                    health_ok = True
                    break
            except Exception:
                pass
            await asyncio.sleep(3)

        if health_ok:
            print(f"  {OK}  /health → 200 in {cold_ms:.0f}ms"
                  + (f" {YELLOW}(cold start){RESET}" if cold_ms > 5000 else ""))
        else:
            print(f"  {FAIL}  /health never returned 200 in {max_wait_s:.0f}s — backend may be down")
            all_ok = False
            return all_ok

        # ── Step 2: Corridor registry (YAML, confirms app is fully loaded) ───
        print(f"  [2/5] Loading corridor registry...")
        try:
            r = await client.get(f"{base_url}/api/compliance/corridors", timeout=15)
            body = r.json()
            count = body.get("count", len(body.get("corridors", [])))
            print(f"  {OK}  {count} pre-validated corridors loaded")
        except Exception as e:
            print(f"  {FAIL}  Corridor registry failed: {e}")
            all_ok = False

        # ── Step 3: Compliance warm-up (triggers Supabase + OPA) ─────────────
        print(f"  [3/5] Running compliance warm-up (Supabase + policy engine)...")
        t_c = time.perf_counter()
        try:
            r = await client.post(
                f"{base_url}/api/compliance/evaluate",
                json={
                    "compliance_input": {
                        "origin_jurisdiction":   "CHINA",
                        "spv_jurisdiction":      "SINGAPORE",
                        "target_jurisdiction":   "INDIA",
                        "sector":                "Technology",
                        "investment_amount_usd": 5_000_000,
                        "equity_pct":            49.0,
                    }
                },
                timeout=30,
            )
            cmp_ms = (time.perf_counter() - t_c) * 1000
            if r.status_code == 200:
                body = r.json()
                matched = body.get("corridor_matched", False)
                print(f"  {OK}  compliance/evaluate → 200 in {cmp_ms:.0f}ms "
                      f"(matched={matched})")
            else:
                print(f"  {WARN}  compliance/evaluate → {r.status_code} ({cmp_ms:.0f}ms)")
        except Exception as e:
            print(f"  {FAIL}  compliance warm-up failed: {e}")
            all_ok = False

        # ── Step 4: RAG warm-up (triggers Qdrant connection + index load) ────
        print(f"  [4/5] Warming Qdrant via RAG query...")
        t_r = time.perf_counter()
        try:
            r = await client.post(
                f"{base_url}/api/rag/query",
                json={"query": "cross-border investment regulatory approval", "top_k": 3},
                timeout=30,
            )
            rag_ms = (time.perf_counter() - t_r) * 1000
            if r.status_code == 200:
                body = r.json()
                hits = len(body.get("results", []))
                print(f"  {OK}  rag/query → 200 in {rag_ms:.0f}ms ({hits} results)")
            else:
                # RAG may fail if Qdrant not configured — non-fatal for prewarm
                print(f"  {WARN}  rag/query → {r.status_code} ({rag_ms:.0f}ms) "
                      f"(Qdrant may not be configured — non-fatal)")
        except Exception as e:
            rag_ms = (time.perf_counter() - t_r) * 1000
            print(f"  {WARN}  rag/query failed ({rag_ms:.0f}ms): {e} (non-fatal)")

        # ── Step 5: Full pipeline smoke test (structure generation stub) ─────
        print(f"  [5/5] Structure generation ping (triggers LLM router)...")
        t_s = time.perf_counter()
        try:
            r = await client.post(
                f"{base_url}/api/structures/generate",
                json={
                    "scenario": {
                        "capital_origin":            "China",
                        "target_jurisdiction":       "India",
                        "sector":                    "Technology",
                        "investment_amount_usd":     10_000_000,
                        "investment_structure_type": "spv_layered",
                    },
                    "max_alternatives": 2,
                },
                timeout=60,
            )
            gen_ms = (time.perf_counter() - t_s) * 1000
            if r.status_code == 200:
                body = r.json()
                alts = len(body.get("alternatives", []))
                provider = body.get("llm_provider_used", "unknown")
                print(f"  {OK}  structures/generate → 200 in {gen_ms:.0f}ms "
                      f"({alts} alternatives, provider={provider})")
            else:
                print(f"  {WARN}  structures/generate → {r.status_code} ({gen_ms:.0f}ms) "
                      f"(LLM keys may not be set — check .env in HF Space)")
                if r.status_code == 500:
                    all_ok = False
        except Exception as e:
            gen_ms = (time.perf_counter() - t_s) * 1000
            print(f"  {WARN}  structures/generate failed ({gen_ms:.0f}ms): {e}")

    # ── Summary ───────────────────────────────────────────────────────────────
    total_ms = cold_ms + (time.perf_counter() - t0 - cold_ms / 1000) * 1000
    print(f"\n  {'─'*50}")
    if all_ok:
        print(f"  {GREEN}{BOLD}GO — All systems nominal. Demo is ready.{RESET}")
    else:
        print(f"  {RED}{BOLD}NO-GO — Issues detected. See warnings above.{RESET}")
    print(f"  Total pre-warm time: {(time.perf_counter() - t0) * 1000:.0f}ms")
    print(f"  {'─'*50}\n")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Sententia.ai Pre-Demo Pre-Warm")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--max-wait", type=float, default=90.0,
                        help="Max seconds to wait for cold start (default: 90)")
    args = parser.parse_args()

    ok = asyncio.run(prewarm(args.url, args.max_wait))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
