"""Phase 2 — Chunking: single-page raw snapshots -> section-sized chunks.

Strategy (architecture.md Phase 2):
  * Never merge text across different source_url values. Each document is
    processed independently.
  * The [Page facts ...] block is kept whole as the primary facts chunk; it
    holds the FAQ facts (expense ratio, minimum SIP, exit load, lock-in,
    riskometer, benchmark).
  * The visible body is reduced to four readable prose sections (Understand
    terms, Exit load/stamp duty/tax, About, Fund house). Noise that carries no
    grounded FAQ facts -- return calculator, historic returns, holdings,
    "compare similar funds", fund-manager cross-scheme lists, site chrome --
    is discarded rather than indexed.
  * No commentary or computed returns are added into chunks.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.loading.persist import RAW_DIR

CHUNKS_DIR = _REPO_ROOT / "data" / "chunks"

# Facts block header produced by src.loading.extract.
_FACTS_HEADER = "[Page facts from this Groww fund page]"

# The four prose sections worth indexing, in display order. Each key maps to
# the heading lines that open that section.
_SECTION_HEADINGS: dict[str, tuple[str, ...]] = {
    "understand-terms": ("Understand terms",),
    "exit-load-stamp-duty-tax": ("Exit load, stamp duty and tax",),
    "about": ("About",),
    "fund-house": ("Fund house",),
}

_ALL_HEADINGS = frozenset(
    heading for headings in _SECTION_HEADINGS.values() for heading in headings
)

# Body content we never index and that terminates a running prose section:
# off-scope, computed returns/rankings, fund-manager cross-scheme lists,
# holdings, site chrome. (Defines such as "Expense ratio"/"Tax"/"Exit load"/
# "Stamp duty" are useful subheadings inside the Understand-terms and tax
# sections, so they are intentionally NOT on this list.)
_DROP_ANYWHERE = (
    "Return calculator",
    "Historic returns",
    "Holdings (",
    "Compare similar funds",
    "Check past data",
    "Fund management",
    "Also manages these schemes",
    "Other HDFC funds",
    "Home",
    "See All",
    "Returns and rankings",
    "Fund returns",
    "Category average",
    "Minimum investments",
    "Annualised returns",
    "Absolute returns",
    "Exit Load",
)


def split_facts_block(document: dict[str, Any]) -> str:
    """Return the facts block text, or \"\" if this page has no facts block."""
    text = document.get("text", "")
    if not text.startswith(_FACTS_HEADER):
        return ""
    end = text.find("\n\n")
    return text[:end].strip() if end != -1 else text.strip()


def split_body_sections(document: dict[str, Any]) -> list[str]:
    """Extract the four prose sections in source order as whole chunks.

    A state machine walks the visible body once. Only text belonging to one of
    the four prose sections is kept. Everything else (return calculator,
    historic returns, holdings, compare-funds lists, site chrome) is dropped.
    """
    text = document.get("text", "")
    facts = split_facts_block(document)
    if facts:
        start = facts + "\n\n"
        body = text[len(start):] if text.startswith(start) else text
    else:
        body = text

    sections: dict[str, list[str]] = {name: [] for name in _SECTION_HEADINGS}
    order: list[str] = []
    current: str | None = None

    for raw_line in body.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        heading = _heading(stripped)
        if heading is not None:
            if heading not in order:
                order.append(heading)
            current = heading
            sections[heading].append(stripped)
            continue

        # Outside the four prose sections -> discarded.
        if current is None:
            continue

        # A dropped block (returns/rankings/holdings/site chrome) interrupts
        # the running section; stop capturing here.
        if any(stripped.startswith(marker) for marker in _DROP_ANYWHERE):
            current = None
            continue

        sections[current].append(stripped)

    out: list[str] = []
    for name in order:
        block = "\n".join(sections[name]).strip()
        if block:
            out.append(block)
    return out


def _heading(stripped: str) -> str | None:
    """Return the section key if `stripped` opens one of the four sections."""
    for name, headings in _SECTION_HEADINGS.items():
        for heading in headings:
            if stripped.startswith(heading):
                return name
    return None


def chunk_document(document: dict[str, Any]) -> list[dict[str, str]]:
    """Chunk one Phase 1 document into a list of chunk records."""
    source_url = document["source_url"]
    fund_name = document["fund_name"]
    ingest_ts = document["ingest_ts"]
    base = _slug(source_url)

    chunks: list[dict[str, str]] = []
    facts = split_facts_block(document)
    if facts:
        chunks.append(
            {
                "chunk_id": f"{base}:facts",
                "text": facts,
                "source_url": source_url,
                "fund_name": fund_name,
                "ingest_ts": ingest_ts,
            }
        )

    for idx, text in enumerate(split_body_sections(document), start=1):
        chunks.append(
            {
                "chunk_id": f"{base}:s{idx}",
                "text": text,
                "source_url": source_url,
                "fund_name": fund_name,
                "ingest_ts": ingest_ts,
            }
        )
    return chunks


def _slug(source_url: str) -> str:
    return source_url.rstrip("/").rsplit("/", 1)[-1]


def load_documents() -> list[dict[str, Any]]:
    """Read all Phase 1 snapshots from data/raw as document dicts."""
    import json

    docs: list[dict[str, Any]] = []
    if not RAW_DIR.exists():
        return docs
    for path in sorted(RAW_DIR.glob("*.json")):
        docs.append(json.loads(path.read_text(encoding="utf-8")))
    return docs
