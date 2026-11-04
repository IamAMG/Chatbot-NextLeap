"""Link validator: checks that every source URL stored in sip_pipeline_rows is reachable.

Updates sip_pipeline_rows.link_status (working|broken|timeout|unchecked) and
link_checked_at per row. Safe to run daily; failures never block ingestion.
"""

from __future__ import annotations

import sqlite3
from typing import List, Dict, Any
import httpx

from app.db.models import get_connection


def validate_links(concurrency: int = 8, timeout: float = 10.0) -> Dict[str, Any]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT document_id, url FROM sip_pipeline_rows WHERE url IS NOT NULL AND url != ''"
    ).fetchall()
    conn.close()

    results: List[Dict[str, Any]] = []
    statuses: Dict[str, int] = {}

    def check(row: sqlite3.Row) -> Dict[str, Any]:
        rid = row["document_id"]
        url = row["url"]
        status = "unchecked"
        try:
            with httpx.Client(timeout=timeout, follow_redirects=True) as client:
                # HEAD first; fall back to GET if 405/403/5xx
                try:
                    resp = client.head(url)
                except Exception:
                    resp = client.get(url)
                if resp.status_code < 400:
                    status = "working"
                elif resp.status_code in (405, 403, 501, 502, 503):
                    # HEAD not allowed or server issue; try GET
                    try:
                        gresp = client.get(url)
                        status = "working" if gresp.status_code < 400 else "broken"
                    except Exception:
                        status = "broken"
                else:
                    status = "broken"
        except httpx.TimeoutException:
            status = "timeout"
        except Exception:
            status = "broken"
        statuses[status] = statuses.get(status, 0) + 1
        results.append({"document_id": rid, "url": url, "status": status})
        return results[-1]

    # Run checks in a thread pool for speed
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        list(pool.map(check, rows))

    # Persist statuses back to SQLite
    conn = get_connection()
    for r in results:
        conn.execute(
            "UPDATE sip_pipeline_rows SET link_status=?, link_checked_at=datetime('now') WHERE document_id=?",
            (r["status"], r["document_id"]),
        )
    conn.commit()
    conn.close()

    return {"checked": len(results), "by_status": statuses}
