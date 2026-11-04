"""Daily scheduler: runs /api/ingest + /api/validate-links once per day.

Run:  cd backend && python -m app.scheduler
Interval is controlled by SCHEDULER_INTERVAL_HOURS env (default 24).
Uses only the stdlib (threading + time) so no new dependency is required.
"""

from __future__ import annotations

import os
import time
import threading
import httpx

BASE_URL = os.getenv("SCHEDULER_BASE_URL", "http://127.0.0.1:8000")
INTERVAL_HOURS = float(os.getenv("SCHEDULER_INTERVAL_HOURS", "24"))


def _call(path: str) -> dict:
    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{BASE_URL}{path}")
            return {"path": path, "status": resp.status_code, "body": resp.json()}
    except Exception as exc:  # noqa: BLE001
        return {"path": path, "status": "error", "error": str(exc)}


def run_cycle() -> list[dict]:
    return [_call("/api/ingest"), _call("/api/validate-links")]


def loop() -> None:
    while True:
        run_cycle()
        time.sleep(INTERVAL_HOURS * 3600)


def start_background() -> threading.Thread:
    t = threading.Thread(target=loop, daemon=True, name="daily-scheduler")
    t.start()
    return t


if __name__ == "__main__":
    import signal

    print(f"[scheduler] running ingest+validate-links every {INTERVAL_HOURS}h -> {BASE_URL}")
    stop = threading.Event()

    def handle(signum, frame):  # noqa: ANN001
        stop.set()

    signal.signal(signal.SIGINT, handle)
    signal.signal(signal.SIGTERM, handle)

    while not stop.is_set():
        results = run_cycle()
        print("[scheduler] cycle:", results)
        stop.wait(INTERVAL_HOURS * 3600)
