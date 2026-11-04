"""Conftest for backend tests."""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_APP = Path(__file__).resolve().parent.parent / "app"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
