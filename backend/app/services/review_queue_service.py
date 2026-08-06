"""
Sententia.ai — Review Queue Service (FR-6.1, FR-6.3)

Manages the human-in-loop workflow:
  - auto_enqueue(): called by structures router on every generation
  - submit_decision(): reviewer approves/flags/rejects
  - add_correction(): reviewer adds a structured correction (FR-6.3)
  - get_queue(): returns workspace-filtered queue

FR-6.1: Newly generated structures enter review_queue as 'pending' by default.
        No structure reaches 'validated' status without going through review.
FR-6.3: Corrections are structured (typed enum + fields), not free text.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from app.dependencies.auth import UserContext

logger = logging.getLogger(__name__)


# ── In-memory fallback (dev without Supabase) ──────────────────────────────────

_queue_fallback: list[dict] = []
_corrections_fallback: list[dict] = []


# ── Supabase helpers ─────────────────────────────────────────────────────────

def _sb():
    try:
        from app.db.supabase_client import get_supabase_client
        return get_supabase_client()
    except Exception:
        return None


# ── Auto-enqueue ──────────────────────────────────────────────────────────────

async def auto_enqueue(
    structure_id: str,
    scenario_id: str,
    structure_name: str | None,
    structure_rank: int | None,
    structure_json: dict[str, Any],
    compliance_result: dict[str, Any] | None,
    generated_by: UserContext | None,
) -> str:
    """
    FR-6.1: Called immediately after structure generation.
    Inserts a 'pending' row into review_queue. The DB trigger also does this
    for structures persisted to the structures table; this covers in-memory flows.
    Returns the review_queue row id.
    """
    review_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    row = {
        "id": review_id,
        "structure_id": structure_id,
        "scenario_id": scenario_id,
        "structure_name": structure_name,
        "structure_rank": structure_rank,
        "structure_json": structure_json,
        "compliance_result": compliance_result,
        "status": "pending",
        "generated_by": generated_by.user_id if generated_by else None,
        "firm_workspace_id": generated_by.firm_workspace_id if generated_by else None,
        "created_at": created_at,
        "updated_at": created_at,
    }

    sb = _sb()
    if sb:
        try:
            sb.table("review_queue").insert({
                k: v for k, v in row.items()
                if k in {
                    "id", "structure_id", "status", "created_at", "updated_at",
                    # extended columns added by migration 0003
                    "firm_workspace_id", "generated_by",
                }
            }).execute()
            logger.info(f"[review_queue] auto-enqueued: review_id={review_id} structure={structure_id}")
        except Exception as e:
            logger.warning(f"[review_queue] Supabase insert failed (using in-memory): {e}")
            _queue_fallback.append(row)
    else:
        _queue_fallback.append(row)

    return review_id


# ── Reviewer decision ─────────────────────────────────────────────────────────

async def submit_decision(
    review_queue_id: str,
    action: str,          # 'approved' | 'flagged' | 'rejected' | 'in_review'
    reviewer: UserContext,
    notes: str | None,
) -> dict[str, Any]:
    """
    FR-6.1/FR-6.3: Reviewer submits a decision. Updates review_queue.status and
    syncs structures.status via DB trigger. Returns updated row.
    """
    if not reviewer.is_reviewer_or_above():
        raise PermissionError(f"Role '{reviewer.role}' cannot submit review decisions.")

    now = datetime.now(timezone.utc).isoformat()

    update_payload = {
        "status":       action,
        "reviewer_id":  reviewer.user_id,
        "reviewed_at":  now,
        "updated_at":   now,
    }
    if notes:
        update_payload["notes"] = notes

    sb = _sb()
    if sb:
        try:
            sb.table("review_queue").update(update_payload).eq("id", review_queue_id).execute()
        except Exception as e:
            logger.warning(f"[review_queue] Decision write failed: {e}")
    else:
        # Update in-memory fallback
        for item in _queue_fallback:
            if item["id"] == review_queue_id:
                item.update(update_payload)
                break

    return {
        "review_queue_id": review_queue_id,
        "action":          action,
        "reviewed_by":     reviewer.email,
        "reviewed_at":     now,
    }


# ── Structured correction (FR-6.3) ────────────────────────────────────────────

VALID_CORRECTION_TYPES = {
    "jurisdiction_error", "ownership_threshold", "regulatory_gap",
    "tax_issue", "structure_type_wrong", "risk_severity_wrong",
    "missing_touchpoint", "citation_error", "treaty_benefit_wrong",
    "gaar_issue", "other",
}

async def add_correction(
    review_queue_id: str,
    structure_id: str,
    reviewer: UserContext,
    correction_type: str,
    affected_field: str,
    corrected_value: str,
    severity: str = "medium",
    original_value: str | None = None,
    jurisdiction: str | None = None,
    notes: str | None = None,
) -> str:
    """
    FR-6.3: Insert a structured correction row. Returns the correction id.
    correction_type must be one of VALID_CORRECTION_TYPES (enum enforced in DB).
    """
    if correction_type not in VALID_CORRECTION_TYPES:
        raise ValueError(f"Invalid correction_type: {correction_type}. Must be one of {VALID_CORRECTION_TYPES}")

    correction_id = str(uuid.uuid4())
    created_at    = datetime.now(timezone.utc).isoformat()

    row = {
        "id":               correction_id,
        "review_queue_id":  review_queue_id,
        "structure_id":     structure_id,
        "reviewer_id":      reviewer.user_id,
        "firm_workspace_id": reviewer.firm_workspace_id,
        "correction_type":  correction_type,
        "affected_field":   affected_field,
        "original_value":   original_value,
        "corrected_value":  corrected_value,
        "jurisdiction":     jurisdiction,
        "severity":         severity,
        "notes":            notes,
        "created_at":       created_at,
    }

    sb = _sb()
    if sb:
        try:
            sb.table("reviewer_corrections").insert(row).execute()
            logger.info(f"[corrections] Added: id={correction_id} type={correction_type} field={affected_field}")
        except Exception as e:
            logger.warning(f"[corrections] Supabase insert failed: {e}")
            _corrections_fallback.append(row)
    else:
        _corrections_fallback.append(row)

    return correction_id


# ── Queue read ────────────────────────────────────────────────────────────────

async def get_queue(
    workspace_id: str | None,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Return review queue items for the workspace. RLS enforced on Supabase side.
    Falls back to in-memory queue if Supabase unavailable.
    """
    sb = _sb()
    if sb:
        try:
            query = sb.table("review_queue").select("*")
            if workspace_id:
                query = query.eq("firm_workspace_id", workspace_id)
            if status_filter:
                query = query.eq("status", status_filter)
            result = query.order("created_at", desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            logger.warning(f"[review_queue] Supabase read failed: {e}")

    # In-memory fallback
    items = list(reversed(_queue_fallback[-limit:]))
    if status_filter:
        items = [i for i in items if i.get("status") == status_filter]
    return items


async def get_corrections(review_queue_id: str) -> list[dict[str, Any]]:
    """Return all structured corrections for a given review_queue_id."""
    sb = _sb()
    if sb:
        try:
            result = (
                sb.table("reviewer_corrections")
                .select("*")
                .eq("review_queue_id", review_queue_id)
                .order("created_at", desc=True)
                .execute()
            )
            return result.data or []
        except Exception as e:
            logger.warning(f"[corrections] Supabase read failed: {e}")

    return [c for c in _corrections_fallback if c.get("review_queue_id") == review_queue_id]
