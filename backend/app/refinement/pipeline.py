"""Content refinement pipeline: normalize -> language filter -> near-duplicate dedupe.

Runs between Stage 1 (fetch) and Stage 2 (triage) so every row entering the DB
is cleaned, language-filtered (English / Hinglish kept), and cross-source
near-duplicates are removed before triage scoring.
"""

from __future__ import annotations

import html
import re
import unicodedata
from difflib import SequenceMatcher
from typing import List, Dict, Any, Tuple

# --------------------------------------------------------------------------- #
# 1. Normalization
# --------------------------------------------------------------------------- #

_URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_HTML_RE = re.compile(r"<[^>]+>")
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)
_MULTI_WS_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Strip HTML, URLs, emojis, and collapse whitespace."""
    if not text:
        return ""
    t = html.unescape(text)
    t = _HTML_RE.sub(" ", t)
    t = _URL_RE.sub(" ", t)
    t = _EMOJI_RE.sub(" ", t)
    t = _MULTI_WS_RE.sub(" ", t).strip()
    return t


def fingerprint(text: str) -> str:
    """Normalized fingerprint for exact/near-dup matching: lowercase, alnum only."""
    t = clean_text(text).lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = _MULTI_WS_RE.sub(" ", t).strip()
    return t


# --------------------------------------------------------------------------- #
# 2. Language filter (dependency-free)
# --------------------------------------------------------------------------- #

_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_LATIN_RE = re.compile(r"[a-zA-Z]")
_COMMON_HINGLISH = {
    "hai", "hain", "ho", "hoga", "hui", "hua", "kya", "kaise", "kab", "kyun",
    "mein", "mai", "mai", "se", "ko", "ka", "ke", "ki", "waqt", "samay",
    "paisa", "rupaye", "invest", "sip", "mutual", "fund", "groww", "app",
    "accha", "achha", "bura", "khrab", "theek", "sahi", "galat", "chalo",
    "bhai", "yaar", "bhaiya", "didi", "bhai", "mere", "mera", "meri", "hamara",
    "tumhara", "uska", "uski", "uske", "yaha", "waha", "abhi", "kal", "aaj",
    "subah", "shaam", "raat", "din", "hfte", "mahina", "saal",
}


def _script_hint(text: str) -> str:
    if _DEVANAGARI_RE.search(text):
        return "devanagari"
    if _LATIN_RE.search(text):
        return "latin"
    return "other"


def detect_language(text: str) -> str:
    """Return 'en', 'hi', 'hinglish', or 'other'."""
    t = text.strip()
    if not t:
        return "other"
    script = _script_hint(t)
    if script == "devanagari":
        return "hi"
    if script == "latin":
        # Heuristic Hinglish: Latin script + at least one common Hindi word
        tokens = set(t.lower().split())
        if tokens & _COMMON_HINGLISH:
            return "hinglish"
        return "en"
    return "other"


def is_allowed_language(lang: str) -> bool:
    return lang in ("en", "hinglish", "hi")


# --------------------------------------------------------------------------- #
# 3. Near-duplicate dedupe (cross-source, within batch)
# --------------------------------------------------------------------------- #

def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def dedupe_rows(
    rows: List[Dict[str, Any]],
    threshold: float = 0.86,
) -> Tuple[List[Dict[str, Any]], int]:
    """Remove near-duplicate rows within the batch.

    Keeps the first occurrence per (source-normalized) fingerprint, then
    drops rows whose cleaned text is >= threshold similar to a kept row
    from a *different* source (cross-source dup) or same source.
    """
    kept: List[Dict[str, Any]] = []
    kept_fps: List[str] = []
    dropped = 0

    for r in rows:
        content = r.get("content", "") or ""
        fp = fingerprint(content)

        # Exact fingerprint dup -> drop
        if fp and fp in kept_fps:
            dropped += 1
            continue

        # Fuzzy near-dup vs already-kept rows
        is_dup = False
        for kfp in kept_fps:
            if _similarity(fp, kfp) >= threshold:
                is_dup = True
                break

        if is_dup:
            dropped += 1
            continue

        kept.append(r)
        if fp:
            kept_fps.append(fp)

    return kept, dropped


# --------------------------------------------------------------------------- #
# 4. Orchestration
# --------------------------------------------------------------------------- #

def refine_rows(
    rows: List[Dict[str, Any]],
    keep_languages: Tuple[str, ...] = ("en", "hinglish", "hi"),
    dup_threshold: float = 0.86,
) -> Dict[str, Any]:
    """Run the full refinement pipeline on a batch of raw rows.

    Returns:
        dict with keys: rows (cleaned, filtered, deduped), counts
    """
    total_in = len(rows)
    normalized: List[Dict[str, Any]] = []

    for r in rows:
        content = r.get("content", "") or ""
        cleaned = clean_text(content)
        if not cleaned.strip():
            continue
        r = dict(r)
        r["content"] = cleaned
        r["content_raw"] = content
        lang = detect_language(cleaned)
        r["detected_language"] = lang
        if lang not in keep_languages:
            continue
        normalized.append(r)

    after_lang = len(normalized)
    deduped, dropped = dedupe_rows(normalized, threshold=dup_threshold)

    return {
        "rows": deduped,
        "counts": {
            "in": total_in,
            "after_normalize": after_lang,
            "dropped_language": total_in - after_lang,
            "dropped_dup": dropped,
            "out": len(deduped),
        },
    }
