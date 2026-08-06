"""
Sententia.ai — OPA Service

Evaluation strategy (cascade):
  1. OPA REST API   — if OPA_URL env var is set (production/Docker)
  2. opa eval CLI   — if OPA binary is on PATH (dev with OPA installed)
  3. Python-native  — always available fallback (used in tests)

The caller never needs to know which mode was used — the evaluation_mode
field in the result documents this for resilience tracking.

OPA REST API notes:
  - Expects OPA running at OPA_URL (default http://localhost:8181)
  - Policies are pushed at first call (PUT /v1/policies/{id}) and cached
  - Input is posted to POST /v1/data/{package_path}
  - Response is expected at result.violations, result.required_approvals, result.allow
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.schemas.compliance import (
    ComplianceInput,
    ComplianceResult,
    PolicyViolation,
)
from app.services.corridor_registry import CorridorConfig
from app.services.policy_evaluator import get_evaluator

logger = logging.getLogger(__name__)

_REGO_DIR = Path(__file__).parent.parent.parent / "policies" / "rego"

# Track whether OPA policies have been loaded for this process lifetime
_opa_policies_loaded: set[str] = set()


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _build_input_dict(compliance_input: ComplianceInput) -> dict[str, Any]:
    """Convert ComplianceInput → dict for OPA / Python evaluator."""
    return compliance_input.model_dump(exclude_none=False)


def _parse_opa_result(raw: dict) -> tuple[list[dict], list[str], bool]:
    """Parse OPA /v1/data response into (violations, required_approvals, allow)."""
    result = raw.get("result", raw)  # OPA wraps in 'result' key
    violations          = result.get("violations", [])
    required_approvals  = list(result.get("required_approvals", []))
    allow               = result.get("allow", False)
    return violations, required_approvals, allow


def _build_compliance_result(
    corridor: CorridorConfig,
    violations: list[dict],
    required_approvals: list[str],
    allow: bool,
    evaluation_mode: str,
) -> ComplianceResult:
    """Assemble a ComplianceResult from raw policy output."""
    blocking = [PolicyViolation(**v) for v in violations if v.get("severity") == "blocking"]
    warnings  = [PolicyViolation(**v) for v in violations if v.get("severity") == "warning"]

    return ComplianceResult(
        corridor_id=corridor.id,
        corridor_name=corridor.name,
        policy_package=corridor.policy_package,
        is_rule_validated=True,
        is_allowed=allow,
        violations=blocking,
        warnings=warnings,
        required_approvals=required_approvals,
        evaluation_mode=evaluation_mode,
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        blocking_count=len(blocking),
        warning_count=len(warnings),
    )


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 1: OPA REST API
# ══════════════════════════════════════════════════════════════════════════════

async def _load_policy_to_opa(opa_url: str, policy_id: str, rego_text: str) -> None:
    """Push a Rego policy to OPA via the Policy API."""
    import httpx
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.put(
            f"{opa_url}/v1/policies/{policy_id}",
            content=rego_text.encode(),
            headers={"Content-Type": "text/plain"},
        )
        resp.raise_for_status()
    logger.debug(f"Policy '{policy_id}' loaded to OPA at {opa_url}")


async def _ensure_policies_loaded(opa_url: str) -> None:
    """Push all Rego policies to OPA once per process lifetime."""
    if opa_url in _opa_policies_loaded:
        return
    for rego_file in _REGO_DIR.glob("*.rego"):
        policy_id = rego_file.stem
        await _load_policy_to_opa(opa_url, policy_id, rego_file.read_text())
    _opa_policies_loaded.add(opa_url)
    logger.info(f"All Rego policies loaded to OPA at {opa_url}")


async def _evaluate_via_opa_server(
    opa_url: str,
    policy_package: str,
    input_dict: dict,
) -> tuple[list[dict], list[str], bool] | None:
    """
    Try to evaluate policy via OPA REST API.
    Returns None if OPA is unreachable.
    """
    try:
        import httpx
        await _ensure_policies_loaded(opa_url)
        # Convert "sententia.corridors.india" → "sententia/corridors/india"
        path = policy_package.replace(".", "/")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{opa_url}/v1/data/{path}",
                json={"input": input_dict},
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
        raw = resp.json()
        return _parse_opa_result(raw)
    except Exception as e:
        logger.warning(f"OPA server evaluation failed: {type(e).__name__}: {str(e)[:100]}")
        _opa_policies_loaded.discard(opa_url)  # force reload next attempt
        return None


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 2: OPA CLI subprocess
# ══════════════════════════════════════════════════════════════════════════════

def _evaluate_via_opa_subprocess(
    policy_package: str,
    input_dict: dict,
) -> tuple[list[dict], list[str], bool] | None:
    """
    Try to evaluate via `opa eval` subprocess.
    Returns None if OPA binary not found or eval fails.
    """
    opa_bin = shutil.which("opa")
    if not opa_bin:
        return None

    # Find the rego file
    package_last = policy_package.split(".")[-1]
    rego_candidates = list(_REGO_DIR.glob(f"*{package_last}*.rego"))
    if not rego_candidates:
        logger.warning(f"No rego file found for package {policy_package}")
        return None
    rego_file = rego_candidates[0]

    # Build the query — eval all three bindings at once using a wrapper object
    query = textwrap.dedent(f"""
        x := {{
            "violations": data.{policy_package}.violations,
            "required_approvals": data.{policy_package}.required_approvals,
            "allow": data.{policy_package}.allow
        }}
    """).strip()

    try:
        result = subprocess.run(
            [
                opa_bin, "eval",
                "--data", str(rego_file),
                "--input", "/dev/stdin",
                "--format", "json",
                query,
            ],
            input=json.dumps(input_dict).encode(),
            capture_output=True,
            timeout=30,
        )
        if result.returncode != 0:
            logger.warning(f"opa eval failed: {result.stderr.decode()[:200]}")
            return None

        data = json.loads(result.stdout)
        # OPA eval returns: {"result": [{"expressions": [{"value": ...}]}]}
        value = data["result"][0]["expressions"][0]["value"]
        x = value.get("x", {})
        return (
            list(x.get("violations", [])),
            list(x.get("required_approvals", [])),
            x.get("allow", False),
        )
    except Exception as e:
        logger.warning(f"OPA subprocess evaluation failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# STRATEGY 3: Python-native fallback
# ══════════════════════════════════════════════════════════════════════════════

def _evaluate_python_native(
    policy_package: str,
    input_dict: dict,
) -> tuple[list[dict], list[str], bool] | None:
    """Always-available Python-native evaluator."""
    evaluator = get_evaluator(policy_package)
    if evaluator is None:
        return None
    result = evaluator.evaluate(input_dict)
    return result["violations"], result["required_approvals"], result["allow"]


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

async def evaluate_compliance(
    compliance_input: ComplianceInput,
    corridor: CorridorConfig,
) -> ComplianceResult:
    """
    Evaluate compliance for the matched corridor using the best available strategy.

    Cascade:
      OPA REST API → OPA subprocess → Python-native

    Always returns a ComplianceResult — never raises.
    The evaluation_mode field indicates which strategy was used.
    """
    from app.config import get_settings
    settings = get_settings()

    input_dict = _build_input_dict(compliance_input)

    # ── Strategy 1: OPA REST API ──────────────────────────────────────────────
    opa_url = getattr(settings, "opa_url", None)
    if opa_url:
        raw = await _evaluate_via_opa_server(opa_url, corridor.policy_package, input_dict)
        if raw is not None:
            violations, required_approvals, allow = raw
            logger.info(
                f"Compliance evaluated via OPA server: corridor={corridor.id} "
                f"allow={allow} blocking={sum(1 for v in violations if v.get('severity')=='blocking')}"
            )
            return _build_compliance_result(
                corridor, violations, required_approvals, allow, "opa_server"
            )

    # ── Strategy 2: OPA subprocess ────────────────────────────────────────────
    raw = _evaluate_via_opa_subprocess(corridor.policy_package, input_dict)
    if raw is not None:
        violations, required_approvals, allow = raw
        logger.info(
            f"Compliance evaluated via OPA subprocess: corridor={corridor.id} allow={allow}"
        )
        return _build_compliance_result(
            corridor, violations, required_approvals, allow, "opa_subprocess"
        )

    # ── Strategy 3: Python-native ─────────────────────────────────────────────
    raw = _evaluate_python_native(corridor.policy_package, input_dict)
    if raw is not None:
        violations, required_approvals, allow = raw
        logger.info(
            f"Compliance evaluated via Python-native: corridor={corridor.id} allow={allow}"
        )
        return _build_compliance_result(
            corridor, violations, required_approvals, allow, "python_native"
        )

    # ── All strategies failed — this should never happen if Python-native is registered ──
    logger.error(
        f"All evaluation strategies failed for policy_package={corridor.policy_package}. "
        "This is a bug — Python-native evaluator should always be available."
    )
    return ComplianceResult(
        corridor_id=corridor.id,
        corridor_name=corridor.name,
        policy_package=corridor.policy_package,
        is_rule_validated=False,
        is_allowed=False,
        violations=[],
        warnings=[],
        required_approvals=[],
        evaluation_mode="none",
        evaluated_at=datetime.now(timezone.utc).isoformat(),
        blocking_count=0,
        warning_count=0,
    )
