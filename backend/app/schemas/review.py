"""
Sententia.ai — Review Queue Schemas (FR-6.2)

ReviewActionRequest:  Payload for POST /api/review/action
ReviewActionResponse: Confirmation returned to client
ReviewQueueItem:      A single item in the review queue list
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewActionRequest(BaseModel):
    """POST /api/review/action — reviewer submits a decision on one structure."""
    structure_id: str = Field(
        ...,
        description="Unique ID of the structure being reviewed (scenario_id + rank)",
    )
    scenario_id: str | None = Field(None, description="Parent scenario ID")
    alternative_rank: int | None = Field(None, ge=1, le=4)
    structure_name: str | None = None
    action: Literal["approve", "flag", "reject"] = Field(
        ...,
        description="approve = expert-validated | flag = needs attention | reject = do not use",
    )
    notes: str | None = Field(None, max_length=2000)
    reviewer_role: str = Field("reviewer", description="Role of the reviewer submitting the action")


class ReviewActionResponse(BaseModel):
    """Confirmation from POST /api/review/action."""
    review_id: str
    action: str
    structure_id: str
    created_at: str
    audit_log_id: str | None = None
    message: str


class ReviewQueueItem(BaseModel):
    """A single item returned by GET /api/review/queue."""
    review_id: str
    structure_id: str
    scenario_id: str | None
    structure_name: str | None
    action: str
    notes: str | None
    reviewer_role: str
    created_at: str
