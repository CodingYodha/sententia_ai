"""
Sententia.ai — Intake Router

Endpoints:
  POST /api/intake/document  — file upload → Docling extraction → Instructor structuring
  POST /api/intake/scenario  — scenario form fields → validation → Supabase persist
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.schemas.intake import (
    DocumentExtractionResult,
    ExtractionMethod,
    ScenarioCreate,
    ScenarioResponse,
)
from app.services.docling_service import extract_document
from app.services.instructor_service import structure_document
from app.db.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/intake", tags=["Intake"])

# ── Allowed MIME types ────────────────────────────────────────────────────────
_ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
}
_MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


# ══════════════════════════════════════════════════════════════════════════════
# POST /api/intake/document
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/document",
    response_model=DocumentExtractionResult,
    summary="Upload a document for extraction and structuring",
    status_code=status.HTTP_200_OK,
)
async def intake_document(
    file: UploadFile = File(..., description="PDF or DOCX document to extract"),
) -> DocumentExtractionResult:
    """
    Accepts a PDF or DOCX upload and returns structured extraction:

    1. **Docling** parses the document (tables, multi-column layout, legal structure)
    2. **Instructor + LLM** structures the text into UBOInfo, EquityStake[], ControlRights
    3. Returns all three schemas in a single JSON response

    If no LLM API key is configured, extraction still runs but structuring is skipped
    (llm_structured = false, all schema fields = null/empty).
    """
    warnings: list[str] = []

    # ── Validate file ─────────────────────────────────────────────────────────
    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type: {file.content_type}. Allowed: PDF, DOCX, TXT",
        )

    file_bytes = await file.read()

    if len(file_bytes) > _MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large: {len(file_bytes) / 1024 / 1024:.1f} MB. Max: 20 MB",
        )

    if len(file_bytes) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded",
        )

    filename = file.filename or "upload.pdf"

    # ── Extract ───────────────────────────────────────────────────────────────
    try:
        doc_result = extract_document(file_bytes, filename)
    except Exception as e:
        logger.exception(f"Extraction failed for '{filename}'")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document extraction failed: {str(e)}",
        )

    if not doc_result.text.strip():
        warnings.append("Extracted text is empty — document may be image-only or encrypted")

    # ── Structure ─────────────────────────────────────────────────────────────
    ubo_info, equity_stakes, control_rights, model_used = structure_document(
        extracted_text=doc_result.text,
        filename=filename,
    )
    llm_structured = model_used is not None

    if not llm_structured:
        warnings.append("LLM structuring skipped — no API key configured. Set OPENROUTER_API_KEY or GROQ_API_KEY.")

    # ── Build response ────────────────────────────────────────────────────────
    method_map = {
        "docling":        ExtractionMethod.DOCLING,
        "pypdf_fallback": ExtractionMethod.PYPDF_FALLBACK,
        "text_plain":     ExtractionMethod.TEXT_PLAIN,
    }

    return DocumentExtractionResult(
        filename=filename,
        file_size_bytes=len(file_bytes),
        extraction_method=method_map.get(doc_result.method, ExtractionMethod.TEXT_PLAIN),
        extracted_text_preview=doc_result.text[:500],
        extracted_text_length=len(doc_result.text),
        ubo_info=ubo_info,
        equity_stakes=equity_stakes,
        control_rights=control_rights,
        llm_model_used=model_used,
        llm_structured=llm_structured,
        warnings=warnings,
    )


# ══════════════════════════════════════════════════════════════════════════════
# POST /api/intake/scenario
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/scenario",
    response_model=ScenarioResponse,
    summary="Create a new deal scenario",
    status_code=status.HTTP_201_CREATED,
)
async def intake_scenario(
    payload: ScenarioCreate,
) -> ScenarioResponse:
    """
    Validates and persists a deal scenario per PRD FR-1.1 / FR-1.2.

    **Required fields (FR-1.2):**
    - capital_origin, target_jurisdiction, sector
    - investment_amount_usd, investment_structure_type

    **Optional:** spv_jurisdiction, equity_pct, control_rights_requested,
    regulatory_constraints, investor_profile, notes, uploaded_doc_url

    Returns the created scenario_id for use in subsequent structure-generation calls.
    """
    # ── Persist to Supabase ───────────────────────────────────────────────────
    scenario_id = str(uuid.uuid4())

    row = {
        "id":                      scenario_id,
        "user_id":                 "00000000-0000-0000-0000-000000000000",  # placeholder — replace with auth
        "origin_jurisdiction":     payload.capital_origin,
        "spv_jurisdiction":        payload.spv_jurisdiction,
        "target_jurisdiction":     payload.target_jurisdiction,
        "investment_amount_usd":   payload.investment_amount_usd,
        "equity_pct":              payload.equity_pct,
        "control_rights":          payload.control_rights_requested,
        "uploaded_doc_url":        payload.uploaded_doc_url,
        "notes":                   payload.notes,
        "status":                  "draft",
        "metadata": {
            "sector":                  payload.sector,
            "investment_structure_type": payload.investment_structure_type.value,
            "regulatory_constraints":  payload.regulatory_constraints,
            "investor_profile":        payload.investor_profile.value,
        },
    }

    try:
        client = get_supabase_client()
        client.table("scenarios").insert(row).execute()
        logger.info(f"Scenario created: {scenario_id}")
    except Exception as e:
        logger.warning(f"Supabase insert failed: {e} — returning scenario_id anyway")
        # Don't crash if Supabase isn't wired yet — return the ID so callers can proceed
        # In production, this should raise an HTTPException

    return ScenarioResponse(
        scenario_id=scenario_id,
        status="created",
        capital_origin=payload.capital_origin,
        target_jurisdiction=payload.target_jurisdiction,
        sector=payload.sector,
        investment_amount_usd=payload.investment_amount_usd,
        investment_structure_type=payload.investment_structure_type.value,
        spv_jurisdiction=payload.spv_jurisdiction,
        equity_pct=payload.equity_pct,
        investor_profile=payload.investor_profile.value,
    )
