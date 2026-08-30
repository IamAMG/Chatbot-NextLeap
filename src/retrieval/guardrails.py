"""Pre-retrieve guardrails (architecture.md Phase 5.1).

Run BEFORE any query embedding / ChromaDB access. On a match: no vector-store
write and no PII present in the message is ever persisted or logged. A refusal
carries exactly one allowlisted URL where required.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from src.loading.corpus import CORPUS, CorpusPage

# --- Fund recognition -------------------------------------------------------
# Map surface tokens (short / legacy names) to the fund scheme. The Flexi-cap
# page uses the legacy "equity" slug on Groww.
_FUND_KEYS: tuple[tuple[str, str], ...] = (
    ("large cap", "large cap"),
    ("flexi cap", "flexi cap"),
    ("elss", "elss"),
    ("small cap", "small cap"),
    ("balanced advantage", "balanced"),
)

_CATEGORY_TO_FUND = {
    "large cap": "HDFC Large Cap Fund Direct Growth",
    "flexi cap": "HDFC Flexi Cap Fund Direct Growth",
    "flexi": "HDFC Flexi Cap Fund Direct Growth",
    "equity": "HDFC Flexi Cap Fund Direct Growth",
    "elss": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
    "small cap": "HDFC Small Cap Fund Direct Growth",
    "balanced": "HDFC Balanced Advantage Fund Direct Growth",
    "hybrid": "HDFC Balanced Advantage Fund Direct Growth",
}


def find_page(fund_name: str) -> Optional[CorpusPage]:
    for page in CORPUS:
        if page["fund_name"] == fund_name:
            return page
    return None


def identify_fund(query: str) -> Optional[CorpusPage]:
    """Return the matching CorpusPage if the query clearly names one fund.

    Returns None when none or more than one fund is named (ambiguous), so an
    editor can ask the user to pick.
    """
    lowered = query.lower()
    matched: set[str] = set()
    for token, _canon in _FUND_KEYS:
        if token in lowered:
            matched.add(token)
    if len(matched) != 1:
        return None
    fund_name = _CATEGORY_TO_FUND[next(iter(matched))]
    return find_page(fund_name)


def identify_fund_page_or_none(query: str) -> Optional[CorpusPage]:
    return identify_fund(query)


def _fund_url(query: str) -> Optional[str]:
    page = identify_fund(query)
    return page["source_url"] if page else None


def _general_url() -> str:
    # Educational fallback: the first (large cap) allowlisted page.
    return CORPUS[0]["source_url"]


# --- PII patterns (F8 / edge case 8) ---------------------------------------
_PAN_RE = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_AADHAAR_RE = re.compile(r"\b[2-9][0-9]{3}[ -]?[0-9]{4}[ -]?[0-9]{4}\b")
_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_OTP_RE = re.compile(r"\bOTP\b|\bverification code\b|\bone[- ]?time password\b", re.IGNORECASE)
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9][0-9]{9}(?!\d)")
_ACCOUNT_RE = re.compile(r"\b\d{10,18}\b")

_PII_LABELS = (
    ("PAN", _PAN_RE),
    ("Aadhaar", _AADHAAR_RE),
    ("email address", _EMAIL_RE),
    ("OTP", _OTP_RE),
    ("phone number", _PHONE_RE),
    ("account number", _ACCOUNT_RE),
)


def detect_pii(query: str) -> Optional[str]:
    """Return the label of the first PII-type detected, else None."""
    for label, pattern in _PII_LABELS:
        if pattern.search(query):
            return label
    return None


# --- Advice / returns intent (F6, F7; edges 5, 6) ---------------------------
_ADVICE_RE = re.compile(
    r"\b(should i|is (it|hdfc|[a-z ]+) (good|worth)|worth (investing|it|it to|buying)|"
    r"good (idea|time)|buy|sell|switch|recommend|portfolio allocation|"
    r"how much should|good time to|hold|redeem|withdraw|invest in|better to|"
    r"best time)\b",
    re.IGNORECASE,
)
_CALCULATE_RE = re.compile(
    r"\b(how much (will|would)|compute|calculate|compound|grow to)\b",
    re.IGNORECASE,
)
# Returns/compare/rank intent (F7 / edge 6): never compute, compare or rank.
_COMPARE_RE = re.compile(
    r"\b(best fund|which (fund|one|scheme) is (best|better)|compare|comparison|"
    r"vs\.?|versus|outperform|better than|rank|ranking|top fund)\b",
    re.IGNORECASE,
)
_RETURNS_RE = re.compile(
    r"\b(returns|performance|past (return|performance)|annualized|annualised|"
    r"cagr|trailing|3y|5y|10y)\b",
    re.IGNORECASE,
)
# Future-value / return projection (F7): computing how much an amount becomes.
_PROJECTION_RE = re.compile(
    r"\b(grow( n| to)?|become|worth (after|in)|future value|mature|"
    r"how much (will|would))\b",
    re.IGNORECASE,
)


@dataclass
class GuardResult:
    action: str  # "allow" | "refuse"
    category: str  # pii | empty | advice | returns | out-of-scope | ok
    reason: str = ""
    url: Optional[str] = None  # exactly one allowlisted URL on refusal
    fund_name: Optional[str] = None
    pii_label: Optional[str] = None
    matches: list = field(default_factory=list)


def _is_gibberish(query: str) -> bool:
    # A run of 5+ consecutive consonants is almost always keyboard gibberish
    # (real English words rarely exceed 4), e.g. "asdfjkl".
    if re.search(r"[bcdfghjklmnpqrstvwxz]{5,}", query, re.IGNORECASE):
        return True
    return not bool(re.search(r"[A-Za-z]{2,}", query))


def check(query: str) -> GuardResult:
    cleaned = (query or "").strip()

    # PII (F8 / edge 8) first — refuse and do not store anything.
    pii = detect_pii(query)
    if pii:
        return GuardResult(
            "refuse",
            "pii",
            "I can't accept personal or financial identifiers. Please rephrase without PAN, Aadhaar, account, OTP, email, or phone details.",
            url=_general_url(),
            pii_label=pii,
        )

    # Empty / gibberish (edge 9).
    if not cleaned or _is_gibberish(cleaned):
        return GuardResult(
            "refuse",
            "empty",
            "I couldn't understand that. Please rephrase your question.",
            url=_general_url(),
        )

    fund = identify_fund(query)

    # Advice / opinion / portfolio direction (F6 / edge 5).
    if _ADVICE_RE.search(cleaned):
        return GuardResult(
            "refuse",
            "advice",
            "I'm a facts-only assistant and can't offer investment advice or portfolio direction. I can share factual details from the fund pages.",
            url=_fund_url(cleaned) or _general_url(),
            fund_name=fund["fund_name"] if fund else None,
        )

    # Returns / compare / ranking / return-projection — never compute, compare
    # or rank (F7 / edge 6).
    if (_COMPARE_RE.search(cleaned)
            or (_RETURNS_RE.search(cleaned) and _CALCULATE_RE.search(cleaned))
            or (_PROJECTION_RE.search(cleaned) and re.search(r"\d{3,}", cleaned))):
        return GuardResult(
            "refuse",
            "returns",
            "I don't compute, compare, or rank fund returns. The official factsheet is on the fund's Groww page.",
            url=_fund_url(cleaned) or _general_url(),
            fund_name=fund["fund_name"] if fund else None,
        )

    # Out-of-scope fund (edge 7): clearly a fund question about something
    # that is not one of the five.
    if (_looks_like_fund_question(cleaned) and fund is None
            and re.search(r"\b(mutual fund|fund)\b", cleaned, re.IGNORECASE)):
        return GuardResult(
            "refuse",
            "out-of-scope",
            "That fund isn't among the five HDFC Groww pages I cover, so I don't have facts about it.",
            url=_general_url(),
        )

    return GuardResult("allow", "ok")


def _looks_like_fund_question(query: str) -> bool:
    return bool(
        re.search(
            r"\b(fund|expense|sip|exit|load|lock|risk|benchmark|nav|aum|"
            r"riskometer|stamp duty)\b",
            query,
            re.IGNORECASE,
        )
    )
