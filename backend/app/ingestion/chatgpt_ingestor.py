"""Stage 1 connector: ChatGPT (OpenAI) generates/refines commentary on seed topics."""

from __future__ import annotations

from typing import List, Dict, Any

SOURCE = "ChatGPT"

TOPICS = [
    "Groww SIP mutual fund user reviews India",
    "Groww app SIP investment experience comments",
    "mutual fund SIP reddit x youtube discussion Groww",
    "Groww systematic investment plan customer feedback",
]


def _key() -> str | None:
    from app.config import settings
    s = settings()
    return s.get("openai_api_key") or ""


def _chat_complete(api_key: str, prompt: str) -> str | None:
    try:
        import httpx
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You generate short, realistic social-media style comments (2-3 sentences) about Indian mutual fund SIP investing and the Groww app. Output only the comment text, no quotes, no preamble."},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 120,
                },
            )
            if resp.status_code != 200:
                return None
            return resp.json()["choices"][0]["message"]["content"].strip()
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
                comment = _chat_complete(api_key, f"Write a realistic user comment about: {topic}")
                if not comment:
                    continue
                rows.append({
                    "source": SOURCE,
                    "content": comment,
                    "title": topic,
                    "author": "ChatGPT",
                    "date": "",
                    "votes": 0,
                    "url": "https://chat.openai.com/",
                })
                if len(rows) >= limit:
                    return rows
    except Exception:
        pass
    return rows
