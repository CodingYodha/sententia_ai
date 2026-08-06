"""
Sententia.ai — Audit Service (FR-7.3)

Provides a single function: audit_log() that writes an immutable row to
the audit_log Supabase table. Every generate, view, edit, export, and
compliance-check action must call this.

Design:
  - Fire-and-forget via asyncio.create_task — never blocks the request path.
  - Falls back to structured logging if Supabase is unavailable.
  - Accepts an optional UserContext; if None, the event is anonymous.
  - action_category enum matches the CHECK constraint in the DB migration.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

logger = logging.getLogger(__name__)

ActionCategory = Literal[
    "auth", "scenario", "structure", "compliance", "diagram", "review", "export", "admin"
]


# ── Core write ────────────────────────────────────────────────────────────────

async def _write_audit_row(
    action: str,
    action_category: ActionCategory,
    actor_id: str | None,
    actor_email: str | None,
    firm_workspace_id: str | None,
    entity_type: str | None,
    entity_id: str | None,
    metadata: dict[str, Any],
) -> None:
    """Write one audit_log row. Called from asyncio.create_task — never awaited by callers."""
    row_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc).isoformat()

    try:
        from app.db.supabase_client import get_supabase_client
        sb = get_supabase_client()
        sb.table("audit_log").insert({
            "id":                 row_id,
            "actor_id":           actor_id,
            "actor_email":        actor_email,
            "action":             action,
            "action_category":    action_category,
            "entity_type":        entity_type,
            "entity_id":          entity_id,
            "firm_workspace_id":  firm_workspace_id,
            "metadata":           metadata,
            "created_at":         created_at,
        }).execute()
        logger.debug(f"[audit] {action} actor={actor_email or actor_id} entity={entity_type}/{entity_id}")
    except Exception as e:
        # Never let audit failure affect the request — log and continue
        logger.warning(
            f"[audit] WRITE FAILED (non-fatal) action={action} error={type(e).__name__}: {str(e)[:200]}"
        )
        # Structured fallback log so the event is at least captured
        logger.info(
            f"[audit:fallback] id={row_id} action={action} category={action_category} "
            f"actor={actor_id} workspace={firm_workspace_id} entity={entity_type}/{entity_id}"
        )


# ── Public API ────────────────────────────────────────────────────────────────

def audit_log(
    action: str,
    category: ActionCategory,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    user: "Any | None" = None,   # UserContext — avoid circular import with string annotation
) -> None:
    """
    Schedule a non-blocking audit log write.

    Call this from any route handler:

        from app.services.audit_service import audit_log
        audit_log(
            action="structure.generated",
            category="structure",
            entity_type="structure",
            entity_id=scenario_id,
            metadata={"provider": provider_used, "alternatives": 3},
            user=current_user,       # optional UserContext
        )

    The write is fire-and-forget — it never blocks the HTTP response.

    FR-7.3 required actions:
        scenario.created   | scenario.viewed
        structure.generated | structure.viewed | structure.edited
        compliance.checked
        diagram.exported
        review.submitted   | review.correction_added
        user.login         | user.logout
    """
    actor_id          = getattr(user, "user_id", None) if user else None
    actor_email       = getattr(user, "email",   None) if user else None
    firm_workspace_id = getattr(user, "firm_workspace_id", None) if user else None

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(
                _write_audit_row(
                    action=action,
                    action_category=category,
                    actor_id=actor_id,
                    actor_email=actor_email,
                    firm_workspace_id=firm_workspace_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    metadata=metadata or {},
                )
            )
        else:
            # Sync fallback (test / script context)
            try:
                loop.run_until_complete(
                    _write_audit_row(
                        action=action, action_category=category,
                        actor_id=actor_id, actor_email=actor_email,
                        firm_workspace_id=firm_workspace_id,
                        entity_type=entity_type, entity_id=entity_id,
                        metadata=metadata or {},
                    )
                )
            except Exception as e:
                logger.warning(f"[audit] sync fallback failed (non-fatal): {e}")
    except RuntimeError:
        # No event loop — just log
        logger.info(
            f"[audit:no-loop] action={action} category={category} "
            f"actor={actor_id} entity={entity_type}/{entity_id}"
        )


# ── Convenience wrappers ──────────────────────────────────────────────────────

def audit_structure_generated(scenario_id: str, num_alternatives: int, provider: str, user: "Any | None" = None) -> None:
    audit_log("structure.generated", "structure", "scenario", scenario_id,
              {"num_alternatives": num_alternatives, "provider": provider}, user)

def audit_compliance_checked(scenario_id: str, corridor: str, is_rule_validated: bool, user: "Any | None" = None) -> None:
    audit_log("compliance.checked", "compliance", "scenario", scenario_id,
              {"corridor": corridor, "is_rule_validated": is_rule_validated}, user)

def audit_diagram_exported(structure_id: str, export_format: str, user: "Any | None" = None) -> None:
    audit_log("diagram.exported", "export", "structure", structure_id,
              {"format": export_format}, user)

def audit_review_submitted(review_id: str, action: str, structure_id: str, user: "Any | None" = None) -> None:
    audit_log("review.submitted", "review", "review_queue", review_id,
              {"action": action, "structure_id": structure_id}, user)

def audit_user_login(user: "Any") -> None:
    audit_log("user.login", "auth", "user", getattr(user, "user_id", None),
              {"email": getattr(user, "email", None)}, user)
