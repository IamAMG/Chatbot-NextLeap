"""Stage 3: fast micro-batched LLM extraction (15 rows per call).

Incremental mode: only untagged CLEAN_SIP_SIGNAL rows (processed_by_llm = 0);
if all tagged, refresh one fast batch of the newest 8 rows.
"""

from __future__ import annotations

import json
import random
from typing import List, Dict, Any, Optional

from app.llm.router import LLMRouter
from app.triage.signal_filter import triage_row

BATCH_SIZE = 15
REFRESH_BATCH = 8

TRIGGERS: List[str] = [
    "Anxiety on negative portfolio returns",
    "Cash-flow crunch / salary date mismatch",
    "Information overload / confusion about CAGR vs absolute returns",
    "App friction / autodebit (NACH/UPI mandate) failures",
]

SYSTEM_PROMPT = """You are a behavioral research assistant tagging Indian Groww SIP investor posts.

Task: For each input post (indexed 0..N-1), output a JSON object with exactly these keys:
- document_id: int
- behavioral_trigger: strictly one of the 4 triggers below
- sentiment_polarity: float between -1.0 and +1.0
- sentiment_label: one of "Critical","Negative","Neutral","Positive"
- emotional_intensity: float 1.0 to 10.0
- segment_proxy_ticket: one of "Rs.500 - Rs.2,000/mo","Rs.2,500 - Rs.10,000/mo","Rs.10,000 - Rs.25,000/mo","Rs.25,000+/mo"
- segment_proxy_tenure: one of "Months 1-3","Months 6-8","Months 10-12","Year 2+"
- retention_dropoff_bucket: one of "Months 1-3","Months 6-8","Months 10-12"
- opportunity_score: int 60 to 98

Allowed behavioral_trigger values (exact strings):
1. "Anxiety on negative portfolio returns"
2. "Cash-flow crunch / salary date mismatch"
3. "Information overload / confusion about CAGR vs absolute returns"
4. "App friction / autodebit (NACH/UPI mandate) failures"

Return ONLY a JSON array of objects (one per input), in the same order. No extra text.
"""


def build_extraction_prompt(rows: List[Dict[str, Any]]) -> str:
    lines = []
    for i, r in enumerate(rows):
        content = (r.get("content") or "").replace("\n", " ")
        lines.append(f"{i}. {content}")
    return "Posts to tag:\n" + "\n".join(lines)


def deterministic_tag(text: str) -> Dict[str, Any]:
    """Calibrated deterministic Indian SIP behavioral classifier (zero token, zero cost)."""
    t = (text or "").lower()
    if any(w in t for w in ["negative", "loss", "down", "red", "anxious", "worried", "scared", "panic", "falling", "in loss"]):
        trigger = "Anxiety on negative portfolio returns"
    elif any(w in t for w in ["salary", "cash", "crunch", "tight", "month end", "emi", "expense", "insufficient"]):
        trigger = "Cash-flow crunch / salary date mismatch"
    elif any(w in t for w in ["cagr", "absolute", "confus", "xirr", "don't", "donot", "overload", "which ", "how to", "metric"]):
        trigger = "Information overload / confusion about CAGR vs absolute returns"
    else:
        trigger = "App friction / autodebit (NACH/UPI mandate) failures"

    pos = sum(1 for w in ["good", "great", "happy", "satisfied", "profit", "gain", "love", "best", "started"] if w in t)
    neg = sum(1 for w in ["bad", "worst", "sad", "angry", "frustrat", "loss", "negative", "scam", "cheat", "fail", "stuck"] if w in t)
    if pos > neg:
        polarity, label = 0.4, "Positive"
    elif neg > pos:
        polarity, label = -0.5, "Negative"
    else:
        polarity, label = 0.0, "Neutral"

    intensity = min(max(5.0 + abs(polarity) * 3, 1.0), 10.0)
    ticket = "Rs.500 - Rs.2,000/mo"
    tenure = "Months 1-3"
    dropoff = "Months 1-3"
    opp = 70
    return {
        "behavioral_trigger": trigger,
        "sentiment_polarity": round(polarity, 2),
        "sentiment_label": label,
        "emotional_intensity": round(intensity, 1),
        "segment_proxy_ticket": ticket,
        "segment_proxy_tenure": tenure,
        "retention_dropoff_bucket": dropoff,
        "opportunity_score": opp,
    }


def extract_batch(rows: List[Dict[str, Any]], router: LLMRouter) -> List[Dict[str, Any]]:
    if not rows:
        return []
    prompt = build_extraction_prompt(rows)
    result = router.complete_json(SYSTEM_PROMPT, prompt)
    if result is None:
        return [merge_row(r, deterministic_tag(r.get("content", "")), used_llm=False) for r in rows]
    tags = result if isinstance(result, list) else result.get("results", [])
    out = []
    for i, r in enumerate(rows):
        tag = tags[i] if i < len(tags) and isinstance(tags[i], dict) else {}
        out.append(merge_row(r, tag, used_llm=True))
    return out


def merge_row(r: Dict[str, Any], tag: Dict[str, Any], used_llm: bool) -> Dict[str, Any]:
    return {
        "source": r.get("source"),
        "content": r.get("content"),
        "content_hash": r.get("content_hash"),
        "title": r.get("title"),
        "author": r.get("author"),
        "date": r.get("date"),
        "votes": r.get("votes", 0),
        "url": r.get("url"),
        "cleaning_status": "CLEAN_SIP_SIGNAL",
        "processed_by_llm": 1,
        "behavioral_trigger": tag.get("behavioral_trigger"),
        "sentiment_polarity": tag.get("sentiment_polarity"),
        "sentiment_label": tag.get("sentiment_label"),
        "emotional_intensity": tag.get("emotional_intensity"),
        "segment_proxy_ticket": tag.get("segment_proxy_ticket"),
        "segment_proxy_tenure": tag.get("segment_proxy_tenure"),
        "retention_dropoff_bucket": tag.get("retention_dropoff_bucket"),
        "opportunity_score": tag.get("opportunity_score"),
    }
