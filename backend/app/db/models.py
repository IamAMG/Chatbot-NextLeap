"""Local SQLite mirror of sip_pipeline_rows (WAL mode) for <10ms UI reads + offline use."""

from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "discovery_engine.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sip_pipeline_rows (
    document_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    content TEXT NOT NULL,
    content_hash TEXT UNIQUE NOT NULL,
    title TEXT,
    author TEXT,
    date TEXT,
    votes INTEGER DEFAULT 0,
    url TEXT,
    cleaning_status TEXT NOT NULL,
    removal_reason TEXT,
    processed_by_llm INTEGER DEFAULT 0,
    behavioral_trigger TEXT,
    sentiment_polarity REAL,
    sentiment_label TEXT,
    emotional_intensity REAL,
    segment_proxy_ticket TEXT,
    segment_proxy_tenure TEXT,
    retention_dropoff_bucket TEXT,
    opportunity_score INTEGER,
    created_at TEXT,
    synced_to_supabase INTEGER DEFAULT 0,
    link_status TEXT DEFAULT 'unchecked',
    link_checked_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_rows_cleaning_status ON sip_pipeline_rows(cleaning_status);
CREATE INDEX IF NOT EXISTS idx_rows_source ON sip_pipeline_rows(source);
CREATE INDEX IF NOT EXISTS idx_rows_content_hash ON sip_pipeline_rows(content_hash);
CREATE INDEX IF NOT EXISTS idx_rows_processed ON sip_pipeline_rows(processed_by_llm);
CREATE INDEX IF NOT EXISTS idx_rows_trigger ON sip_pipeline_rows(behavioral_trigger);
CREATE INDEX IF NOT EXISTS idx_rows_link_status ON sip_pipeline_rows(link_status);
CREATE TABLE IF NOT EXISTS source_cursors (
    source TEXT PRIMARY KEY,
    last_fetched_at TEXT
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Add new columns to existing databases (SQLite lacks ADD COLUMN IF NOT EXISTS)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(sip_pipeline_rows)").fetchall()}
    if "link_status" not in existing:
        try:
            conn.execute("ALTER TABLE sip_pipeline_rows ADD COLUMN link_status TEXT DEFAULT 'unchecked'")
        except sqlite3.OperationalError:
            pass
    if "link_checked_at" not in existing:
        try:
            conn.execute("ALTER TABLE sip_pipeline_rows ADD COLUMN link_checked_at TEXT")
        except sqlite3.OperationalError:
            pass


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    _migrate(conn)
    conn.executescript(SCHEMA)
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.commit()
    conn.close()
