"""Stage 1 connector: Apple App Store iTunes Customer Reviews RSS (id=1404871703, country=in)."""

from __future__ import annotations

from typing import List, Dict, Any
import httpx

from app.db.cursors import is_newer

SOURCE = "App Store"
APP_ID = "1404871703"
APP_URL = f"https://apps.apple.com/in/app/id{APP_ID}"


def fetch(limit: int = 200, since: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    url = f"https://itunes.apple.com/rss/customerreviews/id={APP_ID}/sortBy=mostRecent/json?l=en&cc=in"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            data = resp.json()
        entries = data.get("feed", {}).get("entry", [])
        # First entry is app metadata; the rest are reviews.
        for e in entries[1 : 1 + limit]:
            date_str = e.get("updated", {}).get("label", "")
            if not is_newer(date_str, since):
                continue
            link = e.get("link", {}).get("attributes", {}).get("href", "") or APP_URL
            rows.append({
                "source": SOURCE,
                "content": e.get("content", {}).get("label", ""),
                "title": e.get("im:name", {}).get("label", "Groww"),
                "author": e.get("author", {}).get("name", {}).get("label"),
                "date": date_str,
                "votes": 0,
                "url": link,
            })
    except Exception:
        pass
    return rows
