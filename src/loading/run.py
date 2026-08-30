"""Phase 1 — Data loading: allowlisted Groww pages → data/raw snapshots."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.loading.corpus import CORPUS, CorpusPage
from src.loading.extract import snapshot_text
from src.loading.fetch import FetchError, fetch_html
from src.loading.persist import write_snapshot


def ingest_page(page: CorpusPage, ingest_ts: str) -> dict[str, Any]:
    html = fetch_html(page["source_url"])
    text = snapshot_text(html, fund_name=page["fund_name"])
    if not text:
        raise FetchError(f"empty extracted text for {page['source_url']}")
    return {
        "source_url": page["source_url"],
        "fund_name": page["fund_name"],
        "category": page["category"],
        "text": text,
        "ingest_ts": ingest_ts,
    }


def run_ingest() -> tuple[list[dict[str, Any]], list[str]]:
    ingest_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    saved: list[dict[str, Any]] = []
    failures: list[str] = []

    for page in CORPUS:
        url = page["source_url"]
        try:
            document = ingest_page(page, ingest_ts)
            path = write_snapshot(document)
            saved.append(document)
            print(f"OK  {page['fund_name']}\n    {path}")
        except FetchError as exc:
            failures.append(f"{url}: {exc}")
            print(f"FAIL {page['fund_name']}\n     {exc}", file=sys.stderr)

    return saved, failures


def main() -> int:
    saved, failures = run_ingest()
    print(f"\nSaved {len(saved)} of {len(CORPUS)} pages to data/raw/")
    if failures:
        print("Failed URLs were not written and were not replaced:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
