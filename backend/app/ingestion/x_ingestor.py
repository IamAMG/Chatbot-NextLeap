"""Stage 1 connector: X / Twitter API v2 recent search (requires X_BEARER_TOKEN)."""

from __future__ import annotations

from typing import List, Dict, Any
import httpx

from app.db.cursors import is_newer

SOURCE = "X"
X_SEARCH = "https://api.twitter.com/2/tweets/search/recent"
QUERY = "Groww SIP mutual fund India -is:retweet lang:en"


def _bearer() -> str | None:
    from app.config import settings
    s = settings()
    return s.get("x_bearer_token") or ""


def fetch(limit: int = 100, since: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    token = _bearer()
    if not token:
        return rows

    try:
        with httpx.Client(timeout=30.0, headers={"Authorization": f"Bearer {token}"}) as client:
            resp = client.get(X_SEARCH, params={
                "query": QUERY,
                "max_results": min(max(limit, 10), 100),
                "tweet.fields": "created_at,author_id,public_metrics,conversation_id",
                "user.fields": "username,name",
                "expansions": "author_id",
            })
            if resp.status_code != 200:
                return rows

            data = resp.json()
            tweets = data.get("data", [])
            users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}

            for t in tweets:
                date_str = t.get("created_at", "")
                if not is_newer(date_str, since):
                    continue
                metrics = t.get("public_metrics", {})
                author = users.get(t.get("author_id"), {})
                rows.append({
                    "source": SOURCE,
                    "content": t.get("text", ""),
                    "title": f"X post by {author.get('username', 'unknown')}",
                    "author": author.get("username"),
                    "date": date_str,
                    "votes": int(metrics.get("like_count") or 0),
                    "url": f"https://twitter.com/i/web/status/{t.get('id')}",
                })
    except Exception:
        pass
    return rows
