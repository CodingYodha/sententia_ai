"""
Sententia.ai — Docling Document Extraction Service

Parses PDF and DOCX files using Docling (primary) with a PyPDF fallback.
Docling handles multi-column layouts, tables, and complex legal document
structures that simple text extractors miss.

Fallback chain:
  1. Docling (handles tables, multi-column, OCR) — preferred
  2. PyPDF  (text-layer only, fast, no layout)  — fallback if Docling fails
  3. Raw bytes decode                             — last resort for plain text
"""

from __future__ import annotations

import io
import logging
import tempfile
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Try importing Docling ──────────────────────────────────────────────────────
try:
    from docling.document_converter import DocumentConverter
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    _DOCLING_AVAILABLE = True
except ImportError:
    _DOCLING_AVAILABLE = False
    logger.warning("docling not available — will use PyPDF fallback")

# ── Try importing PyPDF ───────────────────────────────────────────────────────
try:
    from pypdf import PdfReader
    _PYPDF_AVAILABLE = True
except ImportError:
    _PYPDF_AVAILABLE = False
    logger.warning("pypdf not available — no PDF fallback")


class DoclingResult:
    """Normalized result from any extraction method."""
    def __init__(
        self,
        text: str,
        method: str,
        page_count: int | None = None,
        tables_found: int = 0,
    ):
        self.text = text
        self.method = method          # "docling" | "pypdf_fallback" | "text_plain"
        self.page_count = page_count
        self.tables_found = tables_found


def _extract_with_docling(file_bytes: bytes, suffix: str) -> DoclingResult:
    """
    Run Docling extraction on the provided file bytes.

    Docling writes to a temp file (it needs a filepath), then extracts
    structured markdown + table text from the document.
    """
    # Configure pipeline — disable OCR for speed unless needed
    pipeline_opts = PdfPipelineOptions()
    pipeline_opts.do_ocr = False           # enable if scanned docs expected
    pipeline_opts.do_table_structure = True

    converter = DocumentConverter()

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        result = converter.convert(tmp_path)
        doc = result.document

        # Export as markdown — preserves table structure
        markdown_text = doc.export_to_markdown()

        # Count tables
        tables_found = len(doc.tables) if hasattr(doc, "tables") else 0

        return DoclingResult(
            text=markdown_text,
            method="docling",
            tables_found=tables_found,
        )
    finally:
        os.unlink(tmp_path)


def _extract_with_pypdf(file_bytes: bytes) -> DoclingResult:
    """
    Fallback: extract text layer only using PyPDF.
    Handles text-based PDFs but loses table structure.
    """
    reader = PdfReader(io.BytesIO(file_bytes))
    pages_text = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages_text.append(text)

    full_text = "\n\n---\n\n".join(pages_text)
    return DoclingResult(
        text=full_text,
        method="pypdf_fallback",
        page_count=len(reader.pages),
    )


def _extract_plain_text(file_bytes: bytes) -> DoclingResult:
    """Last resort: decode as UTF-8 text."""
    text = file_bytes.decode("utf-8", errors="replace")
    return DoclingResult(text=text, method="text_plain")


def extract_document(
    file_bytes: bytes,
    filename: str,
    force_fallback: bool = False,
) -> DoclingResult:
    """
    Main entry point — extract text from a PDF or DOCX file.

    Args:
        file_bytes:     Raw file bytes from the upload.
        filename:       Original filename (used to determine suffix / format).
        force_fallback: If True, skip Docling and use PyPDF directly
                        (useful in tests or low-memory environments).

    Returns:
        DoclingResult with .text, .method, .page_count, .tables_found
    """
    suffix = Path(filename).suffix.lower()

    # ── Docling path ──────────────────────────────────────────────────────────
    if _DOCLING_AVAILABLE and not force_fallback and suffix in {".pdf", ".docx", ".doc"}:
        try:
            logger.info(f"Extracting '{filename}' with Docling")
            return _extract_with_docling(file_bytes, suffix)
        except Exception as e:
            logger.warning(f"Docling failed for '{filename}': {e} — falling back to PyPDF")

    # ── PyPDF fallback (PDF only) ─────────────────────────────────────────────
    if _PYPDF_AVAILABLE and suffix == ".pdf":
        try:
            logger.info(f"Extracting '{filename}' with PyPDF fallback")
            return _extract_with_pypdf(file_bytes)
        except Exception as e:
            logger.warning(f"PyPDF failed for '{filename}': {e}")

    # ── Plain text last resort ────────────────────────────────────────────────
    logger.info(f"Treating '{filename}' as plain text")
    return _extract_plain_text(file_bytes)
