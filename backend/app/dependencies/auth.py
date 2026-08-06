"""
Sententia.ai — JWT Authentication Dependency (FR-7.1)

Verifies Supabase-issued access tokens and resolves the calling user's
profile (role + workspace) from the public.users table.

Usage in route handlers:
    @router.post("/...")
    async def my_route(current_user: UserContext = Depends(get_current_user)):
        ...

For routes that work WITHOUT auth (e.g. health, docs):
    Use Depends(get_optional_user) — returns None if no/invalid token.

For role-gated routes, use the helpers:
    require_role("reviewer", "admin")
    require_role("compliance_officer", "admin")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Sequence

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

logger = logging.getLogger(__name__)

_bearer = HTTPBearer(auto_error=False)


# ── User context ──────────────────────────────────────────────────────────────

@dataclass
class UserContext:
    """Resolved identity injected into every authenticated route."""
    user_id: str
    email: str
    role: str                          # associate | reviewer | compliance_officer | admin
    firm_workspace_id: str | None
    full_name: str | None = None
    is_active: bool = True

    # ── Convenience predicates ─────────────────────────────────────────────────
    def can(self, *roles: str) -> bool:
        return self.role in roles

    def is_reviewer_or_above(self) -> bool:
        return self.role in ("reviewer", "compliance_officer", "admin")

    def is_admin(self) -> bool:
        return self.role == "admin"


# ── JWT verification ──────────────────────────────────────────────────────────

def _verify_jwt(token: str) -> dict:
    """
    Verify a Supabase-issued JWT against the project JWT secret (HS256).
    Raises HTTPException 401 on any failure.
    """
    settings = get_settings()
    secret = settings.supabase_jwt_secret

    if not secret:
        # Dev mode: skip verification, parse without verification
        logger.warning(
            "SUPABASE_JWT_SECRET not set — JWT verification DISABLED (dev mode only)"
        )
        try:
            return jwt.decode(token, options={"verify_signature": False}, algorithms=["HS256"])
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {e}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",        # Supabase always sets aud=authenticated
            options={"require": ["sub", "exp", "aud"]},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired — please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _lookup_user_profile(user_id: str) -> dict | None:
    """
    Fetch the user's profile from public.users using the service-role client
    (bypasses RLS — this is a backend-only lookup).
    Returns None if Supabase is not configured or lookup fails.
    """
    try:
        from app.db.supabase_client import get_supabase_client
        sb = get_supabase_client()
        result = (
            sb.table("users")
            .select("id, email, full_name, role, firm_workspace_id, is_active")
            .eq("id", user_id)
            .single()
            .execute()
        )
        return result.data
    except Exception as e:
        logger.warning(f"User profile lookup failed for {user_id}: {e}")
        return None


# ── FastAPI dependencies ──────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserContext:
    """
    Resolve and return the authenticated UserContext.
    Raises HTTP 401 if no valid token is provided.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _verify_jwt(credentials.credentials)
    user_id: str = payload["sub"]

    # Try to enrich from Supabase profile; fall back to JWT claims
    profile = _lookup_user_profile(user_id)

    if profile:
        return UserContext(
            user_id=user_id,
            email=profile.get("email", payload.get("email", "")),
            role=profile.get("role", "associate"),
            firm_workspace_id=profile.get("firm_workspace_id"),
            full_name=profile.get("full_name"),
            is_active=profile.get("is_active", True),
        )

    # Supabase not configured / user not yet in public.users — use JWT claims only
    user_meta = payload.get("user_metadata", {})
    app_meta  = payload.get("app_metadata", {})
    return UserContext(
        user_id=user_id,
        email=payload.get("email", ""),
        role=app_meta.get("role", "associate"),
        firm_workspace_id=app_meta.get("firm_workspace_id"),
        full_name=user_meta.get("full_name"),
    )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UserContext | None:
    """
    Like get_current_user but returns None instead of 401 for public routes.
    """
    if not credentials:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_role(*allowed_roles: str):
    """
    Factory for role-gating dependencies.

    Usage:
        @router.delete("/...", dependencies=[Depends(require_role("admin"))])
    """
    async def _dep(user: UserContext = Depends(get_current_user)) -> UserContext:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Insufficient permissions. "
                    f"Required: {list(allowed_roles)}. "
                    f"Your role: {user.role}."
                ),
            )
        return user
    return _dep


def require_same_workspace(workspace_id: str, user: UserContext) -> None:
    """
    Raise HTTP 403 if the user is not in the given workspace.
    Call from route handlers where workspace_id comes from the request body/path.
    """
    if (
        user.firm_workspace_id
        and workspace_id
        and user.firm_workspace_id != workspace_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cross-workspace access denied (FR-7.2).",
        )
