"""Stage 1 connector: Google Play Store reviews for com.nextbillion.groww (lang=en, country=in)."""

from __future__ import annotations

from typing import List, Dict, Any

from app.db.cursors import is_newer

SOURCE = "Google Play"
APP_ID = "com.nextbillion.groww"
APP_URL = f"https://play.google.com/store/apps/details?id={APP_ID}"


def _build_url(review_id: str | None) -> str:
    if review_id:
        return f"{APP_URL}&reviewId={review_id}"
    return APP_URL


def fetch(limit: int = 200, since: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    try:
        from google_play_scraper import reviews, Sort  # type: ignore
        result, _ = reviews(
            APP_ID,
            lang="en",
            country="in",
            sort=Sort.MOST_RELEVANT,
            count=limit,
        )
        for r in result:
            at = r.get("at")
            review_id = r.get("reviewId") or ""
            date_str = at.isoformat() if hasattr(at, "isoformat") else str(at) if at else ""
            if not is_newer(date_str, since):
                continue
            rows.append({
                "source": SOURCE,
                "content": r.get("content", ""),
                "title": "Groww: Investing Made Simple",
                "author": r.get("userName"),
                "date": date_str,
                "votes": int(r.get("thumbsUpCount") or 0),
                "url": _build_url(review_id),
            })
    except Exception:
        pass
    return rows
