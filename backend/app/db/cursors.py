"""Persistent per-source fetch cursors (source -> last_fetched_at).

Enables incremental ingestion: each connector only pulls items newer than its
stored cursor, so daily runs don't re-fetch the whole corpus.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from app.db.models import get_connection


def get_cursor(conn: sqlite3.Connection, source: str) -> Optional[str]:
    row = conn.execute(
        "SELECT last_fetched_at FROM source_cursors WHERE source=?",
        (source,),
    ).fetchone()
    return row["last_fetched_at"] if row else None


def set_cursor(conn: sqlite3.Connection, source: str, ts: str) -> None:
    conn.execute(
        """INSERT INTO source_cursors(source, last_fetched_at)
           VALUES (?, ?)
           ON CONFLICT(source) DO UPDATE SET last_fetched_at=excluded.last_fetched_at""",
        (source, ts),
    )


def _parse_ts(value: str) -> Optional[datetime]:
    """Parse common timestamp formats returned by connectors into aware datetime."""
    if not value:
        return None
    v = value.strip()
    # Twitter: 2026-01-15T10:30:00.000Z
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    # iTunes RSS: 2026-01-15T10:30:00-05:00  (already ISO)
    try:
        dt = datetime.fromisoformat(v)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_newer(item_ts: Optional[str], since: Optional[str]) -> bool:
    """Return True if item_ts is strictly newer than since (or since is None)."""
    if since is None:
        return True
    dt_item = _parse_ts(item_ts or "")
    dt_since = _parse_ts(since or "")
    if dt_item is None or dt_since is None:
        # Can't compare -> keep the item (safe default)
        return True
    return dt_item > dt_since


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
