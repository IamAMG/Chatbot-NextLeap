"""Phase 3 — Embedding: chunk text -> MiniLM vectors (data/embeddings).

Reads every chunk from ``data/chunks/*.chunks.json`` and writes a sidecar JSON
per page to ``data/embeddings/`` aligned by ``chunk_id``. Query-time embeds are
produced on demand by :func:`src.embedding.encoder.MiniLmEncoder.encode_query`
and are never persisted (architecture.md Phase 3).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.embedding.encoder import MiniLmEncoder
from src.chunking.run import chunks_path_for
from src.loading.corpus import CORPUS

EMBEDDINGS_DIR = _REPO_ROOT / "data" / "embeddings"


def embeddings_path_for(source_url: str) -> Path:
    slug = source_url.rstrip("/").rsplit("/", 1)[-1]
    return EMBEDDINGS_DIR / f"{slug}.embeddings.json"


def load_chunks_per_page() -> list[tuple[str, list[dict[str, str]]]]:
    """Return (source_url, chunks) pairs for every page in the corpus."""
    result: list[tuple[str, list[dict[str, str]]]] = []
    for page in CORPUS:
        path = chunks_path_for(page["source_url"])
        if not path.exists():
            print(f"SKIP {page['source_url']}: no chunks file", file=sys.stderr)
            continue
        chunks = json.loads(path.read_text(encoding="utf-8"))
        result.append((page["source_url"], chunks))
    return result


def embed_all(encoder: MiniLmEncoder) -> tuple[int, int]:
    """Embed every chunk in the corpus; write one sidecar JSON per page."""
    EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)
    total_chunks = 0
    total_pages = 0

    for source_url, chunks in load_chunks_per_page():
        if not chunks:
            continue
        texts = [chunk["text"] for chunk in chunks]
        chunk_ids = [chunk["chunk_id"] for chunk in chunks]
        vectors = encoder.encode_texts(texts)

        records = [
            {"chunk_id": chunk_id, "vector": vector}
            for chunk_id, vector in zip(chunk_ids, vectors)
        ]
        path = embeddings_path_for(source_url)
        path.write_text(
            json.dumps(records, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        total_chunks += len(records)
        total_pages += 1
        print(f"OK  {path.name} ({len(records)} vectors)")

    return total_chunks, total_pages


def main() -> int:
    encoder = MiniLmEncoder()
    total_chunks, total_pages = embed_all(encoder)
    print(f"\nEmbedded {total_chunks} chunks across {total_pages} pages -> data/embeddings/")
    return 0 if total_chunks else 1


if __name__ == "__main__":
    raise SystemExit(main())
