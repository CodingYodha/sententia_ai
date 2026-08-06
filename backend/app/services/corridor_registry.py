"""
Sententia.ai — Corridor Registry

Loads corridors.yaml and provides corridor matching logic.
This is the single source of truth for which corridors are pre-validated
and which Rego/Python policy to invoke.

Matching algorithm:
  1. Normalize input jurisdictions to UPPER_SNAKE_CASE
  2. For each corridor in registry (ordered):
       a. Check origin_jurisdictions contains input.origin
       b. Check target_jurisdictions contains input.target
       c. If corridor has spv_jurisdictions: check spv matches OR input.spv is None
  3. Return first match (corridors.yaml ordering is priority order)
  4. Return None if no match (fallback to LLM-only analysis)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from functools import lru_cache

import yaml

logger = logging.getLogger(__name__)

_CORRIDORS_PATH = Path(__file__).parent.parent.parent / "policies" / "corridors.yaml"


@dataclass
class CorridorConfig:
    """Single corridor configuration entry from corridors.yaml."""

    id: str
    name: str
    origin_jurisdictions: list[str]
    target_jurisdictions: list[str]
    spv_jurisdictions: list[str] | None   # None = matches any or no SPV
    policy_package: str
    rego_file: str
    status: str
    description: str = ""
    references: list[str] = field(default_factory=list)


@lru_cache(maxsize=1)
def load_corridors(corridors_path: str = str(_CORRIDORS_PATH)) -> list[CorridorConfig]:
    """
    Load and parse corridors.yaml.
    Cached after first load — call load_corridors.cache_clear() to reload.
    """
    path = Path(corridors_path)
    if not path.exists():
        logger.error(f"corridors.yaml not found at {path}")
        return []

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    corridors = []
    for entry in data.get("corridors", []):
        if entry.get("status", "active") != "active":
            logger.debug(f"Skipping inactive corridor: {entry.get('id')}")
            continue

        spv_raw = entry.get("spv_jurisdictions")
        corridors.append(CorridorConfig(
            id=entry["id"],
            name=entry["name"],
            origin_jurisdictions=[j.upper() for j in (entry.get("origin_jurisdictions") or [])],
            target_jurisdictions=[j.upper() for j in (entry.get("target_jurisdictions") or [])],
            spv_jurisdictions=(
                [j.upper() for j in spv_raw] if spv_raw else None
            ),
            policy_package=entry["policy_package"],
            rego_file=entry["rego_file"],
            status=entry.get("status", "active"),
            description=entry.get("description", ""),
            references=entry.get("references", []),
        ))

    logger.info(f"Loaded {len(corridors)} active corridors from {path.name}")
    return corridors


def _normalize(s: str | None) -> str | None:
    """Normalize a jurisdiction string to UPPER_SNAKE_CASE."""
    if s is None:
        return None
    return s.upper().replace(" ", "_").replace("-", "_")


def match_corridor(
    origin: str,
    target: str,
    spv: str | None = None,
) -> CorridorConfig | None:
    """
    Find the first corridor in corridors.yaml matching the given jurisdictions.

    Args:
        origin: Origin jurisdiction (any casing — normalized internally)
        target: Target jurisdiction (any casing — normalized internally)
        spv:    SPV jurisdiction or None (optional — any casing)

    Returns:
        CorridorConfig if a match is found, None otherwise.
    """
    origin_n = _normalize(origin)
    target_n = _normalize(target)
    spv_n    = _normalize(spv)

    for corridor in load_corridors():
        # Check origin
        if origin_n not in corridor.origin_jurisdictions:
            continue
        # Check target
        if target_n not in corridor.target_jurisdictions:
            continue
        # Check SPV:
        #   - If corridor has no SPV requirement → matches any input SPV (including None)
        #   - If corridor has SPV requirement → input SPV must be in the list
        #   - If input has no SPV but corridor requires one → no match
        if corridor.spv_jurisdictions is not None:
            if spv_n is None or spv_n not in corridor.spv_jurisdictions:
                continue

        logger.debug(
            f"Corridor matched: {corridor.id} "
            f"({origin_n} → {spv_n or 'direct'} → {target_n})"
        )
        return corridor

    logger.info(
        f"No corridor matched: {origin_n} → {spv_n or 'direct'} → {target_n}"
    )
    return None


def list_all_corridors() -> list[dict]:
    """Return a summary list of all active corridors — used by the corpus health endpoint."""
    return [
        {
            "id": c.id,
            "name": c.name,
            "origin_jurisdictions": c.origin_jurisdictions,
            "target_jurisdictions": c.target_jurisdictions,
            "spv_jurisdictions": c.spv_jurisdictions,
            "policy_package": c.policy_package,
            "rego_file": c.rego_file,
            "status": c.status,
        }
        for c in load_corridors()
    ]
