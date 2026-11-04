"""LLM generation via the Mistral API (architecture.md Phase 5.3).

Contract enforced in the system prompt:
  * facts from retrieved context only
  * no advice
  * no performance/return math
  * no PII echo
  * <= 3 sentences
  * one citation URL
  * a "Last updated from sources: <ingest_ts>" line

A deterministic zero-token fallback is used when Mistral is unavailable or
rate-limited so the prototype stays functional end-to-end.
"""

from __future__ import annotations

import json
import re
from typing import Optional

import requests

from src.config import MissingApiKeyError, mistral_api_key, mistral_model

_API_URL = "https://api.mistral.ai/v1/chat/completions"
_TIMEOUT_SEC = 60

SYSTEM_PROMPT = (
    "You are a facts-only assistant for five HDFC Direct Growth mutual funds "
    "using ONLY the provided context. Rules:\n"
    "- Answer only from the retrieved context. If the context lacks the fact, say "
    "you don't have that on the page \u2014 do not guess from prior knowledge.\n"
    "- Keep the answer to at most 3 sentences.\n"
    "- No investment advice, no buy/sell recommendations.\n"
    "- No computed or compared returns; do not invent returns.\n"
    "- Never echo or print PAN, Aadhaar, account, OTP, email, or phone numbers.\n"
)


def _headers() -> dict:
    key = mistral_api_key()
    if not key:
        raise MissingApiKeyError(
            "MISTRAL_API_KEY is not set in .env. Add it, then retry."
        )
    return {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}


def _build_user_message(query: str, context: str, source_url: str, ingest_ts: str) -> str:
    return (
        f"Context from sources:\n{context}\n\n"
        f"Citing exactly one source URL: {source_url}\n"
        f"Last updated from sources: {ingest_ts}\n\n"
        f"Question: {query}\n\n"
        "Answer (at most 3 sentences) using only the context above. End with "
        f"the line: Last updated from sources: {ingest_ts}"
    )


def _deterministic_fallback(query: str, context: str, source_url: str, ingest_ts: str) -> str:
    """Build a facts-only answer from context without calling Mistral.

    Picks the sentence(s) most relevant to the query keywords, caps at 3
    sentences, and appends the citation + timestamp. Never invents facts.
    """
    # Split context into sentences.
    raw_sentences = re.split(r"(?<=[.!?])\s+", context.strip())
    sentences = [s.strip() for s in raw_sentences if s.strip()]

    # Score sentences by keyword overlap with the query.
    query_words = set(w.lower() for w in re.findall(r"[a-zA-Z0-9]+", query))
    stop = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "can", "of", "in", "on", "at", "to", "for",
        "with", "by", "from", "as", "or", "and", "not", "what", "which", "who",
        "where", "when", "how", "why", "i", "my", "me", "it", "its", "this",
        "that", "these", "those", "you", "your",
    }
    query_words = query_words - stop

    scored = []
    for s in sentences:
        words = set(w.lower() for w in re.findall(r"[a-zA-Z0-9]+", s))
        score = len(query_words & words)
        scored.append((score, s))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Take top sentences (max 3) that have at least one keyword match.
    chosen = [s for score, s in scored if score > 0][:3]
    if not chosen:
        # No keyword match: use the first sentence(s) as a best-effort fact.
        chosen = sentences[:3]

    answer = " ".join(chosen).strip()
    if not answer:
        answer = "I don't have that fact on the page."

    # Ensure at most 3 sentences.
    answer_sentences = re.split(r"(?<=[.!?])\s+", answer)
    answer = " ".join(answer_sentences[:3]).strip()
    if not answer.endswith((".", "!", "?")):
        answer += "."

    return (
        f"{answer}\n\n"
        f"Source: {source_url}\n"
        f"Last updated from sources: {ingest_ts}"
    )


def generate_answer(
    query: str,
    context: str,
    source_url: str,
    ingest_ts: str,
    model: Optional[str] = None,
) -> str:
    """Call Mistral and return the generated answer text (without formatting).

    Falls back to a deterministic, zero-token answer when Mistral is
    unavailable, rate-limited, or has no API key.
    """
    try:
        body = {
            "model": model or mistral_model(),
            "temperature": 0.2,
            "max_tokens": 250,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_user_message(query, context, source_url, ingest_ts),
                },
            ],
        }
        response = requests.post(_API_URL, headers=_headers(), json=body, timeout=_TIMEOUT_SEC)
        if response.status_code != 200:
            raise RuntimeError(f"Mistral API error {response.status_code}: {response.text[:300]}")
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    except (MissingApiKeyError, RuntimeError, Exception):
        return _deterministic_fallback(query, context, source_url, ingest_ts)
