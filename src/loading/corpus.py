"""Fixed allowlist: the five Groww HDFC Direct Growth pages from architecture.md."""

from __future__ import annotations

from typing import TypedDict


class CorpusPage(TypedDict):
    fund_name: str
    category: str
    source_url: str


# Exact URLs only. Do not add factsheets, blogs, or other funds.
CORPUS: tuple[CorpusPage, ...] = (
    {
        "fund_name": "HDFC Large Cap Fund Direct Growth",
        "category": "Large-cap",
        "source_url": "https://groww.in/mutual-funds/hdfc-large-cap-fund-direct-growth",
    },
    {
        "fund_name": "HDFC Flexi Cap Fund Direct Growth",
        "category": "Flexi-cap",
        "source_url": "https://groww.in/mutual-funds/hdfc-equity-fund-direct-growth",
    },
    {
        "fund_name": "HDFC ELSS Tax Saver Fund Direct Plan Growth",
        "category": "ELSS",
        "source_url": "https://groww.in/mutual-funds/hdfc-elss-tax-saver-fund-direct-plan-growth",
    },
    {
        "fund_name": "HDFC Small Cap Fund Direct Growth",
        "category": "Small-cap",
        "source_url": "https://groww.in/mutual-funds/hdfc-small-cap-fund-direct-growth",
    },
    {
        "fund_name": "HDFC Balanced Advantage Fund Direct Growth",
        "category": "Hybrid",
        "source_url": "https://groww.in/mutual-funds/hdfc-balanced-advantage-fund-direct-growth",
    },
)

ALLOWLIST_URLS: frozenset[str] = frozenset(page["source_url"] for page in CORPUS)
