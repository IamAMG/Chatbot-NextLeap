"""Stage 1 connector: Gemini generates/refines commentary on seed topics."""

from __future__ import annotations

from typing import List, Dict, Any

SOURCE = "Gemini"

TOPICS = [
    "Groww SIP mutual fund user reviews India",
    "Groww app SIP investment experience comments",
    "mutual fund SIP reddit x youtube discussion Groww",
    "Groww systematic investment plan customer feedback",
]


def _key() -> str | None:
    from app.config import settings
    s = settings()
    keys = s.get("gemini_api_keys") or []
    return keys[0] if keys else ""


def _generate(api_key: str, prompt: str) -> str | None:
    try:
        import httpx
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
                json={
                    "contents": [
                        {"parts": [{"text": f"You generate short, realistic social-media style comments (2-3 sentences) about Indian mutual fund SIP investing and the Groww app. Output only the comment text, no quotes, no preamble.\n\n{prompt}"}]}
                    ],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 120},
                },
            )
            if resp.status_code != 200:
                return None
            cand = resp.json().get("candidates", [])[0]
            return cand["content"]["parts"][0]["text"].strip()
    except Exception:
        return None


def fetch(limit: int = 60, since: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    api_key = _key()
    if not api_key:
        return rows

    try:
        per_topic = max(1, limit // len(TOPICS) + 1)
        for topic in TOPICS:
            for _ in range(per_topic):
                comment = _generate(api_key, f"Write a realistic user comment about: {topic}")
                if not comment:
                    continue
                rows.append({
                    "source": SOURCE,
                    "content": comment,
                    "title": topic,
                    "author": "Gemini",
                    "date": "",
                    "votes": 0,
                    "url": "https://gemini.google.com/",
                })
                if len(rows) >= limit:
                    return rows
    except Exception:
        pass
    return rows
