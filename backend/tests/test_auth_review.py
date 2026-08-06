"""
Tests for auth dependency, audit service, and review/corrections endpoints.
Marked 'not integration' — no real Supabase or JWT secret required.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.dependencies.auth import (
    UserContext,
    _verify_jwt,
    require_role,
)
from app.main import app
from app.services import audit_service, review_queue_service


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_token(
    sub: str = "test-uid",
    email: str = "reviewer@example.com",
    role: str = "reviewer",
    secret: str = "testsecret",
    expired: bool = False,
) -> str:
    exp = datetime.now(timezone.utc) + (timedelta(seconds=-1) if expired else timedelta(hours=1))
    return jwt.encode(
        {"sub": sub, "email": email, "aud": "authenticated",
         "app_metadata": {"role": role}, "exp": exp},
        secret,
        algorithm="HS256",
    )


@pytest.fixture
def reviewer_token() -> str:
    return make_token(role="reviewer")


@pytest.fixture
def associate_token() -> str:
    return make_token(role="associate", email="associate@example.com")


@pytest.fixture
def admin_token() -> str:
    return make_token(role="admin", email="admin@example.com")


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ── JWT verification ──────────────────────────────────────────────────────────

class TestJWTVerification:
    def test_verify_valid_token_without_secret(self):
        """Dev mode: valid token parsed without verification when secret not set."""
        token = make_token()
        with patch("app.dependencies.auth.get_settings") as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = ""
            payload = _verify_jwt(token)
        assert payload["sub"] == "test-uid"
        assert payload["email"] == "reviewer@example.com"

    def test_verify_valid_token_with_secret(self):
        """Prod mode: token verified against secret."""
        token = make_token(secret="mysecret")
        with patch("app.dependencies.auth.get_settings") as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "mysecret"
            payload = _verify_jwt(token)
        assert payload["sub"] == "test-uid"

    def test_verify_expired_token_raises_401(self):
        from fastapi import HTTPException
        token = make_token(secret="mysecret", expired=True)
        with patch("app.dependencies.auth.get_settings") as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "mysecret"
            with pytest.raises(HTTPException) as exc_info:
                _verify_jwt(token)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_verify_wrong_secret_raises_401(self):
        from fastapi import HTTPException
        token = make_token(secret="correct")
        with patch("app.dependencies.auth.get_settings") as mock_settings:
            mock_settings.return_value.supabase_jwt_secret = "wrong"
            with pytest.raises(HTTPException) as exc_info:
                _verify_jwt(token)
        assert exc_info.value.status_code == 401


# ── UserContext ───────────────────────────────────────────────────────────────

class TestUserContext:
    def test_role_predicates(self):
        reviewer = UserContext(user_id="u1", email="r@test.com", role="reviewer",
                               firm_workspace_id="ws1")
        assert reviewer.is_reviewer_or_above()
        assert not reviewer.is_admin()
        assert reviewer.can("reviewer", "admin")

    def test_associate_cannot_review(self):
        associate = UserContext(user_id="u2", email="a@test.com", role="associate",
                                firm_workspace_id="ws1")
        assert not associate.is_reviewer_or_above()
        assert not associate.is_admin()

    def test_admin_is_reviewer_or_above(self):
        admin = UserContext(user_id="u3", email="a@test.com", role="admin",
                            firm_workspace_id="ws1")
        assert admin.is_reviewer_or_above()
        assert admin.is_admin()


# ── Review endpoint: action ────────────────────────────────────────────────────

class TestReviewActionEndpoint:
    def test_action_requires_auth(self, client: TestClient):
        r = client.post("/api/review/action", json={
            "structure_id": "s1", "action": "approve"
        })
        assert r.status_code == 401

    def test_action_requires_reviewer_role(self, client: TestClient, associate_token: str):
        with (
            patch("app.dependencies.auth.get_settings") as ms,
            patch("app.dependencies.auth._lookup_user_profile") as mp,
        ):
            ms.return_value.supabase_jwt_secret = ""
            mp.return_value = None  # Use JWT claims
            r = client.post(
                "/api/review/action",
                json={"structure_id": "s1", "action": "approve"},
                headers={"Authorization": f"Bearer {associate_token}"},
            )
        assert r.status_code == 403

    def test_approve_succeeds_for_reviewer(self, client: TestClient, reviewer_token: str):
        with (
            patch("app.dependencies.auth.get_settings") as ms,
            patch("app.dependencies.auth._lookup_user_profile") as mp,
            patch("app.services.review_queue_service._sb") as msb,
            patch("app.services.audit_service._write_audit_row"),
        ):
            ms.return_value.supabase_jwt_secret = ""
            mp.return_value = None
            msb.return_value = None  # in-memory fallback

            r = client.post(
                "/api/review/action",
                json={"structure_id": "struct-001", "action": "approve",
                      "structure_name": "Primary Structure", "reviewer_role": "reviewer"},
                headers={"Authorization": f"Bearer {reviewer_token}"},
            )
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "approve"
        assert data["structure_id"] == "struct-001"
        assert "approved" in data["message"].lower()

    def test_flag_action(self, client: TestClient, reviewer_token: str):
        with (
            patch("app.dependencies.auth.get_settings") as ms,
            patch("app.dependencies.auth._lookup_user_profile") as mp,
            patch("app.services.review_queue_service._sb") as msb,
            patch("app.services.audit_service._write_audit_row"),
        ):
            ms.return_value.supabase_jwt_secret = ""
            mp.return_value = None
            msb.return_value = None

            r = client.post(
                "/api/review/action",
                json={"structure_id": "struct-002", "action": "flag",
                      "notes": "Missing DPIIT filing requirement"},
                headers={"Authorization": f"Bearer {reviewer_token}"},
            )
        assert r.status_code == 200
        assert r.json()["action"] == "flag"


# ── Review endpoint: correction ────────────────────────────────────────────────

class TestCorrectionEndpoint:
    def test_correction_requires_reviewer(self, client: TestClient, associate_token: str):
        with (
            patch("app.dependencies.auth.get_settings") as ms,
            patch("app.dependencies.auth._lookup_user_profile") as mp,
        ):
            ms.return_value.supabase_jwt_secret = ""
            mp.return_value = None
            r = client.post(
                "/api/review/correction",
                json={
                    "review_queue_id": "rq1", "structure_id": "s1",
                    "correction_type": "jurisdiction_error",
                    "affected_field": "ownership_chain",
                    "corrected_value": "Cayman Islands (not Singapore)",
                },
                headers={"Authorization": f"Bearer {associate_token}"},
            )
        assert r.status_code == 403

    def test_valid_correction_returns_201(self, client: TestClient, reviewer_token: str):
        with (
            patch("app.dependencies.auth.get_settings") as ms,
            patch("app.dependencies.auth._lookup_user_profile") as mp,
            patch("app.services.review_queue_service._sb") as msb,
            patch("app.services.audit_service._write_audit_row"),
        ):
            ms.return_value.supabase_jwt_secret = ""
            mp.return_value = None
            msb.return_value = None

            r = client.post(
                "/api/review/correction",
                json={
                    "review_queue_id": "rq-test-1",
                    "structure_id": "struct-test-1",
                    "correction_type": "ownership_threshold",
                    "affected_field": "compliance_touchpoints[0].requirement",
                    "original_value": "25% threshold",
                    "corrected_value": "10% threshold (Press Note 3/2020, land-border UBO)",
                    "jurisdiction": "India",
                    "severity": "high",
                    "notes": "DPIIT circular updated threshold for Chinese UBOs",
                },
                headers={"Authorization": f"Bearer {reviewer_token}"},
            )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["correction_type"] == "ownership_threshold"
        assert data["affected_field"] == "compliance_touchpoints[0].requirement"
        assert data["severity"] == "high"
        assert "correction_id" in data

    def test_invalid_correction_type_returns_422(self, client: TestClient, reviewer_token: str):
        with (
            patch("app.dependencies.auth.get_settings") as ms,
            patch("app.dependencies.auth._lookup_user_profile") as mp,
            patch("app.services.review_queue_service._sb") as msb,
        ):
            ms.return_value.supabase_jwt_secret = ""
            mp.return_value = None
            msb.return_value = None

            r = client.post(
                "/api/review/correction",
                json={
                    "review_queue_id": "rq1", "structure_id": "s1",
                    "correction_type": "not_a_real_type",
                    "affected_field": "some_field",
                    "corrected_value": "something",
                },
                headers={"Authorization": f"Bearer {reviewer_token}"},
            )
        assert r.status_code in (422, 422)

    @pytest.mark.parametrize("ct", [
        "jurisdiction_error", "ownership_threshold", "regulatory_gap",
        "tax_issue", "structure_type_wrong", "risk_severity_wrong",
        "missing_touchpoint", "citation_error", "treaty_benefit_wrong",
        "gaar_issue", "other",
    ])
    def test_all_correction_types_are_valid(self, client: TestClient, reviewer_token: str, ct: str):
        """All 11 correction_type values in VALID_CORRECTION_TYPES pass validation."""
        with (
            patch("app.dependencies.auth.get_settings") as ms,
            patch("app.dependencies.auth._lookup_user_profile") as mp,
            patch("app.services.review_queue_service._sb") as msb,
            patch("app.services.audit_service._write_audit_row"),
        ):
            ms.return_value.supabase_jwt_secret = ""
            mp.return_value = None
            msb.return_value = None

            r = client.post(
                "/api/review/correction",
                json={
                    "review_queue_id": "rq1", "structure_id": "s1",
                    "correction_type": ct,
                    "affected_field": "some_field",
                    "corrected_value": "correct_value",
                },
                headers={"Authorization": f"Bearer {reviewer_token}"},
            )
        assert r.status_code == 201, f"Expected 201 for type={ct}, got {r.status_code}: {r.text}"


# ── Audit service ─────────────────────────────────────────────────────────────

class TestAuditService:
    def test_audit_log_does_not_raise(self):
        """audit_log must never raise — always fire-and-forget."""
        user = UserContext(user_id="u1", email="t@t.com", role="reviewer",
                           firm_workspace_id="ws1")
        # Should not raise even without Supabase
        with patch("app.services.audit_service._write_audit_row") as mock:
            mock.side_effect = Exception("DB down")
            # Should not propagate
            audit_service.audit_log("test.action", "review", user=user)

    def test_audit_wrappers_exist(self):
        """All convenience wrappers are importable and callable."""
        assert callable(audit_service.audit_structure_generated)
        assert callable(audit_service.audit_compliance_checked)
        assert callable(audit_service.audit_diagram_exported)
        assert callable(audit_service.audit_review_submitted)
        assert callable(audit_service.audit_user_login)


# ── Review queue service ───────────────────────────────────────────────────────

class TestReviewQueueService:
    @pytest.mark.asyncio
    async def test_auto_enqueue_uses_fallback(self):
        with patch("app.services.review_queue_service._sb") as msb:
            msb.return_value = None  # no Supabase
            review_queue_service._queue_fallback.clear()

            review_id = await review_queue_service.auto_enqueue(
                structure_id="st-001",
                scenario_id="sc-001",
                structure_name="Primary Structure",
                structure_rank=1,
                structure_json={"name": "Primary"},
                compliance_result=None,
                generated_by=None,
            )
            assert review_id
            assert any(q["structure_id"] == "st-001"
                       for q in review_queue_service._queue_fallback)

    @pytest.mark.asyncio
    async def test_submit_decision_requires_reviewer(self):
        associate = UserContext(user_id="u1", email="a@t.com", role="associate",
                                firm_workspace_id="ws1")
        with pytest.raises(PermissionError):
            await review_queue_service.submit_decision(
                review_queue_id="rq1",
                action="approved",
                reviewer=associate,
                notes=None,
            )

    @pytest.mark.asyncio
    async def test_valid_correction_types(self):
        reviewer = UserContext(user_id="u1", email="r@t.com", role="reviewer",
                               firm_workspace_id="ws1")
        with patch("app.services.review_queue_service._sb") as msb:
            msb.return_value = None

            for ct in review_queue_service.VALID_CORRECTION_TYPES:
                cid = await review_queue_service.add_correction(
                    review_queue_id="rq1",
                    structure_id="st1",
                    reviewer=reviewer,
                    correction_type=ct,
                    affected_field="some.field",
                    corrected_value="correct",
                )
                assert cid

    @pytest.mark.asyncio
    async def test_invalid_correction_type_raises(self):
        reviewer = UserContext(user_id="u1", email="r@t.com", role="reviewer",
                               firm_workspace_id="ws1")
        with pytest.raises(ValueError, match="Invalid correction_type"):
            await review_queue_service.add_correction(
                review_queue_id="rq1",
                structure_id="st1",
                reviewer=reviewer,
                correction_type="fake_type",
                affected_field="field",
                corrected_value="value",
            )
