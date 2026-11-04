"""Stage 1 connector: Reddit (praw if configured, else public .json endpoints)."""

from __future__ import annotations

from typing import List, Dict, Any
import datetime
import httpx

from app.db.cursors import is_newer

SOURCE = "Reddit"
SUBREDDITS = ["MutualfundsIndia", "IndiaInvestments", "personalfinanceindia"]
REDDIT_BASE = "https://www.reddit.com"


def _subreddit_url(sub: str) -> str:
    return f"{REDDIT_BASE}/r/{sub}/search/?q=groww%20sip"


def _fetch_json(url: str, headers: dict) -> dict | None:
    try:
        with httpx.Client(timeout=30.0, headers=headers) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.json()
    except Exception:
        pass
    return None


def _utc_iso(ts: float) -> str:
    try:
        return datetime.datetime.utcfromtimestamp(float(ts)).isoformat()
    except Exception:
        return ""


def _build_url(permalink: str | None) -> str:
    if permalink:
        return f"{REDDIT_BASE}{permalink}"
    return f"{REDDIT_BASE}/search/?q=groww%20sip"


def fetch(limit: int = 200, since: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    headers = {"User-Agent": "groww-sip-discovery/1.0 (by /u/unknown)"}
    from app.config import settings
    s = settings()
    use_praw = bool(s["reddit_client_id"])

    if use_praw:
        try:
            import praw  # type: ignore
            reddit = praw.Reddit(
                client_id=s["reddit_client_id"],
                client_secret=s["reddit_client_secret"],
                user_agent=s["reddit_user_agent"],
            )
            per_sub = max(1, limit // len(SUBREDDITS) + 1)
            for sub in SUBREDDITS:
                for submission in reddit.subreddit(sub).search("groww sip", limit=per_sub):
                    date_str = _utc_iso(submission.created_utc)
                    if not is_newer(date_str, since):
                        continue
                    rows.append({
                        "source": SOURCE,
                        "content": submission.selftext or submission.title,
                        "title": submission.title,
                        "author": str(submission.author) if submission.author else None,
                        "date": date_str,
                        "votes": int(submission.score or 0),
                        "url": _build_url(submission.permalink),
                    })
                    # pull a few top comments
                    submission.comments.replace_more(limit=0)
                    for comment in submission.comments[:5]:
                        if hasattr(comment, "body"):
                            cdate = _utc_iso(comment.created_utc)
                            if not is_newer(cdate, since):
                                continue
                            rows.append({
                                "source": SOURCE,
                                "content": comment.body,
                                "title": submission.title,
                                "author": str(comment.author) if comment.author else None,
                                "date": cdate,
                                "votes": int(comment.score or 0),
                                "url": _build_url(comment.permalink),
                            })
        except Exception:
            use_praw = False

    if not use_praw:
        for sub in SUBREDDITS:
            url = f"https://www.reddit.com/r/{sub}/search.json?q=groww%20sip&restrict_sr=1&limit=25"
            data = _fetch_json(url, headers)
            if not data:
                continue
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                date_str = _utc_iso(d.get("created_utc", 0)) if d.get("created_utc") else ""
                if not is_newer(date_str, since):
                    continue
                rows.append({
                    "source": SOURCE,
                    "content": d.get("selftext") or d.get("title", ""),
                    "title": d.get("title"),
                    "author": d.get("author"),
                    "date": date_str,
                    "votes": int(d.get("score") or 0),
                    "url": _build_url(d.get("permalink") or ""),
                })
    return rows
