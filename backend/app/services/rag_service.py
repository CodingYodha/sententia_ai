"""
Sententia.ai — RAG Service

Retrieval-Augmented Generation layer:
  - Accepts a natural-language query + optional jurisdiction/document_type filters
  - Embeds the query via embedding_service (Jina → Google fallback)
  - Searches Qdrant collection with optional payload filters
  - Returns top-k chunks with scores and full citation metadata

Design note on the Qdrant search:
  - Uses cosine similarity (collection is configured with Cosine distance)
  - Optional pre-filtering on jurisdiction and document_type payload fields
  - Score threshold of 0.35 — below this, chunks are likely irrelevant
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, MatchAny

from app.services.embedding_service import embed_query
from app.config import get_settings

logger = logging.getLogger(__name__)

# ── Qdrant collection name (must match setup_qdrant.py) ───────────────────────
COLLECTION_NAME = "regulatory_corpus"

# ── Score threshold — below this, results are too dissimilar to be useful ─────
SCORE_THRESHOLD = 0.30


@dataclass
class RetrievedChunk:
    """A single retrieved chunk with metadata and relevance score."""
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


@dataclass
class RAGQueryResult:
    """Full result from a RAG query."""
    query: str
    top_k: int
    chunks: list[RetrievedChunk] = field(default_factory=list)
    embedding_provider: str = ""
    filters_applied: dict = field(default_factory=dict)
    total_matches: int = 0


# ── Client singleton ───────────────────────────────────────────────────────────
_qdrant_client: AsyncQdrantClient | None = None


def _get_qdrant_client() -> AsyncQdrantClient:
    global _qdrant_client
    if _qdrant_client is None:
        settings = get_settings()
        if settings.qdrant_url:
            _qdrant_client = AsyncQdrantClient(
                url=settings.qdrant_url,
                api_key=settings.qdrant_api_key or None,
                timeout=30,
            )
        else:
            # In-memory Qdrant for local dev / tests without Qdrant server
            _qdrant_client = AsyncQdrantClient(":memory:")
            logger.warning("Using in-memory Qdrant — data will not persist. Set QDRANT_URL in .env")
    return _qdrant_client


# ── Filter builder ────────────────────────────────────────────────────────────

def _build_filter(
    jurisdiction: str | None = None,
    document_type: str | None = None,
    jurisdictions: list[str] | None = None,
) -> Filter | None:
    """Build Qdrant filter from optional jurisdiction and document_type."""
    conditions = []

    if jurisdiction:
        conditions.append(
            FieldCondition(key="jurisdiction", match=MatchValue(value=jurisdiction.upper()))
        )
    elif jurisdictions:
        conditions.append(
            FieldCondition(key="jurisdiction", match=MatchAny(any=[j.upper() for j in jurisdictions]))
        )

    if document_type:
        conditions.append(
            FieldCondition(key="document_type", match=MatchValue(value=document_type.lower()))
        )

    if not conditions:
        return None

    from qdrant_client.http.models import Filter as QFilter
    return QFilter(must=conditions)


# ── Main query function ────────────────────────────────────────────────────────

async def query_rag(
    query: str,
    top_k: int = 5,
    jurisdiction: str | None = None,
    document_type: str | None = None,
    jurisdictions: list[str] | None = None,
    score_threshold: float = SCORE_THRESHOLD,
) -> RAGQueryResult:
    """
    Execute a RAG query against the regulatory corpus.

    Args:
        query:           Natural language query string
        top_k:           Number of results to return (default 5, max 20)
        jurisdiction:    Optional single jurisdiction filter (e.g. "INDIA")
        document_type:   Optional document type filter (e.g. "statute", "treaty")
        jurisdictions:   Optional list of jurisdictions to include (OR filter)
        score_threshold: Minimum similarity score to include in results

    Returns:
        RAGQueryResult with ranked chunks and metadata
    """
    top_k = min(max(top_k, 1), 20)

    # ── Embed query ────────────────────────────────────────────────────────────
    try:
        query_vector, provider = await embed_query(query)
    except RuntimeError as e:
        logger.error(f"Query embedding failed: {e}")
        return RAGQueryResult(
            query=query,
            top_k=top_k,
            chunks=[],
            embedding_provider="none",
            total_matches=0,
        )

    # ── Build filter ───────────────────────────────────────────────────────────
    qdrant_filter = _build_filter(jurisdiction, document_type, jurisdictions)
    filters_applied = {}
    if jurisdiction:
        filters_applied["jurisdiction"] = jurisdiction
    elif jurisdictions:
        filters_applied["jurisdictions"] = jurisdictions
    if document_type:
        filters_applied["document_type"] = document_type

    # ── Search Qdrant ──────────────────────────────────────────────────────────
    client = _get_qdrant_client()
    try:
        results = await client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vector,
            query_filter=qdrant_filter,
            limit=top_k,
            score_threshold=score_threshold,
            with_payload=True,
        )
    except Exception as e:
        logger.error(f"Qdrant search failed: {e}")
        return RAGQueryResult(
            query=query,
            top_k=top_k,
            chunks=[],
            embedding_provider=provider,
            filters_applied=filters_applied,
            total_matches=0,
        )

    # ── Map results ────────────────────────────────────────────────────────────
    chunks: list[RetrievedChunk] = []
    for hit in results:
        payload = hit.payload or {}
        chunks.append(RetrievedChunk(
            chunk_id=str(hit.id),
            content=payload.get("content", ""),
            score=round(hit.score, 4),
            jurisdiction=payload.get("jurisdiction", "UNKNOWN"),
            document_type=payload.get("document_type", "unknown"),
            effective_date=payload.get("effective_date"),
            source_url=payload.get("source_url", ""),
            title=payload.get("title", ""),
            section_header=payload.get("section_header", ""),
            chunk_index=payload.get("chunk_index", 0),
            total_chunks=payload.get("total_chunks", 0),
        ))

    return RAGQueryResult(
        query=query,
        top_k=top_k,
        chunks=chunks,
        embedding_provider=provider,
        filters_applied=filters_applied,
        total_matches=len(chunks),
    )


async def query_multi_jurisdiction(
    query: str,
    origin: str,
    target: str,
    spv: str | None = None,
    top_k: int = 8,
) -> RAGQueryResult:
    """
    Convenience function for corridor-aware RAG — retrieves chunks relevant to
    the origin, target, and optional SPV jurisdictions, plus global sources.

    Used by the structure generation engine to ground LLM calls with
    jurisdiction-specific regulatory context.
    """
    jurisdictions = [origin.upper(), target.upper(), "GLOBAL"]
    if spv:
        jurisdictions.append(spv.upper())

    return await query_rag(
        query=query,
        top_k=top_k,
        jurisdictions=jurisdictions,
        score_threshold=SCORE_THRESHOLD,
    )


def format_chunks_as_context(result: RAGQueryResult) -> str:
    """
    Format RAG results as a context string for LLM prompt injection.

    Format:
        [SOURCE 1 — INDIA / statute / India FDI Policy (score: 0.87)]
        <chunk content>

        [SOURCE 2 — GLOBAL / commentary / OECD Model Tax Convention (score: 0.81)]
        <chunk content>
    """
    if not result.chunks:
        return "No relevant regulatory context found in corpus."

    parts = []
    for i, chunk in enumerate(result.chunks, 1):
        date_str = ""
        if chunk.effective_date:
            from datetime import datetime, timezone
            dt = datetime.fromtimestamp(chunk.effective_date, tz=timezone.utc)
            date_str = f" | effective {dt.strftime('%Y-%m-%d')}"

        header = (
            f"[SOURCE {i} — {chunk.jurisdiction} / {chunk.document_type} / "
            f"{chunk.title}{date_str} | score: {chunk.score}]"
        )
        if chunk.section_header and chunk.section_header not in chunk.content[:100]:
            header += f"\nSection: {chunk.section_header}"

        parts.append(f"{header}\n{chunk.content}")

    return "\n\n---\n\n".join(parts)
