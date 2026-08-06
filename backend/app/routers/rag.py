"""
Sententia.ai — RAG Router

Endpoints:
  POST /api/rag/query — semantic search over regulatory corpus
  GET  /api/rag/corpus — list ingested documents with metadata
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel, Field

from app.services.rag_service import (
    query_rag,
    query_multi_jurisdiction,
    format_chunks_as_context,
    RetrievedChunk,
    RAGQueryResult,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["RAG"])


# ── Request / Response schemas ────────────────────────────────────────────────

class RAGQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500, description="Natural language query")
    jurisdiction: str | None = Field(
        default=None,
        description="Filter by single jurisdiction: INDIA, SINGAPORE, UNITED_STATES, EUROPEAN_UNION, GLOBAL"
    )
    jurisdictions: list[str] | None = Field(
        default=None,
        description="Filter to any of these jurisdictions (OR). Use instead of jurisdiction for multi-corridor."
    )
    document_type: str | None = Field(
        default=None,
        description="Filter by document type: statute, policy_note, treaty, regulation, commentary"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")
    score_threshold: float = Field(default=0.30, ge=0.0, le=1.0, description="Minimum similarity score")
    include_formatted_context: bool = Field(
        default=False,
        description="If true, also return chunks formatted as a single LLM context string"
    )


class ChunkResponse(BaseModel):
    chunk_id: str
    content: str
    score: float
    jurisdiction: str
    document_type: str
    effective_date: float | None
    source_url: str
    title: str
    section_header: str
    chunk_index: int
    total_chunks: int


class RAGQueryResponse(BaseModel):
    query: str
    top_k: int
    total_matches: int
    embedding_provider: str
    filters_applied: dict
    chunks: list[ChunkResponse]
    formatted_context: str | None = None


class CorridorQueryRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=500)
    origin_jurisdiction: str = Field(..., description="Capital origin jurisdiction, e.g. 'CHINA'")
    target_jurisdiction: str = Field(..., description="Target investment jurisdiction, e.g. 'INDIA'")
    spv_jurisdiction: str | None = Field(default=None, description="SPV jurisdiction, e.g. 'SINGAPORE'")
    top_k: int = Field(default=8, ge=1, le=20)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post(
    "/query",
    response_model=RAGQueryResponse,
    summary="Semantic search over the regulatory corpus",
    status_code=status.HTTP_200_OK,
)
async def rag_query(payload: RAGQueryRequest) -> RAGQueryResponse:
    """
    Retrieve top-k regulatory corpus chunks most semantically similar to the query.

    Supports jurisdiction and document_type filters for targeted retrieval.
    Use `include_formatted_context=true` to get a pre-formatted LLM context string.

    **Jurisdictions available:** INDIA, SINGAPORE, UNITED_STATES, EUROPEAN_UNION, GLOBAL

    **Document types:** statute, policy_note, treaty, regulation, commentary
    """
    result = await query_rag(
        query=payload.query,
        top_k=payload.top_k,
        jurisdiction=payload.jurisdiction,
        document_type=payload.document_type,
        jurisdictions=payload.jurisdictions,
        score_threshold=payload.score_threshold,
    )

    chunks = [
        ChunkResponse(
            chunk_id=c.chunk_id,
            content=c.content,
            score=c.score,
            jurisdiction=c.jurisdiction,
            document_type=c.document_type,
            effective_date=c.effective_date,
            source_url=c.source_url,
            title=c.title,
            section_header=c.section_header,
            chunk_index=c.chunk_index,
            total_chunks=c.total_chunks,
        )
        for c in result.chunks
    ]

    formatted = None
    if payload.include_formatted_context:
        formatted = format_chunks_as_context(result)

    return RAGQueryResponse(
        query=result.query,
        top_k=result.top_k,
        total_matches=result.total_matches,
        embedding_provider=result.embedding_provider,
        filters_applied=result.filters_applied,
        chunks=chunks,
        formatted_context=formatted,
    )


@router.post(
    "/query/corridor",
    response_model=RAGQueryResponse,
    summary="Corridor-aware RAG — retrieves from all relevant jurisdictions at once",
    status_code=status.HTTP_200_OK,
)
async def rag_corridor_query(payload: CorridorQueryRequest) -> RAGQueryResponse:
    """
    Retrieve regulatory context for a specific investment corridor.

    Automatically filters to: origin jurisdiction, target jurisdiction,
    SPV jurisdiction (if provided), and GLOBAL sources.

    This is the endpoint used internally by the structure generation engine.
    """
    result = await query_multi_jurisdiction(
        query=payload.query,
        origin=payload.origin_jurisdiction,
        target=payload.target_jurisdiction,
        spv=payload.spv_jurisdiction,
        top_k=payload.top_k,
    )

    chunks = [
        ChunkResponse(
            chunk_id=c.chunk_id,
            content=c.content,
            score=c.score,
            jurisdiction=c.jurisdiction,
            document_type=c.document_type,
            effective_date=c.effective_date,
            source_url=c.source_url,
            title=c.title,
            section_header=c.section_header,
            chunk_index=c.chunk_index,
            total_chunks=c.total_chunks,
        )
        for c in result.chunks
    ]

    return RAGQueryResponse(
        query=result.query,
        top_k=result.top_k,
        total_matches=result.total_matches,
        embedding_provider=result.embedding_provider,
        filters_applied=result.filters_applied,
        chunks=chunks,
        formatted_context=format_chunks_as_context(result),
    )


@router.get(
    "/corpus",
    summary="List all ingested corpus documents",
    status_code=status.HTTP_200_OK,
)
async def list_corpus() -> dict:
    """
    Returns the metadata registry of all ingested corpus documents.
    Reads from corpus/metadata.json — updated each time ingest_corpus.py runs.
    """
    import json
    from pathlib import Path

    metadata_path = Path(__file__).parent.parent.parent / "corpus" / "metadata.json"
    if not metadata_path.exists():
        return {"documents": [], "note": "Corpus not yet ingested. Run scripts/ingest_corpus.py"}

    with open(metadata_path) as f:
        registry = json.load(f)

    return {
        "total_documents": len(registry),
        "documents": [
            {"filename": filename, **meta}
            for filename, meta in registry.items()
        ]
    }
