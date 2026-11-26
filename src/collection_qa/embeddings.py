"""Embedding backends.

Live runs use a local sentence-transformers model (no embedding API key).
Tests and `--mock` runs default to a lexical bag-of-words embedder so they do
not download weights. The lexical embedder is not a substitute for a semantic
model: mock scorecards say so.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

DEFAULT_ST_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an array of shape (len(texts), dim)."""


def _tokenize(text: str) -> list[str]:
    cleaned = []
    word = []
    for ch in text.lower():
        if ch.isalpha():
            word.append(ch)
        else:
            if word:
                cleaned.append("".join(word))
                word = []
    if word:
        cleaned.append("".join(word))
    stop = {
        "a",
        "an",
        "the",
        "and",
        "or",
        "to",
        "of",
        "for",
        "my",
        "me",
        "i",
        "it",
        "is",
        "am",
        "be",
        "this",
        "that",
        "with",
        "on",
        "in",
        "at",
    }
    return [token for token in cleaned if token not in stop and len(token) > 1]


class LexicalEmbedder:
    """Binary bag-of-words over a frozen vocabulary, L2-normalized.

    The vocabulary should include the anchor statements so purchase-intent
    wording lands on shared dimensions. Unknown tokens are ignored.
    """

    name = "lexical-bow"

    def __init__(self, vocabulary_texts: list[str]):
        vocab: list[str] = []
        seen: set[str] = set()
        for text in vocabulary_texts:
            for token in _tokenize(text):
                if token not in seen:
                    seen.add(token)
                    vocab.append(token)
        if not vocab:
            raise ValueError("lexical embedder needs a non-empty vocabulary")
        self.vocab = vocab
        self.index = {token: i for i, token in enumerate(vocab)}

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), len(self.vocab)), dtype=float)
        for row, text in enumerate(texts):
            for token in _tokenize(text):
                idx = self.index.get(token)
                if idx is not None:
                    matrix[row, idx] = 1.0
            norm = np.linalg.norm(matrix[row])
            if norm > 0:
                matrix[row] /= norm
        return matrix


class HashEmbedder:
    """Feature-hashing bag-of-words. Deterministic, no vocabulary fit.

    Useful as a smoke backend. It does not preserve synonym similarity.
    """

    name = "hash-bow"

    def __init__(self, dim: int = 256):
        self.dim = dim

    def embed(self, texts: list[str]) -> np.ndarray:
        matrix = np.zeros((len(texts), self.dim), dtype=float)
        for row, text in enumerate(texts):
            for token in _tokenize(text):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                matrix[row, int.from_bytes(digest[:4], "little") % self.dim] += 1.0
            norm = np.linalg.norm(matrix[row])
            if norm > 0:
                matrix[row] /= norm
        return matrix


class SentenceTransformerEmbedder:
    """Local open-source embeddings via sentence-transformers."""

    def __init__(self, model_name: str = DEFAULT_ST_MODEL):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers is not installed. "
                "Install the embeddings extra: pip install 'collection-qa[embeddings]'"
            ) from exc
        self.model_name = model_name
        self.name = f"sentence-transformers:{model_name}"
        self._model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> np.ndarray:
        vectors = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return np.asarray(vectors, dtype=float)


def build_embedder(kind: str, *, model_name: str, vocabulary_texts: list[str]) -> Embedder:
    if kind == "lexical":
        return LexicalEmbedder(vocabulary_texts)
    if kind == "hash":
        return HashEmbedder()
    if kind == "sentence-transformers":
        return SentenceTransformerEmbedder(model_name)
    raise ValueError(f"unknown embedder {kind!r}")
