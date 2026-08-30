"""Phase 3 — Embedding: shared MiniLM encoder for ingest and query.

Model is fixed to ``sentence-transformers/all-MiniLM-L6-v2`` (architecture.md
Phase 3). One encoder class serves both the ingest path (chunk text) and the
query path (user question) so vectors live in the same space.

The model is loaded lazily on first use so importing this module is cheap and
the download happens exactly once.
"""

from __future__ import annotations

from typing import Sequence

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
_DIM = 384


class MiniLmEncoder:
    """Thin wrapper around the fixed MiniLM model (lazy-loaded)."""

    __slots__ = ("_model",)

    def __init__(self) -> None:
        self._model = None

    def _ensure(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(_MODEL_NAME)
        return self._model

    def encode_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed chunk/query texts. Returns a list of vectors aligned to input."""
        model = self._ensure()
        vectors = model.encode(
            list(texts),
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [vec.tolist() for vec in vectors]

    def encode_query(self, question: str) -> list[float]:
        """Embed a user question with the same model as ingest."""
        return self.encode_texts([question])[0]

    @property
    def dimension(self) -> int:
        return _DIM


# Module-level default that is cheap to import (model loads on first call).
_default: MiniLmEncoder | None = None


def default_encoder() -> MiniLmEncoder:
    global _default
    if _default is None:
        _default = MiniLmEncoder()
    return _default
