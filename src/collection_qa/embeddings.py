"""Text embedders.

The default model is a local sentence-transformers checkpoint. No second API key.
Tests and `--embedder hash` use a deterministic lexicon embedder so SSR still
separates booking intent without downloading weights. That hash embedder is not
the method in the paper.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

from collection_qa.anchors import INTENT_CUES


class Embedder(Protocol):
    name: str

    def encode(self, texts: list[str]) -> np.ndarray: ...


def _cue_rating(text: str) -> int | None:
    lowered = text.lower()
    # Walk ratings from most negative so "would not book" wins over "would book".
    for rating in (1, 2, 3, 4, 5):
        for cue in INTENT_CUES[rating]:
            if cue in lowered:
                return rating
    return None


class HashEmbedder:
    """Lexicon dimensions plus a small hashed bag.

    Cue dimensions dominate, so texts that use the anchor cues land near the
    matching Likert anchor. The hash keeps two texts in the same bucket from
    being identical vectors.
    """

    def __init__(self, dim: int = 32):
        self.dim = dim
        self.name = f"hash-lexicon-{dim}"

    def encode(self, texts: list[str]) -> np.ndarray:
        rows = np.zeros((len(texts), self.dim), dtype=float)
        for index, text in enumerate(texts):
            rating = _cue_rating(text)
            if rating is not None:
                rows[index, rating - 1] = 8.0
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            for slot in range(5, self.dim):
                rows[index, slot] = ((digest[slot % len(digest)] / 255.0) - 0.5) * 0.15
        return rows


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self.name = model_name
        self._model = None

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=False,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=float)


def build_embedder(kind: str, model_name: str) -> Embedder:
    if kind == "hash":
        return HashEmbedder()
    if kind == "sentence-transformers":
        return SentenceTransformerEmbedder(model_name)
    raise ValueError(f"unknown embedder '{kind}'")
