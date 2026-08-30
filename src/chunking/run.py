"""Phase 2 — Chunking: raw snapshots (data/raw) -> section chunks (data/chunks)."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.chunking.chunks import CHUNKS_DIR, chunk_document, load_documents


def chunks_path_for(source_url: str) -> Path:
    slug = source_url.rstrip("/").rsplit("/", 1)[-1]
    return CHUNKS_DIR / f"{slug}.chunks.json"


def chunk_all() -> tuple[int, list[dict[str, str]]]:
    """Chunk every loaded document; write one JSON list per page."""
    docs = load_documents()
    all_chunks: list[dict[str, str]] = []
    CHUNKS_DIR.mkdir(parents=True, exist_ok=True)

    for doc in docs:
        chunks = chunk_document(doc)
        if not chunks:
            print(
                f"SKIP {doc.get('source_url')} (no chunks produced)",
                file=sys.stderr,
            )
            continue
        path = chunks_path_for(doc["source_url"])
        path.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        all_chunks.extend(chunks)
        print(f"OK  {doc.get('fund_name')} ({len(chunks)} chunks)\n    {path}")

    return len(all_chunks), all_chunks


def main() -> int:
    total, chunks = chunk_all()
    print(f"\nWrote {total} chunks across {len(chunks)} pages to data/chunks/")
    return 0 if total else 1


if __name__ == "__main__":
    raise SystemExit(main())
