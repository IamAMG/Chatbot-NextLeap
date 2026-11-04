"""Bulk PostgREST upsert to Supabase (single HTTP call per batch, never per-row)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Iterable, List

import httpx

from app.config import settings

logger = logging.getLogger("supabase_sync")


def _supabase_headers() -> dict:
    s = settings()
    key = s["supabase_secret_key"] or s["supabase_service_role_key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }


def _is_configured() -> bool:
    s = settings()
    return bool(s["supabase_url"] and (s["supabase_secret_key"] or s["supabase_service_role_key"]))


async def bulk_upsert(rows: Iterable[Dict[str, Any]]) -> dict:
    """Upsert a list of row dicts to Supabase in a single POST with retries."""
    rows = [r for r in rows if r]
    if not rows:
        return {"inserted": 0, "status": "skipped_empty"}
    if not _is_configured():
        return {"inserted": 0, "status": "supabase_not_configured"}

    s = settings()
    url = s["supabase_url"].rstrip("/") + "/rest/v1/sip_pipeline_rows?on_conflict=content_hash"
    headers = _supabase_headers()
    payload: List[dict] = []
    for r in rows:
        payload.append({
            "source": r.get("source"),
            "content": r.get("content"),
            "content_hash": r.get("content_hash"),
            "title": r.get("title"),
            "author": r.get("author"),
            "date": r.get("date"),
            "votes": r.get("votes", 0),
            "url": r.get("url"),
            "cleaning_status": r.get("cleaning_status"),
            "removal_reason": r.get("removal_reason"),
            "processed_by_llm": r.get("processed_by_llm", 0),
            "behavioral_trigger": r.get("behavioral_trigger"),
            "sentiment_polarity": r.get("sentiment_polarity"),
            "sentiment_label": r.get("sentiment_label"),
            "emotional_intensity": r.get("emotional_intensity"),
            "segment_proxy_ticket": r.get("segment_proxy_ticket"),
            "segment_proxy_tenure": r.get("segment_proxy_tenure"),
            "retention_dropoff_bucket": r.get("retention_dropoff_bucket"),
            "opportunity_score": r.get("opportunity_score"),
            "created_at": r.get("created_at"),
        })

    last_error = ""
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 429:
                    import time as _t
                    await asyncio.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                return {"inserted": len(payload), "status": "ok", "supabase_status": resp.status_code}
        except httpx.HTTPStatusError as exc:
            last_error = f"HTTP {exc.response.status_code}"
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            return {"inserted": 0, "status": f"supabase_error: {last_error}"}
        except Exception as exc:  # noqa: BLE001
            last_error = f"{type(exc).__name__}: {exc}"
            if attempt < 2:
                await asyncio.sleep(2 ** attempt)
                continue
            return {"inserted": 0, "status": f"supabase_error: {last_error}"}
    return {"inserted": 0, "status": f"supabase_error: {last_error}"}


def bulk_upsert_sync(rows: Iterable[Dict[str, Any]]) -> dict:
    return asyncio.run(bulk_upsert(rows))


def supabase_configured() -> bool:
    return _is_configured()
