"""Write Phase 1 snapshots to data/raw. One JSON file per successful page."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.loading.corpus import CorpusPage

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"

DOCUMENT_FIELDS = ("source_url", "fund_name", "category", "text", "ingest_ts")


def raw_path_for(page: CorpusPage) -> Path:
    slug = page["source_url"].rstrip("/").rsplit("/", 1)[-1]
    return RAW_DIR / f"{slug}.json"


def write_snapshot(document: dict[str, Any]) -> Path:
    missing = [field for field in DOCUMENT_FIELDS if field not in document]
    if missing:
        raise ValueError(f"snapshot missing fields: {missing}")
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = raw_path_for(
        {
            "fund_name": document["fund_name"],
            "category": document["category"],
            "source_url": document["source_url"],
        }
    )
    path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path
