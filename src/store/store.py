"""Phase 4 — Vector store: ChromaDB read/write (data/vectordb).

One collection holds the current chunk set. Each record stores:
  * embedding  (MiniLM vector, supplied at ingest; Chroma does no embedding)
  * document   (chunk text)
  * metadata   (source_url, fund_name, ingest_ts)

Only chunks from the five allowlisted URLs are ever indexed. No user chat, no
PII, no factsheet bodies, no blogs. Re-ingest rebuilds the collection so
citations and timestamps stay consistent with the new snapshot.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import chromadb
from chromadb.api.types import QueryResult

VECTORDB_DIR = _REPO_ROOT / "data" / "vectordb"
COLLECTION_NAME = "hdfc_funds"


def get_client() -> Any:
    VECTORDB_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(VECTORDB_DIR))


def _coll(client: Any):
    # embedding_function=None: we manage vectors ourselves with the fixed MiniLM.
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=None,
        metadata={"hnsw:space": "cosine"},
    )


def rebuild_collection(
    chunks: Sequence[dict[str, str]],
    vectors: Sequence[Sequence[float]],
) -> int:
    """Replace the collection with the given chunks and aligned vectors."""
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # collection may not exist yet
    coll = _coll(client)

    ids = [c["chunk_id"] for c in chunks]
    metadatas = [
        {
            "source_url": c["source_url"],
            "fund_name": c["fund_name"],
            "ingest_ts": c["ingest_ts"],
        }
        for c in chunks
    ]
    coll.add(
        ids=ids,
        embeddings=[list(v) for v in vectors],
        documents=[c["text"] for c in chunks],
        metadatas=metadatas,
    )
    return coll.count()


def count() -> int:
    return _coll(get_client()).count()


def query(
    query_embedding: Sequence[float],
    k: int = 5,
    include: Sequence[str] = ("documents", "metadatas", "distances"),
) -> QueryResult:
    """k-NN search; returns Chroma QueryResult with the requested fields."""
    coll = _coll(get_client())
    return coll.query(
        query_embeddings=[list(query_embedding)],
        n_results=k,
        include=list(include),
    )


def fetch_all() -> tuple[list[str], list[dict[str, Any]], list[dict[str, str]]]:
    """Return (ids, metadatas, documents) for the whole collection (for tests)."""
    coll = _coll(get_client())
    n = coll.count()
    if n == 0:
        return [], [], []
    result = coll.get(include=["documents", "metadatas"])
    return (
        result["ids"],
        result["metadatas"],
        result["documents"],
    )
