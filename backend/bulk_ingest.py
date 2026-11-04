"""Bulk ingest script: pull real data from no-key connectors at high volume.
Sources: Google Play, Apple App Store, Reddit, TradingQ&A Discourse.
Runs refinement + triage, inserts into SQLite with content_hash dedupe.
"""

import sys
import hashlib
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.ingestion import play_store, app_store, reddit_ingestor, discourse_web_ingestor
from app.refinement.pipeline import refine_rows
from app.triage.signal_filter import triage_row
from app.db.models import get_connection


def _content_hash(source: str, content: str) -> str:
    norm = " ".join((content or "").lower().split())
    return hashlib.sha256(f"{source.lower()}::{norm}".encode()).hexdigest()


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat()


# Real-data connectors (no API key required)
CONNECTORS = [
    ("Google Play", play_store.fetch),
    ("App Store", app_store.fetch),
    ("Reddit", reddit_ingestor.fetch),
    ("TradingQ&A", discourse_web_ingestor.fetch),
]

LIMIT_PER_SOURCE = 400  # pull up to 400 from each


def main():
    raw_rows: list = []
    max_date_by_source: dict = {}
    conn = get_connection()

    # Fetch from each connector (ignore cursor for bulk load)
    for src_name, fn in CONNECTORS:
        try:
            rows = fn(limit=LIMIT_PER_SOURCE, since=None)
            for r in rows:
                d = r.get("date") or ""
                if d and (src_name not in max_date_by_source or d > max_date_by_source[src_name]):
                    max_date_by_source[src_name] = d
            raw_rows.extend(rows)
            print(f"[FETCH] {src_name}: {len(rows)} rows")
        except Exception as exc:
            print(f"[FETCH] {src_name}: ERROR - {exc}")

    print(f"\nTotal raw rows fetched: {len(raw_rows)}")

    # Stage 1.5: refinement (normalize, language filter, dedupe)
    refined = refine_rows(raw_rows)
    raw_rows = refined["rows"]
    counts = refined["counts"]
    print(
        f"[REFINE] in={counts['in']} out={counts['out']} "
        f"dropped_dup={counts['dropped_dup']} dropped_lang={counts['dropped_language']}"
    )

    # Stage 2: triage + insert
    clean_rows: list = []
    noise_rows: list = []
    for r in raw_rows:
        content = r.get("content", "")
        if not content.strip():
            continue
        result = triage_row(content, r.get("source", "Unknown"))
        row = {
            "source": r.get("source", "Unknown"),
            "content": content,
            "title": r.get("title"),
            "author": r.get("author"),
            "date": r.get("date"),
            "votes": r.get("votes", 0),
            "url": r.get("url"),
            "cleaning_status": result.cleaning_status,
            "removal_reason": result.removal_reason,
            "processed_by_llm": 0,
            "content_hash": _content_hash(r.get("source", "Unknown"), content),
        }
        if result.cleaning_status == "CLEAN_SIP_SIGNAL":
            clean_rows.append(row)
        else:
            noise_rows.append(row)

    # Upsert all rows (content_hash dedupe skips existing)
    inserted = 0
    all_rows = clean_rows + noise_rows
    for row in all_rows:
        try:
            cur = conn.cursor()
            cur.execute(
                """INSERT OR IGNORE INTO sip_pipeline_rows
                (source,content,content_hash,title,author,date,votes,url,
                 cleaning_status,removal_reason,processed_by_llm,created_at,synced_to_supabase)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,0)""",
                (
                    row["source"], row["content"], row["content_hash"],
                    row.get("title"), row.get("author"), row.get("date"),
                    row.get("votes", 0), row.get("url"),
                    row["cleaning_status"], row["removal_reason"],
                    row["processed_by_llm"], _now_iso(),
                ),
            )
            if cur.rowcount:
                inserted += 1
        except Exception as exc:
            print(f"[INSERT] ERROR: {exc}")

    conn.commit()

    # Advance cursors to newest fetched date per source
    for src_name, ts in max_date_by_source.items():
        from app.db.cursors import set_cursor
        set_cursor(conn, src_name, ts)
    conn.commit()

    # Final counts
    total = conn.execute("SELECT COUNT(*) AS c FROM sip_pipeline_rows").fetchone()["c"]
    clean_count = conn.execute(
        "SELECT COUNT(*) AS c FROM sip_pipeline_rows WHERE cleaning_status='CLEAN_SIP_SIGNAL'"
    ).fetchone()["c"]
    noise_count = total - clean_count

    print("\n" + "=" * 50)
    print("BULK INGEST COMPLETE")
    print("=" * 50)
    print(f"Newly inserted: {inserted}")
    print(f"Total rows in DB: {total}")
    print(f"Clean SIP signal rows: {clean_count}")
    print(f"Noise rows: {noise_count}")

    # Per-source breakdown
    print("\nPer-source breakdown:")
    cur = conn.execute("SELECT source, COUNT(*) as c, SUM(CASE WHEN cleaning_status='CLEAN_SIP_SIGNAL' THEN 1 ELSE 0 END) as clean FROM sip_pipeline_rows GROUP BY source ORDER BY c DESC")
    for src, cnt, clean in cur.fetchall():
        print(f"  {src}: {cnt} total ({clean} clean)")

    conn.close()


if __name__ == "__main__":
    main()
