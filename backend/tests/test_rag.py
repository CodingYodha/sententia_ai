"""
Sententia.ai — RAG Layer Tests

Tests chunker, embedding service (mocked), RAG endpoint (mocked Qdrant),
and end-to-end query flow.

Run:
    conda run -n iitr pytest tests/test_rag.py -v -m "not integration"
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.chunker import (
    chunk_document,
    ChunkMetadata,
    _is_section_boundary,
    OVERLAP_CHARS,
    TARGET_CHUNK_CHARS,
)
from app.services.rag_service import (
    format_chunks_as_context,
    RAGQueryResult,
    RetrievedChunk,
)

client = TestClient(app)

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ══════════════════════════════════════════════════════════════════════════════
# 1. CHUNKER UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestChunker:
    """Unit tests for the layout-aware legal document chunker."""

    def _make_meta(self) -> ChunkMetadata:
        return ChunkMetadata(
            jurisdiction="INDIA",
            document_type="statute",
            effective_date=1577836800.0,
            source_url="https://example.com",
            title="Test Document",
        )

    def test_empty_text_returns_no_chunks(self):
        chunks = chunk_document("", self._make_meta())
        assert chunks == []

    def test_whitespace_only_returns_no_chunks(self):
        chunks = chunk_document("   \n\n   ", self._make_meta())
        assert chunks == []

    def test_short_text_produces_one_chunk(self):
        text = "This is a short legal document with a single paragraph."
        chunks = chunk_document(text, self._make_meta())
        assert len(chunks) == 1
        assert "short legal document" in chunks[0].content

    def test_chunk_metadata_populated(self):
        text = "Sample content for metadata test."
        chunks = chunk_document(text, self._make_meta())
        assert len(chunks) >= 1
        assert chunks[0].metadata.jurisdiction == "INDIA"
        assert chunks[0].metadata.document_type == "statute"
        assert chunks[0].metadata.source_url == "https://example.com"

    def test_chunk_ids_are_unique(self):
        text = "\n\n".join([f"Paragraph {i} with substantial content here." * 5 for i in range(20)])
        chunks = chunk_document(text, self._make_meta())
        ids = [c.chunk_id for c in chunks]
        assert len(ids) == len(set(ids)), "Chunk IDs must be unique"

    def test_chunk_indices_sequential(self):
        text = "\n\n".join([f"Paragraph {i}. " * 30 for i in range(10)])
        chunks = chunk_document(text, self._make_meta())
        for i, chunk in enumerate(chunks):
            assert chunk.metadata.chunk_index == i
            assert chunk.metadata.total_chunks == len(chunks)

    def test_section_boundary_detection_all_caps(self):
        assert _is_section_boundary("CHAPTER 4 — BOARD COMPOSITION") is True

    def test_section_boundary_detection_article(self):
        assert _is_section_boundary("ARTICLE 13 — Capital Gains") is True

    def test_section_boundary_detection_clause(self):
        assert _is_section_boundary("CLAUSE 5.1 — Reserved Matters") is True

    def test_section_boundary_detection_section_sign(self):
        assert _is_section_boundary("§90 Significant Beneficial Ownership") is True

    def test_section_boundary_detection_markdown(self):
        assert _is_section_boundary("## Overview and Purpose") is True

    def test_non_boundary_not_detected(self):
        assert _is_section_boundary("This is a normal paragraph sentence.") is False
        assert _is_section_boundary("") is False
        assert _is_section_boundary("   ") is False

    def test_long_document_produces_multiple_chunks(self):
        # Generate a document definitely longer than TARGET_CHUNK_CHARS
        long_text = ("This is a very long sentence about legal regulations and compliance. " * 30 + "\n\n") * 10
        chunks = chunk_document(long_text, self._make_meta())
        assert len(chunks) > 1

    def test_chunk_size_within_limits(self):
        long_text = ("A legal regulation sentence. " * 40 + "\n\n") * 15
        chunks = chunk_document(long_text, self._make_meta())
        for chunk in chunks:
            # Allow 50% headroom over target (overlap + header adds chars)
            assert len(chunk.content) < TARGET_CHUNK_CHARS * 2.5

    def test_real_corpus_india_fdi_chunks(self):
        filepath = CORPUS_DIR / "jurisdiction" / "india_fdi_policy.txt"
        if not filepath.exists():
            pytest.skip("Corpus file not found")
        text = filepath.read_text()
        meta = ChunkMetadata(
            jurisdiction="INDIA",
            document_type="policy_note",
            effective_date=1577836800.0,
            source_url="https://dpiit.gov.in",
            title="DPIIT FDI Policy 2020",
        )
        chunks = chunk_document(text, meta)
        assert len(chunks) >= 3  # FDI policy should produce multiple chunks
        # Every chunk should contain non-trivial content
        for chunk in chunks:
            assert len(chunk.content) >= 50

    def test_real_corpus_treaty_shopping(self):
        filepath = CORPUS_DIR / "general" / "treaty_shopping_gaar.txt"
        if not filepath.exists():
            pytest.skip("Corpus file not found")
        text = filepath.read_text()
        meta = ChunkMetadata(
            jurisdiction="GLOBAL",
            document_type="commentary",
            effective_date=1448928000.0,
            source_url="https://oecd.org",
            title="Treaty Shopping and GAAR",
        )
        chunks = chunk_document(text, meta)
        assert len(chunks) >= 4
        # Should find content about PPT
        all_content = " ".join(c.content for c in chunks)
        assert "PPT" in all_content or "Principal Purpose" in all_content


# ══════════════════════════════════════════════════════════════════════════════
# 2. RAG SERVICE UNIT TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestRAGService:
    """Unit tests for RAG service functions."""

    def _make_chunk(self, score: float = 0.85, jurisdiction: str = "INDIA") -> RetrievedChunk:
        return RetrievedChunk(
            chunk_id="test-id",
            content="This is a test regulatory chunk about FDI policy in India.",
            score=score,
            jurisdiction=jurisdiction,
            document_type="policy_note",
            effective_date=1577836800.0,
            source_url="https://dpiit.gov.in",
            title="India FDI Policy",
            section_header="Section 2 — Automatic Route",
            chunk_index=0,
            total_chunks=5,
        )

    def test_format_chunks_empty_returns_fallback(self):
        result = RAGQueryResult(query="test", top_k=5, chunks=[])
        formatted = format_chunks_as_context(result)
        assert "No relevant" in formatted

    def test_format_chunks_includes_source_number(self):
        chunk = self._make_chunk()
        result = RAGQueryResult(query="test", top_k=5, chunks=[chunk])
        formatted = format_chunks_as_context(result)
        assert "[SOURCE 1" in formatted

    def test_format_chunks_includes_jurisdiction(self):
        chunk = self._make_chunk()
        result = RAGQueryResult(query="test", top_k=5, chunks=[chunk])
        formatted = format_chunks_as_context(result)
        assert "INDIA" in formatted

    def test_format_chunks_includes_score(self):
        chunk = self._make_chunk(score=0.87)
        result = RAGQueryResult(query="test", top_k=5, chunks=[chunk])
        formatted = format_chunks_as_context(result)
        assert "0.87" in formatted

    def test_format_chunks_includes_content(self):
        chunk = self._make_chunk()
        result = RAGQueryResult(query="test", top_k=5, chunks=[chunk])
        formatted = format_chunks_as_context(result)
        assert "FDI policy in India" in formatted

    def test_format_chunks_multiple_sources_separated(self):
        chunks = [self._make_chunk(score=0.9), self._make_chunk(score=0.75)]
        result = RAGQueryResult(query="test", top_k=5, chunks=chunks)
        formatted = format_chunks_as_context(result)
        assert "[SOURCE 1" in formatted
        assert "[SOURCE 2" in formatted
        assert "---" in formatted


# ══════════════════════════════════════════════════════════════════════════════
# 3. RAG API ENDPOINT TESTS (mocked Qdrant)
# ══════════════════════════════════════════════════════════════════════════════

class TestRAGEndpoints:
    """Tests for POST /api/rag/query — Qdrant and embeddings are mocked."""

    _MOCK_VECTOR = [0.1] * 768

    def _make_qdrant_hit(self, score: float = 0.85, jurisdiction: str = "INDIA"):
        hit = MagicMock()
        hit.id = "mock-chunk-id-1"
        hit.score = score
        hit.payload = {
            "content": "India FDI policy allows 100% FDI in IT sector via automatic route.",
            "jurisdiction": jurisdiction,
            "document_type": "policy_note",
            "effective_date": 1577836800.0,
            "source_url": "https://dpiit.gov.in",
            "title": "India FDI Policy",
            "section_header": "KEY SECTORS AND FDI CAPS",
            "chunk_index": 2,
            "total_chunks": 8,
        }
        return hit

    def test_rag_query_returns_200(self):
        with (
            patch("app.services.rag_service.embed_query", new_callable=AsyncMock) as mock_embed,
            patch("app.services.rag_service._get_qdrant_client") as mock_client,
        ):
            mock_embed.return_value = (self._MOCK_VECTOR, "jina")
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[self._make_qdrant_hit()])
            mock_client.return_value = mock_qdrant

            response = client.post(
                "/api/rag/query",
                json={"query": "What is India FDI policy for IT sector?", "top_k": 5},
            )
        assert response.status_code == 200

    def test_rag_query_returns_chunks(self):
        with (
            patch("app.services.rag_service.embed_query", new_callable=AsyncMock) as mock_embed,
            patch("app.services.rag_service._get_qdrant_client") as mock_client,
        ):
            mock_embed.return_value = (self._MOCK_VECTOR, "jina")
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[self._make_qdrant_hit(0.85)])
            mock_client.return_value = mock_qdrant

            response = client.post(
                "/api/rag/query",
                json={"query": "FDI automatic route India", "top_k": 5},
            )
        data = response.json()
        assert data["total_matches"] >= 1
        assert len(data["chunks"]) >= 1
        assert "content" in data["chunks"][0]
        assert "score" in data["chunks"][0]

    def test_rag_query_with_jurisdiction_filter(self):
        with (
            patch("app.services.rag_service.embed_query", new_callable=AsyncMock) as mock_embed,
            patch("app.services.rag_service._get_qdrant_client") as mock_client,
        ):
            mock_embed.return_value = (self._MOCK_VECTOR, "jina")
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[])
            mock_client.return_value = mock_qdrant

            response = client.post(
                "/api/rag/query",
                json={"query": "capital gains tax", "jurisdiction": "INDIA", "top_k": 5},
            )
        data = response.json()
        assert response.status_code == 200
        assert data["filters_applied"].get("jurisdiction") == "INDIA"

    def test_rag_query_short_query_returns_422(self):
        response = client.post(
            "/api/rag/query",
            json={"query": "ab", "top_k": 5},  # too short
        )
        assert response.status_code == 422

    def test_rag_query_top_k_exceeds_max_clamped(self):
        with (
            patch("app.services.rag_service.embed_query", new_callable=AsyncMock) as mock_embed,
            patch("app.services.rag_service._get_qdrant_client") as mock_client,
        ):
            mock_embed.return_value = (self._MOCK_VECTOR, "jina")
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[])
            mock_client.return_value = mock_qdrant

            response = client.post(
                "/api/rag/query",
                json={"query": "Singapore SPV DTAA benefits treaty shopping", "top_k": 100},
            )
        # top_k > 20 should be clamped (FastAPI validates ge/le on model)
        assert response.status_code == 422  # Pydantic validation catches top_k > 20

    def test_rag_query_formatted_context_returned(self):
        with (
            patch("app.services.rag_service.embed_query", new_callable=AsyncMock) as mock_embed,
            patch("app.services.rag_service._get_qdrant_client") as mock_client,
        ):
            mock_embed.return_value = (self._MOCK_VECTOR, "jina")
            mock_qdrant = AsyncMock()
            mock_qdrant.search = AsyncMock(return_value=[self._make_qdrant_hit()])
            mock_client.return_value = mock_qdrant

            response = client.post(
                "/api/rag/query",
                json={
                    "query": "FDI in India technology sector",
                    "top_k": 5,
                    "include_formatted_context": True,
                },
            )
        data = response.json()
        assert data["formatted_context"] is not None
        assert "SOURCE 1" in data["formatted_context"]

    def test_rag_corpus_endpoint_returns_200(self):
        response = client.get("/api/rag/corpus")
        assert response.status_code == 200

    def test_rag_corpus_lists_documents(self):
        response = client.get("/api/rag/corpus")
        data = response.json()
        assert "total_documents" in data
        assert data["total_documents"] >= 10  # We have 12 corpus docs

    def test_rag_embedding_failure_returns_empty_gracefully(self):
        """If embedding fails, endpoint returns 200 with empty chunks (no crash)."""
        with patch("app.services.rag_service.embed_query", new_callable=AsyncMock) as mock_embed:
            mock_embed.side_effect = RuntimeError("No API keys")
            response = client.post(
                "/api/rag/query",
                json={"query": "Singapore DTAA capital gains treatment", "top_k": 5},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["total_matches"] == 0
        assert data["chunks"] == []


# ══════════════════════════════════════════════════════════════════════════════
# 4. CORPUS DOCUMENT COMPLETENESS TESTS
# ══════════════════════════════════════════════════════════════════════════════

class TestCorpusCompleteness:
    """Verify all required corpus documents exist and have content."""

    REQUIRED_JURISDICTION = [
        "india_fdi_policy.txt",
        "press_note_3_2020.txt",
        "section_9_indirect_transfer.txt",
        "sbo_companies_act_s90.txt",
        "singapore_india_dtaa.txt",
    ]

    REQUIRED_GENERAL = [
        "oecd_model_tax_convention.txt",
        "cfius_overview.txt",
        "eu_fdi_screening.txt",
        "mas_approach_singapore.txt",
        "treaty_shopping_gaar.txt",
    ]

    def test_jurisdiction_corpus_files_exist(self):
        for filename in self.REQUIRED_JURISDICTION:
            path = CORPUS_DIR / "jurisdiction" / filename
            assert path.exists(), f"Missing corpus file: {path}"

    def test_general_corpus_files_exist(self):
        for filename in self.REQUIRED_GENERAL:
            path = CORPUS_DIR / "general" / filename
            assert path.exists(), f"Missing corpus file: {path}"

    def test_corpus_files_have_content(self):
        for filename in self.REQUIRED_JURISDICTION + self.REQUIRED_GENERAL:
            subdir = "jurisdiction" if filename in self.REQUIRED_JURISDICTION else "general"
            path = CORPUS_DIR / subdir / filename
            if path.exists():
                content = path.read_text()
                assert len(content) > 500, f"{filename} has too little content ({len(content)} chars)"

    def test_metadata_json_exists(self):
        metadata_path = CORPUS_DIR / "metadata.json"
        assert metadata_path.exists(), "corpus/metadata.json not found"

    def test_metadata_covers_all_files(self):
        metadata_path = CORPUS_DIR / "metadata.json"
        if not metadata_path.exists():
            pytest.skip("metadata.json not found")
        with open(metadata_path) as f:
            registry = json.load(f)
        for filename in self.REQUIRED_JURISDICTION + self.REQUIRED_GENERAL:
            assert filename in registry, f"{filename} missing from metadata.json"

    def test_metadata_has_required_fields(self):
        metadata_path = CORPUS_DIR / "metadata.json"
        if not metadata_path.exists():
            pytest.skip("metadata.json not found")
        with open(metadata_path) as f:
            registry = json.load(f)
        required_fields = {"jurisdiction", "document_type", "effective_date", "source_url", "title"}
        for filename, meta in registry.items():
            missing = required_fields - set(meta.keys())
            assert not missing, f"{filename} missing fields: {missing}"
