"""Stage 1 connector: YouTube Data API v3 (only if YOUTUBE_API_KEY present)."""

from __future__ import annotations

from typing import List, Dict, Any
import httpx

from app.db.cursors import is_newer

SOURCE = "YouTube"
YOUTUBE_WATCH = "https://www.youtube.com/watch?v="
YOUTUBE_SEARCH = "https://www.youtube.com/results?search_query=Groww%20SIP%20mutual%20fund"


def fetch(limit: int = 200, since: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    from app.config import settings
    s = settings()
    if not s["youtube_api_key"]:
        return rows

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.get("https://www.googleapis.com/youtube/v3/search", params={
                "key": s["youtube_api_key"],
                "part": "snippet",
                "q": "Groww SIP mutual fund India",
                "type": "video",
                "regionCode": "IN",
                "relevanceLanguage": "en",
                "maxResults": 10,
            })
            if resp.status_code != 200:
                return rows
            videos = resp.json().get("items", [])
            titles = {v["id"]["videoId"]: v["snippet"]["title"] for v in videos}

            for vid in list(titles.keys())[:5]:
                cresp = client.get("https://www.googleapis.com/youtube/v3/commentThreads", params={
                    "key": s["youtube_api_key"],
                    "part": "snippet",
                    "videoId": vid,
                    "maxResults": 50,
                    "textFormat": "plainText",
                })
                if cresp.status_code != 200:
                    continue
                for item in cresp.json().get("items", []):
                    top = item["snippet"]["topLevelComment"]["snippet"]
                    date_str = top.get("publishedAt", "")
                    if not is_newer(date_str, since):
                        continue
                    rows.append({
                        "source": SOURCE,
                        "content": top.get("textOriginal", ""),
                        "title": titles.get(vid),
                        "author": top.get("authorDisplayName"),
                        "date": date_str,
                        "votes": int(top.get("likeCount") or 0),
                        "url": f"{YOUTUBE_WATCH}{vid}",
                    })
    except Exception:
        pass
    return rows
