import numpy as np

from collection_qa.anchors import ANCHOR_SETS
from collection_qa.embeddings import LexicalEmbedder
from collection_qa.ssr import cosine, mean_rating, pmf_as_dict, pmf_for_anchor_set, ssr_pmf


def _orthogonal_anchors() -> np.ndarray:
    return np.eye(5)


def test_cosine_of_parallel_vectors_is_one():
    vector = np.array([1.0, 2.0, 3.0])
    assert cosine(vector, vector * 4) == 1.0


def test_zero_vector_is_not_a_rating():
    pmf = pmf_for_anchor_set(np.zeros(5), _orthogonal_anchors())
    assert np.allclose(pmf, np.full(5, 0.2))


def test_minimum_subtraction_puts_zero_mass_on_the_least_similar_anchor():
    response = np.array([0.0, 0.0, 0.0, 0.2, 1.0])
    pmf = pmf_for_anchor_set(response, _orthogonal_anchors(), epsilon=0.0, temperature=1.0)
    assert pmf.sum() == 1.0
    assert pmf[0] == 0.0
    assert pmf[4] == max(pmf)


def test_epsilon_gives_the_least_similar_anchor_some_mass():
    response = np.array([0.0, 0.0, 0.0, 0.2, 1.0])
    pmf = pmf_for_anchor_set(response, _orthogonal_anchors(), epsilon=0.1, temperature=1.0)
    assert pmf[0] > 0
    assert np.isclose(pmf.sum(), 1.0)


def test_temperature_flattens_when_raised():
    response = np.array([0.0, 0.1, 0.2, 0.4, 1.0])
    sharp = pmf_for_anchor_set(response, _orthogonal_anchors(), temperature=0.5)
    flat = pmf_for_anchor_set(response, _orthogonal_anchors(), temperature=2.0)
    assert sharp.max() > flat.max()


def test_identical_similarities_become_uniform_when_epsilon_is_zero():
    response = np.ones(5)
    anchors = np.vstack([response, response, response, response, response])
    pmf = pmf_for_anchor_set(response, anchors, epsilon=0.0)
    assert np.allclose(pmf, np.full(5, 0.2))


def test_ssr_averages_anchor_sets():
    response = np.array([1.0, 0.0])
    set_a = np.array([[1.0, 0.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0]])
    set_b = np.array([[0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [0.0, 1.0], [1.0, 0.0]])
    averaged = ssr_pmf(response, [set_a, set_b], epsilon=0.0, temperature=1.0)
    only_a = pmf_for_anchor_set(response, set_a)
    only_b = pmf_for_anchor_set(response, set_b)
    assert np.allclose(averaged, (only_a + only_b) / 2)
    assert np.isclose(averaged.sum(), 1.0)


def test_mean_rating_of_a_point_mass():
    assert mean_rating(np.array([0, 0, 0, 0, 1], dtype=float)) == 5
    assert mean_rating(np.full(5, 0.2)) == 3


def test_pmf_dict_uses_likert_labels():
    encoded = pmf_as_dict(np.array([0.0, 0.0, 0.0, 0.0, 1.0]))
    assert set(encoded) == {"1", "2", "3", "4", "5"}
    assert encoded["5"] == 1


def test_lexical_embedder_ranks_anchor_language():
    texts = [statement for group in ANCHOR_SETS for statement in group]
    embedder = LexicalEmbedder(texts)
    anchors = [embedder.embed(group) for group in ANCHOR_SETS]
    low = ssr_pmf(embedder.embed([ANCHOR_SETS[0][0]])[0], anchors)
    high = ssr_pmf(embedder.embed([ANCHOR_SETS[0][4]])[0], anchors)
    assert mean_rating(high) > mean_rating(low)
    assert mean_rating(high) > 3.5
    # Point-1 and point-5 anchors still share booking words, so the low
    # statement does not collapse to a pure 1. Direction is what matters.
    assert mean_rating(low) < 3.5
