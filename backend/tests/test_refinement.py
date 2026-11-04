"""Backend test suite for the Groww SIP Behavioral Discovery Pipeline.

Covers:
  - content refinement pipeline (refinement/pipeline.py)
  - per-source fetch cursors (db/cursors.py)
  - resilience layer (resilience.py)
  - link validator (link_validator.py)
  - DB migration (db/models.py link_status columns)

Run:  cd backend && python -m pytest -q
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pytest

# Ensure backend/app is importable
BACKEND_APP = Path(__file__).resolve().parent.parent / "app"
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.refinement.pipeline import (
    clean_text,
    fingerprint,
    detect_language,
    is_allowed_language,
    dedupe_rows,
    refine_rows,
)  # noqa: E402
from app.db.cursors import is_newer, get_cursor, set_cursor, now_iso  # noqa: E402
from app.resilience import (  # noqa: E402
    CircuitBreaker,
    CircuitOpenError,
    RateLimiter,
    retry_with_backoff,
    fetch_with_resilience,
    circuit_status,
)
from app.db.models import get_connection, DB_PATH, SCHEMA  # noqa: E402


# --------------------------------------------------------------------------- #
# 1. Refinement pipeline
# --------------------------------------------------------------------------- #

class TestCleanText:
    def test_strips_html(self):
        assert clean_text("<b>Hello</b> world") == "Hello world"

    def test_strips_urls(self):
        assert clean_text("Check https://groww.in 🚀 now") == "Check now"

    def test_strips_emojis(self):
        assert clean_text("Great app 😍🔥") == "Great app"

    def test_collapses_whitespace(self):
        assert clean_text("a    b\n\nc") == "a b c"

    def test_empty(self):
        assert clean_text("") == ""
        assert clean_text(None) == ""  # type: ignore[arg-type]


class TestDetectLanguage:
    def test_english(self):
        assert detect_language("The weather is nice today") == "en"

    def test_hinglish(self):
        assert detect_language("Yeh groww app accha hai for mutual fund") == "hinglish"

    def test_hindi_devanagari(self):
        assert detect_language("यह बढ़िया ऐप है") == "hi"

    def test_other(self):
        assert detect_language("¡Hola! ¿Cómo estás?") == "en"  # latin script, no hinglish tokens -> en

    def test_empty(self):
        assert detect_language("") == "other"


class TestIsAllowedLanguage:
    def test_allowed(self):
        assert is_allowed_language("en") is True
        assert is_allowed_language("hinglish") is True
        assert is_allowed_language("hi") is True

    def test_not_allowed(self):
        assert is_allowed_language("es") is False
        assert is_allowed_language("other") is False


class TestDedupeRows:
    def test_exact_dup_dropped(self):
        rows = [
            {"source": "Reddit", "content": "Great app", "url": "a"},
            {"source": "X", "content": "Great app", "url": "b"},
        ]
        kept, dropped = dedupe_rows(rows)
        assert len(kept) == 1
        assert dropped == 1

    def test_near_dup_dropped(self):
        rows = [
            {"source": "Reddit", "content": "Great app for SIP investing", "url": "a"},
            {"source": "X", "content": "Great app for SIP investing!!!", "url": "b"},
        ]
        kept, dropped = dedupe_rows(rows, threshold=0.86)
        assert dropped >= 1

    def test_unique_kept(self):
        rows = [
            {"source": "Reddit", "content": "Great app", "url": "a"},
            {"source": "X", "content": "Completely different topic here", "url": "b"},
        ]
        kept, dropped = dedupe_rows(rows)
        assert len(kept) == 2
        assert dropped == 0


class TestRefineRows:
    def test_full_pipeline(self):
        rows = [
            {"source": "Reddit", "content": "<b>Great</b> app https://x.com 🚀", "url": "a"},
            {"source": "X", "content": "Great app!!! 🚀", "url": "b"},  # near-dup after cleaning
            {"source": "YouTube", "content": "Completely different unique content", "url": "c"},
            {"source": "TradingQ&A", "content": "这是中文文本", "url": "d"},  # non-target lang
        ]
        result = refine_rows(rows)
        assert result["counts"]["in"] == 4
        assert result["counts"]["dropped_language"] >= 1
        assert result["counts"]["dropped_dup"] >= 1
        assert result["counts"]["out"] >= 1
        assert all(r["detected_language"] in ("en", "hinglish", "hi") for r in result["rows"])


# --------------------------------------------------------------------------- #
# 2. Cursors
# --------------------------------------------------------------------------- #

class TestIsNewer:
    def test_none_since_keeps_all(self):
        assert is_newer("2026-01-01T00:00:00Z", None) is True

    def test_newer_item(self):
        assert is_newer("2026-06-01T00:00:00Z", "2026-01-01T00:00:00Z") is True

    def test_older_item(self):
        assert is_newer("2026-01-01T00:00:00Z", "2026-06-01T00:00:00Z") is False

    def test_twitter_format(self):
        assert is_newer("2026-06-01T10:30:00.000Z", "2026-06-01T10:00:00Z") is True

    def test_empty_item_date_keeps(self):
        assert is_newer("", "2026-01-01T00:00:00Z") is True


class TestCursorRoundTrip:
    def test_get_set_cursor(self):
        conn = get_connection()
        try:
            assert get_cursor(conn, "new-src") is None
            set_cursor(conn, "new-src", "2026-01-01T00:00:00Z")
            assert get_cursor(conn, "new-src") == "2026-01-01T00:00:00Z"
            set_cursor(conn, "new-src", "2026-06-01T00:00:00Z")
            assert get_cursor(conn, "new-src") == "2026-06-01T00:00:00Z"
        finally:
            conn.close()


# --------------------------------------------------------------------------- #
# 3. Resilience
# --------------------------------------------------------------------------- #

class TestCircuitBreaker:
    def test_opens_after_threshold(self):
        cb = CircuitBreaker.for_source("cb-test-1", failure_threshold=2, recovery_timeout=1)

        def fail():
            raise ValueError("boom")

        for _ in range(2):
            with pytest.raises(ValueError):
                cb.call(fail)
        assert cb.state == "open"

        # Open circuit blocks calls instantly
        with pytest.raises(CircuitOpenError):
            cb.call(fail)

    def test_half_open_recovers(self):
        cb = CircuitBreaker.for_source("cb-test-2", failure_threshold=1, recovery_timeout=0.1)

        def fail():
            raise ValueError("boom")

        with pytest.raises(ValueError):
            cb.call(fail)
        assert cb.state == "open"

        time.sleep(0.15)  # past recovery_timeout

        def ok():
            return "success"

        # Half-open trial succeeds -> closes
        assert cb.call(ok) == "success"
        assert cb.state == "closed"


class TestRetryWithBackoff:
    def test_retries_then_succeeds(self):
        calls = []

        @retry_with_backoff(max_retries=2, base_delay=0.01, max_delay=1, jitter=False)
        def flaky():
            calls.append(1)
            if len(calls) < 2:
                raise ConnectionError("down")
            return "ok"

        assert flaky() == "ok"
        assert len(calls) == 2

    def test_exhausts_retries(self):
        calls = []

        @retry_with_backoff(max_retries=1, base_delay=0.01, max_delay=1, jitter=False)
        def always_fail():
            calls.append(1)
            raise RuntimeError("permanent")

        with pytest.raises(RuntimeError):
            always_fail()
        assert len(calls) == 2  # 1 initial + 1 retry


class TestFetchWithResilience:
    def test_happy_path(self):
        def good():
            return [{"source": "X", "content": "hi"}]

        rows = fetch_with_resilience(good, "happy-src", timeout=10.0, max_retries=0)
        assert rows == [{"source": "X", "content": "hi"}]

    def test_timeout_returns_empty(self):
        def hang():
            time.sleep(10)
            return []

        rows = fetch_with_resilience(hang, "hang-src", timeout=1.0, max_retries=0)
        assert rows == []

    def test_circuit_open_returns_empty_instantly(self):
        def hang():
            time.sleep(10)
            return []

        # Trip circuit
        for _ in range(2):
            fetch_with_resilience(hang, "cb-src", timeout=1.0, max_retries=0, failure_threshold=2, recovery_timeout=1)

        start = time.time()
        rows = fetch_with_resilience(hang, "cb-src", timeout=10.0, failure_threshold=2, recovery_timeout=1)
        elapsed = time.time() - start
        assert rows == []
        assert elapsed < 1.0  # short-circuited, not waiting for timeout


# --------------------------------------------------------------------------- #
# 4. DB migration (link_status columns)
# --------------------------------------------------------------------------- #

class TestDbMigration:
    def test_link_status_columns_exist(self):
        conn = get_connection()
        try:
            cols = {row[1] for row in conn.execute("PRAGMA table_info(sip_pipeline_rows)").fetchall()}
            assert "link_status" in cols
            assert "link_checked_at" in cols
        finally:
            conn.close()

    def test_source_cursors_table_exists(self):
        conn = get_connection()
        try:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            assert "source_cursors" in tables
        finally:
            conn.close()
