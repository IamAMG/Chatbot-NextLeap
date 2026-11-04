"""Stage 1 connector: TradingQ&A Discourse + Tavily + Firecrawl."""

from __future__ import annotations

from typing import List, Dict, Any
import httpx

from app.db.cursors import is_newer

SOURCE = "TradingQ&A"
TRADINGQNA_BASE = "https://tradingqna.com"
TRADINGQNA_SEARCH = f"{TRADINGQNA_BASE}/search?q=groww%20sip"


def _get(url: str, headers: dict) -> dict | None:
    try:
        with httpx.Client(timeout=30.0, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


def _topic_url(slug: str | None, tid: int | str | None) -> str:
    if slug and tid:
        return f"{TRADINGQNA_BASE}/t/{slug}/{tid}"
    return TRADINGQNA_SEARCH


def _valid_url(url: str | None, fallback: str) -> str:
    return url if url else fallback


def fetch(limit: int = 200, since: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    headers = {"User-Agent": "groww-sip-discovery/1.0"}

    # TradingQ&A public Discourse search (zero cost)
    data = _get("https://tradingqna.com/search.json?q=groww%20sip", headers)
    if data:
        for t in data.get("topics", [])[:limit]:
            date_str = t.get("bumped_at") or t.get("created_at") or ""
            if not is_newer(date_str, since):
                continue
            slug = t.get("slug") or ""
            tid = t.get("id")
            rows.append({
                "source": SOURCE,
                "content": t.get("excerpt") or t.get("title", ""),
                "title": t.get("title"),
                "author": (t.get("last_poster_username")
                           or (t.get("posters") or [{}])[0].get("username")),
                "date": date_str,
                "votes": 0,
                "url": _topic_url(slug, tid),
            })

    from app.config import settings
    s = settings()

    # Tavily (optional)
    if s["tavily_api_key"]:
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": s["tavily_api_key"],
                        "query": "Groww SIP mutual fund India investor forum discussion",
                        "max_results": 10,
                    },
                )
                if resp.status_code == 200:
                    for r in resp.json().get("results", []):
                        date_str = r.get("published_date") or ""
                        if not is_newer(date_str, since):
                            continue
                        rows.append({
                            "source": SOURCE,
                            "content": r.get("content", ""),
                            "title": r.get("title"),
                            "author": None,
                            "date": date_str,
                            "votes": 0,
                            "url": _valid_url(r.get("url"), TRADINGQNA_SEARCH),
                        })
        except Exception:
            pass

    # Firecrawl (optional)
    if s["firecrawl_api_key"]:
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    "https://api.firecrawl.dev/v1/search",
                    headers={"Authorization": f"Bearer {s['firecrawl_api_key']}"},
                    json={
                        "query": "site:tradingqna.com OR site:reddit.com Groww SIP pause stop XIRR",
                        "limit": 10,
                    },
                )
                if resp.status_code == 200:
                    for r in resp.json().get("data", []):
                        date_str = r.get("published_date") or ""
                        if not is_newer(date_str, since):
                            continue
                        rows.append({
                            "source": SOURCE,
                            "content": r.get("content") or r.get("description", ""),
                            "title": r.get("title"),
                            "author": None,
                            "date": date_str,
                            "votes": 0,
                            "url": _valid_url(r.get("url"), TRADINGQNA_SEARCH),
                        })
        except Exception:
            pass

    return rows
