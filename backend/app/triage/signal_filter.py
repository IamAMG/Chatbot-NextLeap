"""Stage 2: deterministic zero-token noise cleaning & SIP signal scoring."""

from __future__ import annotations

import re
from dataclasses import dataclass

SIP_ANCHORS = (
    "sip", "mutual fund", "mutualfunds", "mf", "nav", "xirr", "mandate",
    "autopay", "auto pay", "otm", "nach", "elss", "folio", "lumpsum", "lumsum",
    "redeem", "redemption", "direct", "soa", "statement of account", "demat",
    "pause", "stop sip", "skip", "instalment", "installment", "amt",
)

PROMO_PATTERNS = (
    "referral", "referral code", "promo code", "coupon", "telegram",
    "whatsapp", "join my", "earn", "cashback", "discount", "promo",
)

FIRST_PERSON = (
    "i started", "i started a", "my sip", "i paused", "i stopped",
    "i want to", "i need", "i have", "i am", "i'm", "me", "mujhe",
    "mere", "mera", "meri", "maine", "kaise", "kya", "kyun", "kyuki",
    "mai", "main", "hum", "meri sip", "mere sip", "mera sip", "mujhe sip",
    "shuru", "shuru kiya", "chalu", "band",
)

GENERIC_PRAISE = (
    "good app", "great app", "nice app", "best app", "awesome", "superb",
    "bad app", "worst app", "worst", "radhe radhe", "nice video", "good video",
)

_BODY_ANCHOR_RE = re.compile("|".join(re.escape(a) for a in SIP_ANCHORS), re.IGNORECASE)
_BODY_PROMO_RE = re.compile("|".join(re.escape(p) for p in PROMO_PATTERNS), re.IGNORECASE)
_BODY_FIRST_RE = re.compile("|".join(re.escape(f) for f in FIRST_PERSON), re.IGNORECASE)


def _word_count(text: str) -> int:
    return len([w for w in (text or "").split() if w])


@dataclass
class TriageResult:
    cleaning_status: str  # FILTERED_SPAM_PROMO | FILTERED_NON_SIP | CLEAN_SIP_SIGNAL
    removal_reason: str | None
    word_count: int
    has_sip_anchor: bool
    has_first_person: bool
    is_promo: bool


def triage_row(content: str, source: str) -> TriageResult:
    """Score strictly on the comment content body.

    For youtube / play_store / app_store the body alone is scored (never the
    video title prepended), so short generic comments don't inherit title keywords.
    """
    body = (content or "").strip()
    word_count = _word_count(body)
    is_promo = bool(_BODY_PROMO_RE.search(body))
    has_sip_anchor = bool(_BODY_ANCHOR_RE.search(body))
    has_first_person = bool(_BODY_FIRST_RE.search(body))

    if is_promo:
        return TriageResult(
            "FILTERED_SPAM_PROMO",
            "Removed promo/referral/Telegram-WhatsApp noise",
            word_count,
            has_sip_anchor,
            has_first_person,
            True,
        )

    if word_count < 6:
        return TriageResult(
            "FILTERED_NON_SIP",
            "Removed 1-5 word generic app-store one-liner",
            word_count,
            has_sip_anchor,
            has_first_person,
            False,
        )

    if not has_sip_anchor:
        return TriageResult(
            "FILTERED_NON_SIP",
            "Removed non-SIP content (no SIP/mutual-fund anchor)",
            word_count,
            has_sip_anchor,
            has_first_person,
            False,
        )

    if not has_first_person:
        return TriageResult(
            "FILTERED_NON_SIP",
            "Removed non-narrative third-party content",
            word_count,
            has_sip_anchor,
            has_first_person,
            False,
        )

    return TriageResult("CLEAN_SIP_SIGNAL", None, word_count, has_sip_anchor, has_first_person, False)
