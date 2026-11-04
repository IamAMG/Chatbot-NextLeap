"""Resilience layer: per-source circuit breakers, rate limiters, and retry with
exponential backoff + jitter. Stdlib only — no new dependencies.

Usage in main.py ingest():
    from app.resilience import fetch_with_resilience, circuit_status
    rows = fetch_with_resilience(play_store.fetch, "Google Play", since=since)
"""

from __future__ import annotations

import time
import random
import threading
import concurrent.futures
from functools import wraps
from typing import Callable, TypeVar, Any, Optional, Dict, List, Tuple

T = TypeVar("T")


# --------------------------------------------------------------------------- #
# Circuit breaker
# --------------------------------------------------------------------------- #

class CircuitOpenError(Exception):
    """Raised when a source's circuit breaker is open (temporarily skipped)."""


class CircuitBreaker:
    """Thread-safe circuit breaker per source.

    States:
      closed   - calls proceed normally
      open     - calls are rejected for recovery_timeout seconds
      half-open - a single trial call is allowed; success closes, failure re-opens
    """

    _instances: Dict[str, "CircuitBreaker"] = {}
    _lock = threading.Lock()

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max_calls: int = 1,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self._failures = 0
        self._last_failure_time: Optional[float] = None
        self._state = "closed"  # closed | open | half-open
        self._half_open_calls = 0
        self._lock = threading.RLock()

    @classmethod
    def for_source(cls, source: str, **kwargs) -> "CircuitBreaker":
        with cls._lock:
            if source not in cls._instances:
                cls._instances[source] = CircuitBreaker(**kwargs)
            return cls._instances[source]

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def failures(self) -> int:
        with self._lock:
            return self._failures

    def _record_success(self) -> None:
        self._failures = 0
        self._last_failure_time = None
        self._state = "closed"
        self._half_open_calls = 0

    def _record_failure(self) -> None:
        self._failures += 1
        self._last_failure_time = time.monotonic()
        if self._state == "half-open":
            self._state = "open"
        elif self._failures >= self.failure_threshold:
            self._state = "open"

    def _may_proceed(self) -> bool:
        """Return True if a call should be attempted now."""
        with self._lock:
            if self._state == "closed":
                return True
            if self._state == "open":
                if (
                    self._last_failure_time is not None
                    and time.monotonic() - self._last_failure_time > self.recovery_timeout
                ):
                    self._state = "half-open"
                    self._half_open_calls = 0
                    return True
                return False
            # half-open
            if self._half_open_calls < self.half_open_max_calls:
                self._half_open_calls += 1
                return True
            return False

    def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute func under circuit-breaker protection."""
        if not self._may_proceed():
            raise CircuitOpenError(f"circuit open for source")
        try:
            result = func(*args, **kwargs)
        except Exception:
            self._record_failure()
            raise
        self._record_success()
        return result


def circuit_status() -> Dict[str, Dict[str, Any]]:
    """Snapshot of every known circuit breaker (for /api/ingest diagnostics)."""
    out: Dict[str, Dict[str, Any]] = {}
    with CircuitBreaker._lock:
        sources = list(CircuitBreaker._instances.keys())
    for src in sources:
        cb = CircuitBreaker.for_source(src)
        out[src] = {"state": cb.state, "failures": cb.failures}
    return out


# --------------------------------------------------------------------------- #
# Rate limiter (token bucket, per source)
# --------------------------------------------------------------------------- #

class RateLimiter:
    """Simple token bucket per source.

    `rate` = tokens per second, `capacity` = max burst. Call .acquire() before
    each fetch; blocks until a token is available.
    """

    _instances: Dict[str, "RateLimiter"] = {}
    _lock = threading.Lock()

    def __init__(self, rate: float = 1.0, capacity: int = 5):
        self.rate = rate
        self.capacity = capacity
        self._tokens = float(capacity)
        self._last = time.monotonic()
        self._lock = threading.RLock()

    @classmethod
    def for_source(cls, source: str, rate: float = 1.0, capacity: int = 5) -> "RateLimiter":
        with cls._lock:
            if source not in cls._instances:
                cls._instances[source] = RateLimiter(rate=rate, capacity=capacity)
            return cls._instances[source]

    def acquire(self) -> None:
        while True:
            with self._lock:
                now = time.monotonic()
                elapsed = now - self._last
                self._last = now
                self._tokens = min(self.capacity, self._tokens + elapsed * self.rate)
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                # need to wait for at least one token
                wait = (1.0 - self._tokens) / self.rate
            time.sleep(min(wait, 5.0))


# --------------------------------------------------------------------------- #
# Retry with exponential backoff + jitter
# --------------------------------------------------------------------------- #

def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: bool = True,
    retry_on: Tuple[type, ...] = (Exception,),
):
    """Decorator: retry `func` on `retry_on` exceptions with exponential backoff.

    delay = min(base_delay * 2**attempt + jitter, max_delay)
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exc: Optional[Exception] = None
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as exc:
                    last_exc = exc
                    if attempt == max_retries:
                        break
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    if jitter:
                        delay = delay * (0.5 + random.random())
                    time.sleep(delay)
            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


# --------------------------------------------------------------------------- #
# Orchestrated resilient fetch
# --------------------------------------------------------------------------- #

def fetch_with_resilience(
    fetch_fn: Callable[..., List[dict]],
    source: str,
    *args,
    rate: float = 1.0,
    capacity: int = 5,
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    max_retries: int = 3,
    base_delay: float = 1.0,
    timeout: float = 25.0,
    **kwargs,
) -> List[dict]:
    """Call `fetch_fn(*args, **kwargs)` protected by:
      1. Rate limiter (token bucket, per source)
      2. Circuit breaker (per source)
      3. Retry with exponential backoff + jitter
      4. Per-call timeout (so one hanging connector never stalls the run)

    Returns the rows list on success. On circuit-open, timeout, or total retry
    exhaustion, returns [] (so one flaky source never blocks the daily run).
    """
    limiter = RateLimiter.for_source(source, rate=rate, capacity=capacity)
    breaker = CircuitBreaker.for_source(
        source,
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
    )

    limiter.acquire()

    if breaker.state == "open":
        # Temporarily skip this source; do not stall the whole ingest.
        return []

    def _call_once() -> List[dict]:
        @retry_with_backoff(
            max_retries=max_retries,
            base_delay=base_delay,
            max_delay=30.0,
            jitter=True,
        )
        def _inner():
            return fetch_fn(*args, **kwargs)

        return _inner()

    try:
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(_call_once)
        try:
            rows = future.result(timeout=timeout)
        finally:
            pool.shutdown(wait=False, cancel_futures=True)
        breaker._record_success()
        return rows
    except CircuitOpenError:
        return []
    except concurrent.futures.TimeoutError:
        breaker._record_failure()
        return []
    except Exception:
        breaker._record_failure()
        return []
