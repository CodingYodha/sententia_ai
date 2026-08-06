"""
Sententia.ai — Qdrant collection setup script.

Run ONCE after creating your Qdrant Cloud cluster to provision the
legal corpus collection with the correct vector config and indexed payload fields.

Usage:
    cd backend
    python scripts/setup_qdrant.py

Requires:
    - QDRANT_URL and QDRANT_API_KEY set in backend/.env (or environment)
"""

import sys
import os

# Allow running from /backend root without installing the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PayloadSchemaType,
)
from dotenv import load_dotenv

load_dotenv()

# ── Config ─────────────────────────────────────────────────────────────────────
COLLECTION_NAME = "regulatory_corpus"   # must match ingest_corpus.py and rag_service.py

# Vector dimension standardized at 768 for both providers:
#   - Jina embeddings v3: uses Matryoshka truncation (dimensions=768 param)
#   - Google text-embedding-004: native 768-dim output
# Tradeoff: 768 vs 1024 loses ~3-5% retrieval quality but enables seamless
# provider fallback without dimension mismatch errors.
VECTOR_SIZE = 768
DISTANCE = Distance.COSINE

# ── Connect ────────────────────────────────────────────────────────────────────
qdrant_url = os.getenv("QDRANT_URL", "")
qdrant_api_key = os.getenv("QDRANT_API_KEY", "")

if not qdrant_url:
    print("⚠️  QDRANT_URL not set — using in-memory Qdrant (for local testing only)")
    client = QdrantClient(":memory:")
else:
    print(f"🔗 Connecting to Qdrant at {qdrant_url} ...")
    client = QdrantClient(url=qdrant_url, api_key=qdrant_api_key)


def create_collection():
    """Create the legal corpus collection if it does not already exist."""
    existing = [c.name for c in client.get_collections().collections]

    if COLLECTION_NAME in existing:
        print(f"ℹ️  Collection '{COLLECTION_NAME}' already exists — skipping creation.")
        return

    print(f"📦 Creating collection '{COLLECTION_NAME}' ...")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(
            size=VECTOR_SIZE,
            distance=DISTANCE,
        ),
    )
    print(f"✅ Collection '{COLLECTION_NAME}' created successfully.")


def create_payload_indexes():
    """
    Create indexes on payload fields used for filtered retrieval.

    Indexed fields:
        - jurisdiction      (keyword) — e.g. "INDIA", "SINGAPORE"
        - document_type     (keyword) — e.g. "statute", "treaty", "regulation", "commentary"
        - effective_date    (datetime) — ISO 8601 date string
        - source_url        (keyword) — document source URL (for dedup/lineage)
    """
    indexes = {
        "jurisdiction": PayloadSchemaType.KEYWORD,
        "document_type": PayloadSchemaType.KEYWORD,
        "source_url": PayloadSchemaType.KEYWORD,
        # Note: Qdrant uses FLOAT for datetime range queries on Unix timestamps;
        # store effective_date as a Unix timestamp (float) in the payload.
        "effective_date": PayloadSchemaType.FLOAT,
    }

    for field, schema_type in indexes.items():
        print(f"  🔑 Creating payload index: {field} ({schema_type.value}) ...")
        client.create_payload_index(
            collection_name=COLLECTION_NAME,
            field_name=field,
            field_schema=schema_type,
        )

    print("✅ All payload indexes created.")


def verify():
    """Print collection info to confirm setup."""
    info = client.get_collection(COLLECTION_NAME)
    print("\n── Collection Info ─────────────────────────────────────")
    print(f"  Name:         {COLLECTION_NAME}")
    print(f"  Vector size:  {info.config.params.vectors.size}")
    print(f"  Distance:     {info.config.params.vectors.distance}")
    print(f"  Points count: {info.points_count}")
    print("────────────────────────────────────────────────────────\n")


if __name__ == "__main__":
    create_collection()
    create_payload_indexes()
    verify()
    print("🎉 Qdrant setup complete. You're ready to ingest documents.")
