#!/usr/bin/env python3
"""
Sententia.ai — Concurrent Load Test (Prompt 10)
================================================

Simulates 5-10 simultaneous scenario submissions to expose:
  - Free-tier rate-limit issues (Supabase, Qdrant, LLM providers)
  - HF Spaces cold-start latency
  - Qdrant idle-pause behavior
  - LLM 429 cascade under concurrent load

Usage:
    # Against local backend (development):
    conda run -n iitr python scripts/load_test.py --url http://localhost:8000 --concurrency 5

    # Against production HF Space (pre-demo):
    conda run -n iitr python scripts/load_test.py --url https://YOUR-SPACE.hf.space --concurrency 10

    # Compliance-only test (faster, no LLM needed):
    conda run -n iitr python scripts/load_test.py --url http://localhost:8000 --compliance-only

Output: load_test_report.json in the current directory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess, sys
    subprocess.run([sys.executable, "-m", "pip", "install", "httpx"], check=True)
    import httpx


# ── Test payloads ─────────────────────────────────────────────────────────────

GENERATE_SCENARIOS = [
    {
        "scenario": {
            "capital_origin": "China",
            "target_jurisdiction": "India",
            "sector": "Technology",
            "investment_amount_usd": 10_000_000,
            "investment_structure_type": "spv_layered",
            "spv_jurisdiction": "Singapore",
            "equity_pct": 49.0,
        }
    },
    {
        "scenario": {
            "capital_origin": "United States",
            "target_jurisdiction": "India",
            "sector": "FinTech",
            "investment_amount_usd": 25_000_000,
            "investment_structure_type": "spv_layered",
            "spv_jurisdiction": "Cayman Islands",
            "equity_pct": 30.0,
        }
    },
    {
        "scenario": {
            "capital_origin": "Saudi Arabia",
            "target_jurisdiction": "France",
            "sector": "Infrastructure",
            "investment_amount_usd": 500_000_000,
            "investment_structure_type": "spv_layered",
            "spv_jurisdiction": "Luxembourg",
            "equity_pct": 40.0,
        }
    },
    {
        "scenario": {
            "capital_origin": "Japan",
            "target_jurisdiction": "Vietnam",
            "sector": "Manufacturing",
            "investment_amount_usd": 50_000_000,
            "investment_structure_type": "joint_venture",
            "equity_pct": 51.0,
        }
    },
    {
        "scenario": {
            "capital_origin": "Germany",
            "target_jurisdiction": "Brazil",
            "sector": "Automotive",
            "investment_amount_usd": 75_000_000,
            "investment_structure_type": "direct_fdi",
            "equity_pct": 100.0,
        }
    },
]

COMPLIANCE_SCENARIOS = [
    {
        "compliance_input": {
            "origin_jurisdiction": "CHINA",
            "spv_jurisdiction": "SINGAPORE",
            "target_jurisdiction": "INDIA",
            "sector": "Technology",
            "investment_amount_usd": 10_000_000,
            "equity_pct": 49.0,
        }
    },
    {
        "compliance_input": {
            "origin_jurisdiction": "UNITED_STATES",
            "spv_jurisdiction": "CAYMAN_ISLANDS",
            "target_jurisdiction": "INDIA",
            "sector": "FinTech",
            "investment_amount_usd": 25_000_000,
            "equity_pct": 30.0,
        }
    },
    {
        "compliance_input": {
            "origin_jurisdiction": "UAE",
            "spv_jurisdiction": "LUXEMBOURG",
            "target_jurisdiction": "FRANCE",
            "sector": "Infrastructure",
            "investment_amount_usd": 500_000_000,
            "equity_pct": 40.0,
        }
    },
    {
        "compliance_input": {
            "origin_jurisdiction": "JAPAN",
            "target_jurisdiction": "VIETNAM",
            "sector": "Manufacturing",
            "investment_amount_usd": 50_000_000,
            "equity_pct": 51.0,
        }
    },
    {
        "compliance_input": {
            "origin_jurisdiction": "GERMANY",
            "target_jurisdiction": "BRAZIL",
            "sector": "Automotive",
            "investment_amount_usd": 75_000_000,
            "equity_pct": 100.0,
        }
    },
]


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class RequestResult:
    request_id: int
    endpoint: str
    payload_label: str
    status_code: int | None
    latency_ms: float
    success: bool
    error: str | None = None
    response_summary: dict = field(default_factory=dict)


@dataclass
class LoadTestReport:
    run_at: str
    base_url: str
    concurrency: int
    total_requests: int
    success_count: int
    failure_count: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    max_latency_ms: float
    cold_start_detected: bool
    rate_limit_detected: bool
    results: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


# ── Core load test ─────────────────────────────────────────────────────────────

async def _single_request(
    client: httpx.AsyncClient,
    request_id: int,
    method: str,
    url: str,
    payload: dict,
    label: str,
    timeout: float = 120.0,
) -> RequestResult:
    t0 = time.perf_counter()
    try:
        resp = await client.request(
            method, url, json=payload, timeout=timeout
        )
        ms = (time.perf_counter() - t0) * 1000
        ok = resp.status_code in (200, 201)
        summary = {}
        try:
            body = resp.json()
            if "corridor_matched" in body:
                summary = {
                    "matched": body.get("corridor_matched"),
                    "validated": body.get("result", {}).get("is_rule_validated"),
                }
            elif "alternatives" in body:
                summary = {
                    "alternatives": len(body.get("alternatives", [])),
                    "provider": body.get("llm_provider_used"),
                }
            elif "detail" in body:
                summary = {"detail": str(body["detail"])[:100]}
        except Exception:
            pass
        return RequestResult(
            request_id=request_id,
            endpoint=url.split("/api/")[-1],
            payload_label=label,
            status_code=resp.status_code,
            latency_ms=ms,
            success=ok,
            response_summary=summary,
        )
    except httpx.TimeoutException as e:
        ms = (time.perf_counter() - t0) * 1000
        return RequestResult(
            request_id=request_id, endpoint=url.split("/api/")[-1],
            payload_label=label, status_code=None, latency_ms=ms,
            success=False, error=f"TIMEOUT after {ms:.0f}ms",
        )
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000
        return RequestResult(
            request_id=request_id, endpoint=url.split("/api/")[-1],
            payload_label=label, status_code=None, latency_ms=ms,
            success=False, error=f"{type(e).__name__}: {str(e)[:200]}",
        )


async def run_load_test(
    base_url: str,
    concurrency: int = 5,
    compliance_only: bool = False,
    timeout: float = 120.0,
) -> LoadTestReport:
    """Run concurrent requests and collect results."""

    base_url = base_url.rstrip("/")
    tasks = []

    # Build task list
    if compliance_only:
        scenarios = (COMPLIANCE_SCENARIOS * ((concurrency // len(COMPLIANCE_SCENARIOS)) + 1))[:concurrency]
        endpoints = [(f"{base_url}/api/compliance/evaluate", s, "compliance") for s in scenarios]
    else:
        gen_count = concurrency // 2
        cmp_count = concurrency - gen_count
        gen_scenarios = (GENERATE_SCENARIOS * ((gen_count // len(GENERATE_SCENARIOS)) + 1))[:gen_count]
        cmp_scenarios = (COMPLIANCE_SCENARIOS * ((cmp_count // len(COMPLIANCE_SCENARIOS)) + 1))[:cmp_count]
        endpoints = (
            [(f"{base_url}/api/structures/generate", s, f"generate-{i}") for i, s in enumerate(gen_scenarios)] +
            [(f"{base_url}/api/compliance/evaluate", s, f"compliance-{i}") for i, s in enumerate(cmp_scenarios)]
        )

    print(f"\n{'='*60}")
    print(f"  Sententia.ai Load Test")
    print(f"  URL:         {base_url}")
    print(f"  Concurrency: {concurrency}")
    print(f"  Requests:    {len(endpoints)}")
    print(f"  Timeout:     {timeout}s per request")
    print(f"{'='*60}\n")

    # First: hit /health to measure cold-start
    async with httpx.AsyncClient() as ping_client:
        t_cold = time.perf_counter()
        try:
            health_resp = await ping_client.get(f"{base_url}/health", timeout=30)
            cold_ms = (time.perf_counter() - t_cold) * 1000
            cold_start = cold_ms > 5000  # >5s → likely cold start
            print(f"  /health: {health_resp.status_code} in {cold_ms:.0f}ms"
                  + (" ← COLD START DETECTED" if cold_start else " ✓"))
        except Exception as e:
            cold_ms = (time.perf_counter() - t_cold) * 1000
            cold_start = True
            print(f"  /health: FAILED after {cold_ms:.0f}ms — {e}")

    print(f"\n  Firing {len(endpoints)} concurrent requests...\n")
    t_start = time.perf_counter()

    async with httpx.AsyncClient() as async_client:
        coros = [
            _single_request(
                async_client, i, "POST", url, payload, label, timeout
            )
            for i, (url, payload, label) in enumerate(endpoints)
        ]
        results: list[RequestResult] = await asyncio.gather(*coros)

    total_ms = (time.perf_counter() - t_start) * 1000

    # Compute statistics
    latencies = [r.latency_ms for r in results]
    latencies_sorted = sorted(latencies)
    n = len(latencies_sorted)
    success_count = sum(1 for r in results if r.success)
    failure_count = len(results) - success_count
    rate_limit = any(r.status_code == 429 for r in results)

    p50 = latencies_sorted[int(n * 0.50)] if n else 0
    p95 = latencies_sorted[int(n * 0.95)] if n else 0

    # Print per-request results
    for r in results:
        icon = "✓" if r.success else "✗"
        print(f"  [{icon}] #{r.request_id:02d} {r.endpoint:<35} "
              f"{r.status_code or 'TIMEOUT':<6} {r.latency_ms:>7.0f}ms  "
              f"{r.payload_label}")
        if r.error:
            print(f"       ⚠  {r.error}")
        if r.response_summary:
            print(f"       →  {r.response_summary}")

    notes = []
    if cold_start:
        notes.append(f"Cold start detected: /health took {cold_ms:.0f}ms. Add pre-warm step before demo.")
    if rate_limit:
        notes.append("HTTP 429 received from backend — LLM provider rate limit hit under concurrent load.")
    if failure_count > 0:
        notes.append(f"{failure_count}/{len(results)} requests failed. "
                     "Check Supabase idle-pause and Qdrant connectivity.")
    if all(r.success for r in results):
        notes.append("All requests succeeded under concurrent load.")

    report = LoadTestReport(
        run_at=datetime.now(timezone.utc).isoformat(),
        base_url=base_url,
        concurrency=concurrency,
        total_requests=len(results),
        success_count=success_count,
        failure_count=failure_count,
        avg_latency_ms=sum(latencies) / n if n else 0,
        p50_latency_ms=p50,
        p95_latency_ms=p95,
        max_latency_ms=max(latencies) if latencies else 0,
        cold_start_detected=cold_start,
        rate_limit_detected=rate_limit,
        results=[asdict(r) for r in results],
        notes=notes,
    )

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"  Success:     {success_count}/{len(results)}")
    print(f"  Avg latency: {report.avg_latency_ms:.0f}ms")
    print(f"  P50 latency: {p50:.0f}ms")
    print(f"  P95 latency: {p95:.0f}ms")
    print(f"  Max latency: {report.max_latency_ms:.0f}ms")
    print(f"  Total wall:  {total_ms:.0f}ms")
    print(f"  Cold start:  {'YES ⚠' if cold_start else 'No ✓'}")
    print(f"  Rate limit:  {'YES ⚠' if rate_limit else 'No ✓'}")
    for n in notes:
        print(f"\n  ⚠ {n}")
    print(f"{'='*60}\n")

    return report


def main():
    parser = argparse.ArgumentParser(description="Sententia.ai Load Test")
    parser.add_argument("--url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--concurrency", type=int, default=5, help="Number of concurrent requests (5-10)")
    parser.add_argument("--compliance-only", action="store_true", help="Only test compliance endpoint (faster, no LLM)")
    parser.add_argument("--timeout", type=float, default=120.0, help="Per-request timeout in seconds")
    parser.add_argument("--output", default="load_test_report.json", help="Output JSON report file")
    args = parser.parse_args()

    report = asyncio.run(run_load_test(
        base_url=args.url,
        concurrency=args.concurrency,
        compliance_only=args.compliance_only,
        timeout=args.timeout,
    ))

    with open(args.output, "w") as f:
        json.dump(asdict(report), f, indent=2)
    print(f"Report written to: {args.output}")


if __name__ == "__main__":
    main()
