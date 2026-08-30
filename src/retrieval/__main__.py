"""CLI for the retrieval backend.

Usage:
  python -m src.retrieval "What is the expense ratio of HDFC Large Cap?"
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.retrieval.retrieve import Retriever


def _print_answer(answer) -> None:
    print(f"[action] {answer.action}")
    if answer.url:
        print(f"[source] {answer.url}")
    if answer.fund_name:
        print(f"[fund]   {answer.fund_name}")
    if answer.ingest_ts:
        print(f"[updated] {answer.ingest_ts}")
    print()
    print(answer.answer)


def main() -> int:
    query = " ".join(sys.argv[1:]).strip()
    if not query:
        print("Usage: python -m src.retrieval \"your question\"", file=sys.stderr)
        return 2
    r = Retriever()
    answer = r.answer(query)
    _print_answer(answer)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
