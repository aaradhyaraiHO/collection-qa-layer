"""Semantic similarity rating (SSR).

Implements the mapping in arXiv 2510.08338, appendix equations for the Likert pmf:

    p(r) ∝ γ(σ_r, t) − γ(σ_ℓ, t) + ε δ_{ℓ, r}

γ is cosine similarity, ℓ is a least-similar anchor in the set, and the main
experiments in the paper fix ε = 0 and temperature T = 1. Temperature sharpens
or smears the pmf as p(r, T) ∝ p(r) ** (1/T). Per-set pmfs are averaged.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def similarities_to_pmf(
    similarities: np.ndarray,
    *,
    epsilon: float = 0.0,
    temperature: float = 1.0,
) -> np.ndarray:
    """Map five cosine similarities (index 0 = rating 1) to a pmf.

    ε is added to every anchor tied for the minimum similarity. T = 1 leaves
    the subtracted-min weights unchanged. A non-positive temperature is rejected.
    """
    sims = np.asarray(similarities, dtype=float).reshape(-1)
    if sims.shape != (5,):
        raise ValueError("SSR expects exactly 5 anchor similarities")
    if temperature <= 0:
        raise ValueError("SSR temperature must be positive")
    if epsilon < 0:
        raise ValueError("SSR epsilon must be non-negative")

    minimum = float(sims.min())
    least = np.isclose(sims, minimum)
    weights = sims - minimum
    if epsilon:
        weights = weights + epsilon * least.astype(float)
    weights = np.clip(weights, 0.0, None)
    if temperature != 1.0:
        weights = np.power(weights, 1.0 / temperature)
    total = float(weights.sum())
    if total <= 0.0:
        return np.full(5, 1.0 / 5.0)
    return weights / total


def mean_rating(pmf: np.ndarray) -> float:
    probs = np.asarray(pmf, dtype=float)
    if probs.shape != (5,):
        raise ValueError("pmf must have 5 bins")
    return float(np.dot(np.arange(1, 6), probs))


def average_pmfs(pmfs: list[np.ndarray]) -> np.ndarray:
    if not pmfs:
        raise ValueError("no pmfs to average")
    stacked = np.stack([np.asarray(p, dtype=float) for p in pmfs], axis=0)
    return stacked.mean(axis=0)


@dataclass(frozen=True)
class SSRResult:
    pmf: np.ndarray
    mean: float
    per_set: dict[str, np.ndarray]

    def as_dict(self) -> dict[str, float]:
        return {str(i + 1): float(self.pmf[i]) for i in range(5)}


def rate_embedding(
    response: np.ndarray,
    anchor_matrix: dict[str, np.ndarray],
    *,
    epsilon: float = 0.0,
    temperature: float = 1.0,
) -> SSRResult:
    """Score one response embedding against each anchor set, then average.

    anchor_matrix values are arrays of shape (5, dim), row 0 = rating 1.
    """
    per_set: dict[str, np.ndarray] = {}
    for set_id, matrix in anchor_matrix.items():
        sims = np.array([cosine(response, matrix[i]) for i in range(5)])
        per_set[set_id] = similarities_to_pmf(sims, epsilon=epsilon, temperature=temperature)
    pmf = average_pmfs(list(per_set.values()))
    return SSRResult(pmf=pmf, mean=mean_rating(pmf), per_set=per_set)
