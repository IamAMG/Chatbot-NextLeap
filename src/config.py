"""Load configuration / API keys from .env at the repo root.

Secrets (MISTRAL_API_KEY, HF_TOKEN) live only in .env and are never
written to data/ or logged.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

_ENV_FILE = _REPO_ROOT / ".env"


def load_env() -> None:
    # Load once; harmless to call repeatedly (dotenv skips existing keys).
    try:
        from dotenv import load_dotenv

        load_dotenv(_ENV_FILE, override=False)
    except ImportError:  # pragma: no cover - python-dotenv is a declared dep
        pass


def mistral_api_key() -> str | None:
    load_env()
    import os

    return os.getenv("MISTRAL_API_KEY") or None


def mistral_model() -> str:
    load_env()
    import os

    return (os.getenv("MISTRAL_MODEL") or "mistral-small-latest").strip() or "mistral-small-latest"


def hf_token() -> str | None:
    load_env()
    import os

    return os.getenv("HF_TOKEN") or None


class MissingApiKeyError(RuntimeError):
    """Raised when the Mistral API key is missing but generation is needed."""
