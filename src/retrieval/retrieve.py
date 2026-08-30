"""Backend retrieval (architecture.md Phase 5): guard -> kNN -> generate.

Returns a structured :class:`RetrievalAnswer` for every input so callers (CLI,
UI, tests) can render uniformly and never duplicate guardrail logic.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.embedding.encoder import MiniLmEncoder
from src.retrieval import guardrails, llm
from src.retrieval.guardrails import GuardResult, check
from src.store import store


# Cosine distance threshold above which we treat retrieval as empty/weak (F4).
_WEAK_THRESHOLD = 0.90


@dataclass
class RetrievalAnswer:
    action: str  # "answered" | "refused" | "weak" | "error"
    answer: str
    url: Optional[str] = None          # exactly one citation (allowlisted)
    fund_name: Optional[str] = None
    ingest_ts: Optional[str] = None
    category: str = ""
    reason: str = ""
    hits: list = field(default_factory=list)


def _make_hits(result) -> list:
    docs = result.get("documents") or [[]]
    mds = result.get("metadatas") or [[]]
    dists = result.get("distances") or [[]]
    hits = []
    for i in range(len(docs[0])):
        hits.append(
            (
                dists[0][i],
                mds[0][i].get("source_url", ""),
                docs[0][i],
            )
        )
    return hits


def _refuse(gr: GuardResult) -> RetrievalAnswer:
    return RetrievalAnswer(
        action="refused",
        answer=gr.reason,
        url=gr.url,
        fund_name=gr.fund_name,
        category=gr.category,
        reason=gr.reason,
    )


def _weak_answer(url: Optional[str]) -> RetrievalAnswer:
    reason = (
        "I couldn't find enough on these pages to answer that reliably. "
        "Try asking about expense ratio, SIP minimum, exit load, lock-in, "
        "riskometer, or benchmark for one of the five HDFC funds."
    )
    return RetrievalAnswer(
        action="weak",
        answer=reason,
        url=url or guardrails._general_url(),
        category="weak",
        reason=reason,
    )


def _error(reason: str) -> RetrievalAnswer:
    return RetrievalAnswer(action="error", answer=reason, reason=reason, category="error")


class Retriever:
    """Reusable retrieval pipeline with a single shared MiniLM encoder."""

    def __init__(self, encoder: Optional[MiniLmEncoder] = None, top_k: int = 5):
        self.encoder = encoder or MiniLmEncoder()
        self.top_k = top_k

    def answer(self, query: str) -> RetrievalAnswer:
        # 5.1 Pre-retrieve guardrails (no vector access on refusal).
        gr: GuardResult = check(query)
        if gr.action != "allow":
            return _refuse(gr)

        # 5.2 Retrieve: embed question with the same MiniLM, then k-NN.
        emb = self.encoder.encode_query(query)
        result = store.query(emb, k=self.top_k)
        hits = _make_hits(result)

        # Empty / weak retrieval (F4): do not invent; cite closest allowed page.
        if not hits or hits[0][0] > _WEAK_THRESHOLD:
            return _weak_answer(hits[0][1] if hits else gr.url)

        # Top hit supplies the single citation + metadata (F5).
        _dist, top_url, _text = hits[0]
        top_fund, ingest_ts = _metadata_for_url(top_url)

        context = _format_context(hits)
        try:
            answer = llm.generate_answer(query, context, top_url, ingest_ts or "")
        except llm.MissingApiKeyError as exc:
            return _error(str(exc))
        # Keep other LLM errors visible to the caller.

        return RetrievalAnswer(
            action="answered",
            answer=answer,
            url=top_url,
            fund_name=top_fund,
            ingest_ts=ingest_ts,
            hits=hits,
        )


def _metadata_for_url(url: str):
    urls, mds, _docs = store.fetch_all()
    for m in mds:
        if m.get("source_url") == url:
            return m.get("fund_name"), m.get("ingest_ts")
    return None, None


def _format_context(hits) -> str:
    parts = []
    seen = set()
    for _dist, url, text in hits:
        key = url.rstrip("/")
        if key in seen:
            continue
        seen.add(key)
        parts.append(text.strip())
    return "\n\n---\n\n".join(parts)


def default_retriever() -> Retriever:
    return Retriever()
