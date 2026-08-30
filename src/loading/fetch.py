"""Fetch HTML for allowlisted Groww pages only. No link following into other URLs."""

from __future__ import annotations

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.loading.corpus import ALLOWLIST_URLS

_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
_TIMEOUT_SEC = 45


class FetchError(Exception):
    """Raised when an allowlisted page cannot be loaded. Do not substitute another URL."""


def fetch_html(source_url: str) -> str:
    if source_url not in ALLOWLIST_URLS:
        raise FetchError(f"refused: URL is not on the corpus allowlist: {source_url}")

    request = Request(
        source_url,
        headers={
            "User-Agent": _USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-IN,en;q=0.9",
        },
        method="GET",
    )
    try:
        with urlopen(request, timeout=_TIMEOUT_SEC) as response:
            raw = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
    except HTTPError as exc:
        raise FetchError(f"HTTP {exc.code} for {source_url}") from exc
    except URLError as exc:
        raise FetchError(f"network error for {source_url}: {exc.reason}") from exc
    except TimeoutError as exc:
        raise FetchError(f"timeout for {source_url}") from exc

    return raw.decode(charset, errors="replace")
