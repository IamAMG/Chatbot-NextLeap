"""Ingest-time snapshot: visible HTML text plus FAQ facts from this page only."""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any

_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL,
)

# FAQ-oriented fields on this fund page. Skip peers, historic series, other-fund lists.
_FACT_KEYS: tuple[tuple[str, str], ...] = (
    ("scheme_name", "Scheme name"),
    ("expense_ratio", "Expense ratio"),
    ("min_sip_investment", "Minimum SIP"),
    ("min_investment_amount", "Minimum lumpsum / first investment"),
    ("mini_additional_investment", "Minimum additional investment"),
    ("exit_load", "Exit load"),
    ("lock_in", "Lock-in"),
    ("nfo_risk", "Riskometer"),
    ("benchmark", "Benchmark"),
    ("benchmark_name", "Benchmark name"),
    ("stamp_duty", "Stamp duty"),
    ("category", "Groww category"),
    ("sub_category", "Sub-category"),
    ("plan_type", "Plan type"),
    ("aum", "Fund size (AUM, Cr)"),
    ("nav", "NAV"),
    ("nav_date", "NAV date"),
    ("description", "Investment objective"),
)


class _VisibleTextParser(HTMLParser):
    _SKIP = frozenset({"script", "style", "noscript", "svg"})

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self._SKIP:
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in self._SKIP and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = data.strip()
        if text:
            self._parts.append(text)

    def text(self) -> str:
        return "\n".join(self._parts)


def extract_visible_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    parser.close()
    return _collapse_blank_lines(parser.text())


def extract_page_facts(html: str) -> str:
    """Readable facts from __NEXT_DATA__ for this page. Does not fetch other URLs."""
    match = _NEXT_DATA_RE.search(html)
    if not match:
        return ""
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return ""

    data = (
        payload.get("props", {})
        .get("pageProps", {})
        .get("mfServerSideData")
    )
    if not isinstance(data, dict):
        return ""

    lines = ["[Page facts from this Groww fund page]"]
    for key, label in _FACT_KEYS:
        if key not in data:
            continue
        formatted = _format_fact_value(data[key])
        if formatted:
            lines.append(f"{label}: {formatted}")
    return "\n".join(lines) if len(lines) > 1 else ""


_FOOTER_MARKERS = (
    "Vaishnavi Tech Park",
    "Download the App",
    "© 2016-",
)


def trim_site_chrome(visible: str, fund_name: str) -> str:
    """Keep this fund page body; drop global Groww nav/footer. No extra URLs."""
    start = 0
    if fund_name:
        needle = f"\n{fund_name}\n"
        idx = visible.find(needle)
        start = idx + 1 if idx != -1 else 0
    body = visible[start:]
    cut = len(body)
    for marker in _FOOTER_MARKERS:
        pos = body.find(marker)
        if pos != -1:
            cut = min(cut, pos)
    return body[:cut].strip()


def snapshot_text(html: str, fund_name: str = "") -> str:
    visible = trim_site_chrome(extract_visible_text(html), fund_name)
    facts = extract_page_facts(html)
    parts = [part for part in (facts, visible) if part]
    return "\n\n".join(parts).strip()


def _format_fact_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict) and {"years", "months", "days"} <= set(value.keys()):
        bits = []
        for unit in ("years", "months", "days"):
            amount = value.get(unit)
            if amount not in (None, "", 0, "0"):
                bits.append(f"{amount} {unit}")
        return ", ".join(bits) if bits else "none stated"
    return ""


def _collapse_blank_lines(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    kept: list[str] = []
    blank = False
    for line in lines:
        if not line:
            blank = True
            continue
        if blank and kept:
            kept.append("")
        blank = False
        kept.append(line)
    return "\n".join(kept)
