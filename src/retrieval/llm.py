"""LLM generation via the Mistral API (architecture.md Phase 5.3).

Contract enforced in the system prompt:
  * facts from retrieved context only
  * no advice
  * no performance/return math
  * no PII echo
  * <= 3 sentences
  * one citation URL
  * a "Last updated from sources: <ingest_ts>" line
"""

from __future__ import annotations

import json
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


def generate_answer(
    query: str,
    context: str,
    source_url: str,
    ingest_ts: str,
    model: Optional[str] = None,
) -> str:
    """Call Mistral and return the generated answer text (without formatting)."""
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
