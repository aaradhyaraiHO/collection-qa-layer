import numpy as np

from collection_qa.ssr import average_pmfs, mean_rating, similarities_to_pmf


def test_subtract_min_and_mean():
    # Hand example: min similarity is dropped, remaining weights become the pmf.
    sims = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
    pmf = similarities_to_pmf(sims, epsilon=0.0, temperature=1.0)
    expected = np.array([0.0, 0.1, 0.2, 0.3, 0.4])
    np.testing.assert_allclose(pmf, expected)
    assert abs(pmf.sum() - 1) < 1e-12
    assert mean_rating(pmf) == 4.0


def test_epsilon_puts_mass_on_the_minimum():
    sims = np.array([0.5, 0.6, 0.7, 0.8, 0.9])
    pmf = similarities_to_pmf(sims, epsilon=0.1, temperature=1.0)
    assert pmf[0] > 0
    np.testing.assert_allclose(pmf.sum(), 1.0)


def test_tied_minimum_both_receive_epsilon():
    sims = np.array([0.2, 0.2, 0.5, 0.6, 0.7])
    pmf = similarities_to_pmf(sims, epsilon=0.1, temperature=1.0)
    assert pmf[0] > 0 and pmf[1] > 0
    assert abs(pmf[0] - pmf[1]) < 1e-12


def test_temperature_sharpens_the_top_bin():
    sims = np.array([0.50, 0.55, 0.60, 0.70, 0.90])
    flat = similarities_to_pmf(sims, temperature=1.0)
    sharp = similarities_to_pmf(sims, temperature=0.5)
    assert sharp.argmax() == 4
    assert sharp[4] > flat[4]


def test_zero_weights_fall_back_to_uniform():
    pmf = similarities_to_pmf(np.array([0.4, 0.4, 0.4, 0.4, 0.4]))
    np.testing.assert_allclose(pmf, np.full(5, 0.2))


def test_average_across_anchor_sets_stays_a_pmf():
    left = np.array([0.0, 0.0, 0.0, 0.2, 0.8])
    right = np.array([0.5, 0.2, 0.1, 0.1, 0.1])
    averaged = average_pmfs([left, right])
    np.testing.assert_allclose(averaged.sum(), 1.0)
    np.testing.assert_allclose(averaged, (left + right) / 2)


def test_cosine_of_identical_anchor_peaks_that_rating():
    from collection_qa.embeddings import HashEmbedder
    from collection_qa.anchors import iter_anchors
    from collection_qa.ssr import rate_embedding

    embedder = HashEmbedder()
    rows = iter_anchors()
    vectors = embedder.encode([text for _, _, text in rows])
    grouped: dict[str, list] = {}
    for (set_id, _rating, _text), vector in zip(rows, vectors):
        grouped.setdefault(set_id, []).append(vector)
    matrix = {set_id: np.stack(vs, axis=0) for set_id, vs in grouped.items()}
    response = embedder.encode(["I would book this for the two of us."])[0]
    result = rate_embedding(response, matrix)
    assert result.pmf.argmax() == 4
    assert result.mean > 4.5
