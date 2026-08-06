"""
Sententia.ai — Corpus Ingestion Script

Usage:
    conda run -n iitr python scripts/ingest_corpus.py

What it does:
  1. Reads all .txt files under backend/corpus/ (jurisdiction/ and general/)
  2. Looks up metadata for each file from corpus/metadata.json
  3. Chunks each document using the layout-aware legal chunker
  4. Embeds chunks using Jina v3 (or Google fallback)
  5. Upserts into Qdrant collection 'regulatory_corpus'

Run this script after:
  - Initial setup (first-time population)
  - Adding new corpus documents
  - Changing chunking parameters (re-ingests all docs)

Environment:
  Requires JINA_API_KEY (or GOOGLE_API_KEY) and QDRANT_URL in .env

Estimated time: ~2-5 minutes for the full corpus (~12 documents, ~150 chunks)
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import uuid
from pathlib import Path

# ── Add backend root to sys.path so app.* imports work ────────────────────────
BACKEND_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_ROOT))

from dotenv import load_dotenv
load_dotenv(BACKEND_ROOT / ".env")

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    VectorParams,
    Distance,
    PointStruct,
    PayloadSchemaType,
)

from app.config import get_settings
from app.services.chunker import chunk_document, ChunkMetadata, DocumentChunk
from app.services.embedding_service import embed_texts, VECTOR_DIM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ingest_corpus")

# ── Constants ──────────────────────────────────────────────────────────────────
COLLECTION_NAME = "regulatory_corpus"
CORPUS_DIR      = BACKEND_ROOT / "corpus"
METADATA_FILE   = CORPUS_DIR / "metadata.json"
BATCH_SIZE      = 16    # chunks per Qdrant upsert batch


# ── Qdrant setup ───────────────────────────────────────────────────────────────

def get_qdrant_client(settings) -> QdrantClient:
    if settings.qdrant_url:
        return QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
            timeout=30,
        )
    else:
        logger.warning("QDRANT_URL not set — using local in-memory Qdrant (data lost on exit)")
        return QdrantClient(":memory:")


def ensure_collection(client: QdrantClient) -> None:
    """Create the collection if it doesn't exist, or verify dimensions match."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        logger.info(f"Creating Qdrant collection '{COLLECTION_NAME}' (dim={VECTOR_DIM}, cosine)")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
        # Create payload indexes for filtered search
        for field, schema_type in [
            ("jurisdiction",   PayloadSchemaType.KEYWORD),
            ("document_type",  PayloadSchemaType.KEYWORD),
            ("effective_date", PayloadSchemaType.FLOAT),
            ("title",          PayloadSchemaType.TEXT),
        ]:
            client.create_payload_index(
                collection_name=COLLECTION_NAME,
                field_name=field,
                field_schema=schema_type,
            )
        logger.info("Collection and payload indexes created.")
    else:
        logger.info(f"Collection '{COLLECTION_NAME}' already exists.")


# ── Document loading ───────────────────────────────────────────────────────────

def load_metadata() -> dict:
    """Load the metadata registry from corpus/metadata.json."""
    if not METADATA_FILE.exists():
        logger.error(f"metadata.json not found at {METADATA_FILE}")
        return {}
    with open(METADATA_FILE) as f:
        return json.load(f)


def find_corpus_files() -> list[tuple[Path, dict]]:
    """Find all .txt files under corpus/ and pair with metadata."""
    registry = load_metadata()
    files: list[tuple[Path, dict]] = []

    for txt_file in sorted(CORPUS_DIR.rglob("*.txt")):
        filename = txt_file.name
        if filename in registry:
            files.append((txt_file, registry[filename]))
        else:
            logger.warning(f"No metadata found for '{filename}' — skipping. Add to metadata.json")

    logger.info(f"Found {len(files)} corpus files to ingest")
    return files


# ── Chunking ───────────────────────────────────────────────────────────────────

def chunk_file(filepath: Path, meta: dict) -> list[DocumentChunk]:
    """Read a corpus file and produce chunks with metadata."""
    text = filepath.read_text(encoding="utf-8")
    chunk_meta = ChunkMetadata(
        jurisdiction=meta["jurisdiction"],
        document_type=meta["document_type"],
        effective_date=float(meta["effective_date"]),
        source_url=meta["source_url"],
        title=meta["title"],
    )
    chunks = chunk_document(text, chunk_meta)
    logger.info(f"  {filepath.name}: {len(text):,} chars → {len(chunks)} chunks")
    return chunks


# ── Upsert to Qdrant ───────────────────────────────────────────────────────────

async def embed_and_upsert(
    client: QdrantClient,
    chunks: list[DocumentChunk],
    provider_log: list[str],
) -> int:
    """Embed all chunks and upsert to Qdrant in batches. Returns count upserted."""
    if not chunks:
        return 0

    texts = [c.content for c in chunks]

    # ── Embed ─────────────────────────────────────────────────────────────────
    vectors, provider = await embed_texts(texts, task="retrieval.passage")
    provider_log.append(provider)
    logger.info(f"  Embedded {len(texts)} chunks via {provider}")

    # ── Upsert in batches ─────────────────────────────────────────────────────
    total_upserted = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch_chunks = chunks[i : i + BATCH_SIZE]
        batch_vectors = vectors[i : i + BATCH_SIZE]

        points = [
            PointStruct(
                id=chunk.chunk_id,
                vector=vector,
                payload={
                    "content":        chunk.content,
                    "jurisdiction":   chunk.metadata.jurisdiction,
                    "document_type":  chunk.metadata.document_type,
                    "effective_date": chunk.metadata.effective_date,
                    "source_url":     chunk.metadata.source_url,
                    "title":          chunk.metadata.title,
                    "section_header": chunk.metadata.section_header,
                    "chunk_index":    chunk.metadata.chunk_index,
                    "total_chunks":   chunk.metadata.total_chunks,
                    "char_offset":    chunk.char_offset,
                    "char_length":    chunk.char_length,
                },
            )
            for chunk, vector in zip(batch_chunks, batch_vectors)
        ]

        client.upsert(collection_name=COLLECTION_NAME, points=points)
        total_upserted += len(points)
        logger.debug(f"  Upserted batch {i//BATCH_SIZE + 1}: {len(points)} points")

    return total_upserted


# ── Main ──────────────────────────────────────────────────────────────────────

async def main() -> None:
    settings = get_settings()

    if not settings.jina_api_key and not settings.google_api_key:
        logger.error(
            "No embedding API key found. Set JINA_API_KEY or GOOGLE_API_KEY in .env"
        )
        sys.exit(1)

    client = get_qdrant_client(settings)
    ensure_collection(client)

    corpus_files = find_corpus_files()
    if not corpus_files:
        logger.error("No corpus files found. Check corpus/ directory and metadata.json")
        sys.exit(1)

    total_chunks  = 0
    total_upserted = 0
    provider_log: list[str] = []

    for filepath, meta in corpus_files:
        logger.info(f"\n📄 Processing: {filepath.name}")
        try:
            chunks = chunk_file(filepath, meta)
            upserted = await embed_and_upsert(client, chunks, provider_log)
            total_chunks += len(chunks)
            total_upserted += upserted
        except Exception as e:
            logger.error(f"  FAILED: {filepath.name} — {e}")
            continue

    # ── Summary ───────────────────────────────────────────────────────────────
    providers_used = set(provider_log)
    collection_info = client.get_collection(COLLECTION_NAME)
    point_count = collection_info.points_count

    logger.info("\n" + "═" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info(f"  Documents processed : {len(corpus_files)}")
    logger.info(f"  Chunks produced     : {total_chunks}")
    logger.info(f"  Points upserted     : {total_upserted}")
    logger.info(f"  Embedding providers : {', '.join(providers_used)}")
    logger.info(f"  Qdrant total points : {point_count}")
    logger.info("═" * 60)


if __name__ == "__main__":
    asyncio.run(main())
