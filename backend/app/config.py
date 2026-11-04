"""Backend configuration for the Groww SIP Behavioral Discovery Pipeline.

All secrets live in backend/.env and are read only by the FastAPI server.
Never exposed to the frontend / browser.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - python-dotenv is a declared dep
    load_dotenv = None  # type: ignore

_REPO_ROOT = Path(__file__).resolve().parents[2]  # backend/app -> repo root
_ENV_FILE = _REPO_ROOT / "backend" / ".env"


def load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(_ENV_FILE, override=False)


@lru_cache(maxsize=1)
def settings() -> dict:
    load_env()
    return {
        "supabase_url": os.getenv("SUPABASE_URL", "").strip(),
        "supabase_secret_key": os.getenv("SUPABASE_SECRET_KEY", "").strip(),
        "supabase_service_role_key": os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip(),
        "groq_api_keys": [k.strip() for k in os.getenv("GROQ_API_KEYS", "").split(",") if k.strip()],
        "gemini_api_keys": [k.strip() for k in os.getenv("GEMINI_API_KEYS", "").split(",") if k.strip()],
        "openrouter_api_keys": [k.strip() for k in os.getenv("OPENROUTER_API_KEYS", "").split(",") if k.strip()],
        "mistral_api_keys": [k.strip() for k in os.getenv("MISTRAL_API_KEYS", "").split(",") if k.strip()],
        "xai_api_keys": [k.strip() for k in os.getenv("XAI_API_KEYS", "").split(",") if k.strip()],
        "reddit_client_id": os.getenv("REDDIT_CLIENT_ID", "").strip(),
        "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET", "").strip(),
        "reddit_user_agent": os.getenv("REDDIT_USER_AGENT", "groww-sip-discovery/1.0").strip(),
        "tavily_api_key": os.getenv("TAVILY_API_KEY", "").strip(),
        "firecrawl_api_key": os.getenv("FIRECRAWL_API_KEY", "").strip(),
        "youtube_api_key": os.getenv("YOUTUBE_API_KEY", "").strip(),
        "x_bearer_token": os.getenv("X_BEARER_TOKEN", "").strip(),
        "openai_api_key": os.getenv("OPENAI_API_KEY", "").strip(),
        "app_env": os.getenv("APP_ENV", "dev").strip(),
    }


def has_any_llm_keys() -> bool:
    s = settings()
    return bool(
        s["groq_api_keys"]
        or s["gemini_api_keys"]
        or s["openrouter_api_keys"]
        or s["mistral_api_keys"]
        or s["xai_api_keys"]
    )
