"""Semantic Similarity Rating, following arXiv 2510.08338 equations 8-9.

For a free-text reaction t and one anchor set {sigma_r}:

    gamma(sigma_r, t) = cosine(v_sigma_r, v_t)

    p(r) proportional to gamma(sigma_r, t) - gamma(sigma_ell, t) + epsilon * 1[r = ell]

where ell is the least-similar anchor in the set. Subtracting the minimum is
required because unrelated sentences still sit near each other in embedding
space. With epsilon = 0, the least-similar point gets zero mass.

Temperature (paper): p(r, T) proportional to p(r) ** (1 / T).
Main-text experiments used epsilon = 0 and T = 1, then averaged the pmfs
across reference sets.
"""

from __future__ import annotations

import numpy as np

from collection_qa.anchors import DEFAULT_EPSILON, DEFAULT_TEMPERATURE, LIKERT_POINTS

LIKERT = np.array(LIKERT_POINTS, dtype=float)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = np.linalg.norm(a)
    nb = np.linalg.norm(b)
    if na == 0.0 or nb == 0.0:
        return float("nan")
    return float(np.dot(a, b) / (na * nb))


def pmf_for_anchor_set(
    response: np.ndarray,
    anchors: np.ndarray,
    *,
    epsilon: float = DEFAULT_EPSILON,
    temperature: float = DEFAULT_TEMPERATURE,
) -> np.ndarray:
    """Map one response embedding to a 5-point pmf for a single anchor set.

    `anchors` has shape (5, dim). Returns a probability vector of length 5.
    A zero response vector, or a zero anchor, yields a uniform pmf.
    """
    if anchors.shape[0] != 5:
        raise ValueError(f"expected 5 anchors, got {anchors.shape[0]}")
    if temperature <= 0:
        raise ValueError("temperature must be positive")

    sims = np.array([cosine(response, anchors[i]) for i in range(5)], dtype=float)
    if not np.all(np.isfinite(sims)):
        return np.full(5, 1.0 / 5.0)

    ell = int(np.argmin(sims))
    shifted = sims - sims[ell]
    shifted[ell] += epsilon
    shifted = np.maximum(shifted, 0.0)

    if temperature != 1.0:
        # 0 ** positive = 0. Avoid 0 ** negative, which cannot happen for T > 0
        # unless 1/T is negative (it is not).
        shifted = np.power(shifted, 1.0 / temperature)

    total = float(shifted.sum())
    if total <= 0.0:
        return np.full(5, 1.0 / 5.0)
    return shifted / total


def average_pmfs(pmfs: list[np.ndarray] | np.ndarray) -> np.ndarray:
    stacked = np.vstack(pmfs)
    return stacked.mean(axis=0)


def ssr_pmf(
    response: np.ndarray,
    anchor_sets: list[np.ndarray] | np.ndarray,
    *,
    epsilon: float = DEFAULT_EPSILON,
    temperature: float = DEFAULT_TEMPERATURE,
) -> np.ndarray:
    """Average per-set pmfs. `anchor_sets` is a sequence of (5, dim) arrays."""
    pmfs = [
        pmf_for_anchor_set(response, anchors, epsilon=epsilon, temperature=temperature)
        for anchors in anchor_sets
    ]
    return average_pmfs(pmfs)


def mean_rating(pmf: np.ndarray) -> float:
    pmf = np.asarray(pmf, dtype=float)
    if pmf.shape != (5,):
        raise ValueError(f"pmf must have shape (5,), got {pmf.shape}")
    return float(np.dot(pmf, LIKERT))


def pmf_as_dict(pmf: np.ndarray) -> dict[str, float]:
    return {str(point): float(pmf[point - 1]) for point in LIKERT_POINTS}
