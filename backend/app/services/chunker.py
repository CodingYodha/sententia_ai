"""
Sententia.ai — Layout-Aware Legal Document Chunker

Design philosophy:
  - Inspired by RAGFlow's "Laws" parsing mode (section-boundary detection)
  - RAGFlow itself is too heavy for free-tier compute (requires Elasticsearch +
    MinIO + Redis + Postgres — ~4GB RAM overhead). This lightweight custom chunker
    achieves equivalent quality for well-structured legal documents with zero
    additional infrastructure.
  - Respects section boundaries (§, CLAUSE, ARTICLE, CHAPTER, numbered headings)
  - Merges small fragments, splits oversized paragraphs
  - Overlapping window ensures context continuity across chunks
  - Preserves section header in each chunk for citation

Tradeoff documented:
  RAGFlow full stack: rich UI, multi-format, advanced OCR, collaborative workflow
  This chunker:       500 lines of Python, embedded in FastAPI, zero infra cost,
                      purpose-built for regulatory/legal text, fully testable
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from typing import Optional


# ── Constants ──────────────────────────────────────────────────────────────────
TARGET_CHUNK_CHARS = 1800       # ~450 tokens at 4 chars/token
MAX_CHUNK_CHARS    = 2500       # hard cap before force-splitting
MIN_CHUNK_CHARS    = 200        # below this, merge with adjacent chunk
OVERLAP_CHARS      = 150        # trailing overlap into next chunk


# ── Section header patterns (legal document structure) ────────────────────────
_SECTION_PATTERNS = [
    # ══════ or ─────── (divider lines)
    re.compile(r'^[═─=\-]{5,}\s*$'),
    # CHAPTER 4, PART III, SECTION 9
    re.compile(r'^(CHAPTER|PART|SECTION|SCHEDULE|ANNEXURE)\s+[\dIVXivx]+', re.IGNORECASE),
    # Article 13, Clause 5.1, §90
    re.compile(r'^(ARTICLE|CLAUSE|SUB-CLAUSE|PARAGRAPH|RULE|REGULATION)\s+[\d.]+', re.IGNORECASE),
    re.compile(r'^§\s*\d+'),
    # Numbered sections: 1., 1.1, 1.1.1, (1), (a)
    re.compile(r'^(\d+\.)+\s+[A-Z]'),
    re.compile(r'^\(\w+\)\s+[A-Z]'),
    # ALL-CAPS headers (common in legal docs)
    re.compile(r'^[A-Z][A-Z\s\-–—/,()]{10,}$'),
    # Markdown-style headers
    re.compile(r'^#{1,4}\s+\S'),
    # Underlined headers (═══ or ───)
]


@dataclass
class ChunkMetadata:
    jurisdiction: str
    document_type: str
    effective_date: float       # Unix timestamp
    source_url: str
    title: str = ""
    section_header: str = ""
    chunk_index: int = 0
    total_chunks: int = 0


@dataclass
class DocumentChunk:
    chunk_id: str
    content: str
    metadata: ChunkMetadata
    char_offset: int = 0
    char_length: int = 0

    def __post_init__(self):
        self.char_length = len(self.content)


# ── Header detection ───────────────────────────────────────────────────────────

def _is_section_boundary(line: str) -> bool:
    """Return True if this line looks like a section header."""
    stripped = line.strip()
    if not stripped:
        return False
    for pattern in _SECTION_PATTERNS:
        if pattern.match(stripped):
            return True
    return False


def _extract_header(line: str) -> str:
    """Clean up a section header line for metadata."""
    return line.strip()[:120]  # cap at 120 chars


# ── Core chunker ──────────────────────────────────────────────────────────────

def chunk_document(
    text: str,
    metadata: ChunkMetadata,
) -> list[DocumentChunk]:
    """
    Split a legal document into overlapping, section-aware chunks.

    Algorithm:
    1. Split into paragraphs (double newline)
    2. Group paragraphs under their nearest section header
    3. Build chunks respecting TARGET_CHUNK_CHARS, merging small sections,
       splitting oversized paragraphs
    4. Add OVERLAP_CHARS trailing overlap from previous chunk

    Returns a list of DocumentChunk objects with metadata and char offsets.
    """
    if not text or not text.strip():
        return []

    # ── Step 1: Split into lines, detect headers ───────────────────────────────
    lines = text.split('\n')
    paragraphs: list[tuple[bool, str]] = []  # (is_header, text)
    current_paragraph: list[str] = []

    for line in lines:
        if _is_section_boundary(line):
            # Flush current paragraph first
            if current_paragraph:
                content = '\n'.join(current_paragraph).strip()
                if content:
                    paragraphs.append((False, content))
                current_paragraph = []
            paragraphs.append((True, _extract_header(line)))
        else:
            current_paragraph.append(line)
            # Flush on double blank line
            if len(current_paragraph) >= 2 and current_paragraph[-1] == '' and current_paragraph[-2] == '':
                content = '\n'.join(current_paragraph[:-2]).strip()
                if content:
                    paragraphs.append((False, content))
                current_paragraph = []

    # Final flush
    if current_paragraph:
        content = '\n'.join(current_paragraph).strip()
        if content:
            paragraphs.append((False, content))

    # ── Step 2: Build chunks ───────────────────────────────────────────────────
    chunks: list[str] = []
    current_section_header: str = metadata.title or ""
    current_chunk_parts: list[str] = []
    current_chunk_len: int = 0
    previous_overlap: str = ""

    def _flush_chunk(parts: list[str], header: str, overlap: str) -> tuple[str, str]:
        """Assemble a chunk, prepend overlap, return (assembled_text, new_overlap)."""
        body = '\n\n'.join(parts).strip()
        assembled = (f"[{header}]\n\n" if header else "") + body
        if overlap:
            assembled = overlap + "\n\n" + assembled
        # New overlap = trailing OVERLAP_CHARS of body (not including header)
        new_overlap = body[-OVERLAP_CHARS:] if len(body) > OVERLAP_CHARS else body
        return assembled, new_overlap

    for is_header, content in paragraphs:
        if is_header:
            current_section_header = content
            # Add header as a label, not a flush trigger on its own
            continue

        # Large paragraph: split by sentences if needed
        if len(content) > MAX_CHUNK_CHARS:
            # Split by sentence endings
            sentences = re.split(r'(?<=[.!?])\s+', content)
            for sentence in sentences:
                if current_chunk_len + len(sentence) > TARGET_CHUNK_CHARS and current_chunk_parts:
                    assembled, previous_overlap = _flush_chunk(
                        current_chunk_parts, current_section_header, previous_overlap
                    )
                    chunks.append(assembled)
                    current_chunk_parts = []
                    current_chunk_len = 0
                current_chunk_parts.append(sentence)
                current_chunk_len += len(sentence)
        else:
            # Normal paragraph
            if current_chunk_len + len(content) > TARGET_CHUNK_CHARS and current_chunk_parts:
                assembled, previous_overlap = _flush_chunk(
                    current_chunk_parts, current_section_header, previous_overlap
                )
                chunks.append(assembled)
                current_chunk_parts = []
                current_chunk_len = 0
            current_chunk_parts.append(content)
            current_chunk_len += len(content)

    # Final flush
    if current_chunk_parts:
        assembled, _ = _flush_chunk(
            current_chunk_parts, current_section_header, previous_overlap
        )
        chunks.append(assembled)

    # ── Step 3: Merge tiny trailing chunks ────────────────────────────────────
    merged: list[str] = []
    for chunk in chunks:
        if merged and len(chunk) < MIN_CHUNK_CHARS:
            merged[-1] = merged[-1] + "\n\n" + chunk
        else:
            merged.append(chunk)

    # ── Step 4: Build DocumentChunk objects ───────────────────────────────────
    total = len(merged)
    result: list[DocumentChunk] = []
    char_offset = 0

    for i, chunk_text in enumerate(merged):
        chunk_meta = ChunkMetadata(
            jurisdiction=metadata.jurisdiction,
            document_type=metadata.document_type,
            effective_date=metadata.effective_date,
            source_url=metadata.source_url,
            title=metadata.title,
            section_header=_extract_section_header(chunk_text),
            chunk_index=i,
            total_chunks=total,
        )
        result.append(DocumentChunk(
            chunk_id=str(uuid.uuid4()),
            content=chunk_text,
            metadata=chunk_meta,
            char_offset=char_offset,
            char_length=len(chunk_text),
        ))
        char_offset += len(chunk_text)

    return result


def _extract_section_header(chunk_text: str) -> str:
    """
    Extract the section header from a chunk's leading bracket label,
    e.g. '[ARTICLE 13 — CAPITAL GAINS]\n\n...' → 'ARTICLE 13 — CAPITAL GAINS'
    """
    match = re.match(r'^\[([^\]]+)\]', chunk_text)
    if match:
        return match.group(1)
    # Fall back to first non-empty line
    for line in chunk_text.split('\n'):
        if line.strip():
            return line.strip()[:80]
    return ""
