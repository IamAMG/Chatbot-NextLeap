"""Phase 4 — Vector store build: chunks + MiniLM vectors -> ChromaDB data/vectordb."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.embedding.run import embeddings_path_for, load_chunks_per_page
from src.store import store


def gather_records() -> tuple[list[dict[str, str]], list[list[float]]]:
    """Collect all chunks and their aligned vectors across the corpus."""
    chunks: list[dict[str, str]] = []
    vectors: list[list[float]] = []

    for source_url, page_chunks in load_chunks_per_page():
        emb_path = embeddings_path_for(source_url)
        if not emb_path.exists():
            raise FileNotFoundError(f"missing embeddings: {emb_path}")
        emb_records = {
            r["chunk_id"]: r["vector"] for r in json.loads(emb_path.read_text(encoding="utf-8"))
        }
        for chunk in page_chunks:
            vec = emb_records.get(chunk["chunk_id"])
            if vec is None:
                raise ValueError(f"no vector for chunk {chunk['chunk_id']}")
            chunks.append(chunk)
            vectors.append(vec)

    return chunks, vectors


def main() -> int:
    chunks, vectors = gather_records()
    count = store.rebuild_collection(chunks, vectors)
    print(f"Rebuilt ChromaDB collection '{store.COLLECTION_NAME}' with {count} records")
    return 0 if count else 1


if __name__ == "__main__":
    raise SystemExit(main())
