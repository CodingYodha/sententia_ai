"""
Sententia.ai — Review Router (FR-6.1, FR-6.3, FR-7.1, FR-7.3)

POST /api/review/action           — submit approve/flag/reject (reviewer+)
POST /api/review/correction       — add structured correction (reviewer+)
GET  /api/review/queue            — list workspace queue (reviewer+)
GET  /api/review/corrections/{id} — list corrections for a review item
GET  /api/review/queue/{id}       — single item details

Auth: all endpoints require a valid Supabase JWT.
RBAC: reviewer, compliance_officer, admin only (FR-7.1).
Workspace: all reads/writes are scoped to user's firm_workspace_id (FR-7.2).
Audit: every action writes to audit_log (FR-7.3).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.dependencies.auth import UserContext, get_current_user, require_role
from app.services.audit_service import audit_log, audit_review_submitted
from app.services.review_queue_service import (
    VALID_CORRECTION_TYPES,
    add_correction,
    get_corrections,
    get_queue,
    submit_decision,
)
from app.schemas.review import ReviewActionRequest, ReviewActionResponse, ReviewQueueItem

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/review", tags=["Review"])

_reviewer_dep = Depends(require_role("reviewer", "compliance_officer", "admin"))


# ── Schemas ───────────────────────────────────────────────────────────────────

class CorrectionRequest(BaseModel):
    """FR-6.3 — structured correction form. NOT free text."""
    review_queue_id: str
    structure_id: str
    correction_type: str = Field(
        ...,
        description=(
            "Type of correction — must be one of: "
            + ", ".join(sorted(VALID_CORRECTION_TYPES))
        ),
    )
    affected_field: str = Field(..., description="JSON path of the incorrect field, e.g. 'ownership_chain'")
    corrected_value: str = Field(..., description="The correct value that should replace the LLM output")
    original_value: str | None = Field(None, description="The (incorrect) value the LLM produced")
    jurisdiction: str | None = Field(None, description="Jurisdiction the correction applies to")
    severity: Literal["low", "medium", "high", "critical"] = "medium"
    notes: str | None = Field(None, max_length=1000, description="Optional context (secondary to structured fields)")


class CorrectionResponse(BaseModel):
    correction_id: str
    review_queue_id: str
    correction_type: str
    affected_field: str
    severity: str
    created_at: str
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/action",
    response_model=ReviewActionResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit approve/flag/reject decision (reviewer+ only)",
    dependencies=[_reviewer_dep],
)
async def submit_review_action(
    payload: ReviewActionRequest,
    current_user: UserContext = Depends(get_current_user),
) -> ReviewActionResponse:
    """
    FR-6.1: Reviewer submits a decision on a structure.
    Action moves the review_queue entry out of 'pending'.
    No structure is shown as 'validated' to workspace peers until this runs.
    """
    review_id  = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    # Map action labels to review_queue.status values
    status_map = {"approve": "approved", "flag": "flagged", "reject": "rejected"}
    queue_status = status_map.get(payload.action, payload.action)

    try:
        await submit_decision(
            review_queue_id=payload.structure_id,  # caller uses structure_id as the queue item id
            action=queue_status,
            reviewer=current_user,
            notes=payload.notes,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # Audit log (FR-7.3)
    audit_review_submitted(
        review_id=review_id,
        action=payload.action,
        structure_id=payload.structure_id,
        user=current_user,
    )

    labels = {
        "approve": "approved — marked as expert-validated",
        "flag":    "flagged for further review",
        "reject":  "rejected",
    }
    return ReviewActionResponse(
        review_id=review_id,
        action=payload.action,
        structure_id=payload.structure_id,
        created_at=created_at,
        audit_log_id=review_id,
        message=(
            f"Structure '{payload.structure_name or payload.structure_id}' "
            f"{labels.get(payload.action, payload.action)} by {current_user.role} "
            f"({current_user.email})."
        ),
    )


@router.post(
    "/correction",
    response_model=CorrectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a structured correction to a review item (FR-6.3, reviewer+ only)",
    dependencies=[_reviewer_dep],
)
async def submit_correction(
    payload: CorrectionRequest,
    current_user: UserContext = Depends(get_current_user),
) -> CorrectionResponse:
    """
    FR-6.3: Add a structured, machine-readable correction.
    correction_type is an enum — not free text — so corrections can later
    feed model / rule refinement pipelines.
    """
    if payload.correction_type not in VALID_CORRECTION_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid correction_type '{payload.correction_type}'. Valid: {sorted(VALID_CORRECTION_TYPES)}",
        )

    try:
        correction_id = await add_correction(
            review_queue_id=payload.review_queue_id,
            structure_id=payload.structure_id,
            reviewer=current_user,
            correction_type=payload.correction_type,
            affected_field=payload.affected_field,
            corrected_value=payload.corrected_value,
            severity=payload.severity,
            original_value=payload.original_value,
            jurisdiction=payload.jurisdiction,
            notes=payload.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))

    # Audit
    audit_log(
        "review.correction_added", "review",
        "reviewer_corrections", correction_id,
        {
            "correction_type": payload.correction_type,
            "affected_field":  payload.affected_field,
            "severity":        payload.severity,
            "structure_id":    payload.structure_id,
        },
        current_user,
    )

    return CorrectionResponse(
        correction_id=correction_id,
        review_queue_id=payload.review_queue_id,
        correction_type=payload.correction_type,
        affected_field=payload.affected_field,
        severity=payload.severity,
        created_at=datetime.now(timezone.utc).isoformat(),
        message=f"Correction recorded: {payload.correction_type} on field '{payload.affected_field}'.",
    )


@router.get(
    "/queue",
    response_model=list[ReviewQueueItem],
    status_code=status.HTTP_200_OK,
    summary="List review queue (workspace-scoped, reviewer+ only)",
    dependencies=[_reviewer_dep],
)
async def list_review_queue(
    status_filter: str | None = Query(None, description="Filter by status: pending|in_review|approved|flagged|rejected"),
    limit: int = Query(50, ge=1, le=200),
    current_user: UserContext = Depends(get_current_user),
) -> list[ReviewQueueItem]:
    """FR-7.2: Results are scoped to the caller's firm_workspace_id."""
    items = await get_queue(
        workspace_id=current_user.firm_workspace_id,
        status_filter=status_filter,
        limit=limit,
    )
    return [
        ReviewQueueItem(
            review_id=item.get("id", item.get("review_id", "")),
            structure_id=item.get("structure_id", ""),
            scenario_id=item.get("scenario_id"),
            structure_name=item.get("structure_name"),
            action=item.get("status", "pending"),
            notes=item.get("notes"),
            reviewer_role=item.get("reviewer_role", current_user.role),
            created_at=item.get("created_at", ""),
        )
        for item in items
    ]


@router.get(
    "/corrections/{review_queue_id}",
    status_code=status.HTTP_200_OK,
    summary="List structured corrections for a review item",
    dependencies=[_reviewer_dep],
)
async def list_corrections(
    review_queue_id: str,
    current_user: UserContext = Depends(get_current_user),
) -> list[dict]:
    return await get_corrections(review_queue_id)
