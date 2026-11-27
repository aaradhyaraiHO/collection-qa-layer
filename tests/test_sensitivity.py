"""Reweighting math and robustness verdicts. No model calls."""

import json

import pytest

from collection_qa.cli import main
from collection_qa.sensitivity import (
    additional_personas,
    analyze_panel,
    analyze_scorecard,
    importance_ratio,
    kendall_tau,
    shift_axis,
    spearman,
    weighted_mean,
)


def test_shift_moves_one_level_and_renormalizes_the_rest():
    moved = shift_axis({"solo": 0.25, "couple": 0.25, "family_with_kids": 0.25, "friends": 0.25}, "solo", 0.20)
    assert moved is not None
    assert abs(sum(moved.values()) - 1) < 1e-9
    assert abs(moved["solo"] - 0.45) < 1e-9
    assert abs(moved["couple"] - 0.55 / 3) < 1e-9
    assert shift_axis({"solo": 0.0, "couple": 1.0}, "solo", -0.20) is None


def test_importance_ratio_is_one_when_the_mix_does_not_change():
    weights = {"budget_tier": {"budget": 0.5, "luxury": 0.5}}
    attributes = {"budget_tier": "budget"}
    assert importance_ratio(attributes, weights, weights) == 1
    richer = {"budget_tier": {"budget": 0.7, "luxury": 0.3}}
    assert abs(importance_ratio(attributes, weights, richer) - 1.4) < 1e-9


def test_weighted_mean_recovers_a_group_when_only_that_group_is_kept():
    assert weighted_mean([5, 5, 1, 1], [1, 1, 0, 0]) == 5
    assert weighted_mean([4, 4, 4], [1, 1, 1]) == 4


def test_rank_correlations():
    assert kendall_tau(["a", "b", "c"], ["a", "b", "c"]) == 1
    assert kendall_tau(["a", "b", "c"], ["c", "b", "a"]) == -1
    assert spearman(["a", "b", "c"], ["a", "b", "c"]) == 1
    assert spearman(["a", "b", "c"], ["c", "b", "a"]) == pytest.approx(-1)


def test_additional_sample_reaches_the_target_cell():
    # 15 / 0.15 = 100 total draws. A panel of 30 still needs 70.
    assert additional_personas(30, 0.15, 15) == 70
    assert additional_personas(100, 0.15, 15) == 0


def _panel():
    rows = []
    for index in range(6):
        rows.append(
            {
                "persona_id": f"b{index}",
                "attributes": {
                    "budget_tier": "budget",
                    "trip_type": "solo",
                    "source_market": "United States",
                    "planning_horizon": "weeks_1_4",
                },
                "scores": {"A": {"mean": 5}, "B": {"mean": 1}, "page:primary": {"mean": 4}},
            }
        )
    for index in range(6):
        rows.append(
            {
                "persona_id": f"l{index}",
                "attributes": {
                    "budget_tier": "luxury",
                    "trip_type": "solo",
                    "source_market": "United States",
                    "planning_horizon": "weeks_1_4",
                },
                "scores": {"A": {"mean": 1}, "B": {"mean": 5}, "page:primary": {"mean": 2}},
            }
        )
    return rows


def test_reweight_moves_the_blend_and_leaves_segment_ranks_robust():
    weights = {
        "budget_tier": {"budget": 0.5, "luxury": 0.5},
        "trip_type": {"solo": 1.0},
        "source_market": {"United States": 1.0},
        "planning_horizon": {"weeks_1_4": 1.0},
    }
    result = analyze_panel(
        _panel(),
        weights,
        product_ids=["A", "B"],
        page_ids=["page:primary"],
        titles={"A": "Cheap", "B": "Luxury"},
        base_issues=[],
        shift=0.20,
        n_dirichlet=10,
        concentration=30,
        seed=7,
        min_cell=4,
        target_cell=15,
    )
    assert result["status"] == "ok"
    assert result["base_page_means"]["page:primary"] == 3
    budget_up = next(row for row in result["page_level"])
    assert result["page_level"]["page:primary"]["scenario_max"] > 3
    assert result["page_level"]["page:primary"]["scenario_min"] < 3
    segment = next(item for item in result["findings"] if item["kind"] == "segment_rank")
    assert segment["verdict"] == "ROBUST"
    assert segment["hold_rate"] == 1
    assert any(flag["n"] < 4 for flag in result["small_cells"]) or result["small_cells"] == []
    # trip type has a single level with 12 personas, above min_cell 4.
    # source market too. planning horizon too. budget has 6 and 6, above 4.
    assert result["small_cells"] == []
    assert budget_up


def test_small_cell_tells_you_how_many_more_personas_to_draw():
    rows = _panel()[:1]
    weights = {
        "budget_tier": {"budget": 0.15, "luxury": 0.85},
        "trip_type": {"solo": 1},
        "source_market": {"United States": 1},
        "planning_horizon": {"weeks_1_4": 1},
    }
    # One budget persona only. The luxury level is empty.
    rows[0]["attributes"]["budget_tier"] = "budget"
    result = analyze_panel(
        rows,
        weights,
        product_ids=["A", "B"],
        page_ids=["page:primary"],
        titles={"A": "A", "B": "B"},
        base_issues=[],
        shift=0.20,
        n_dirichlet=0,
        seed=1,
        min_cell=8,
        target_cell=15,
    )
    luxury = next(flag for flag in result["small_cells"] if flag["level"] == "luxury")
    assert luxury["n"] == 0
    assert luxury["additional_personas"] == additional_personas(1, 0.85, 15)


def test_missing_panel_scores_do_not_invent_a_reweight(tmp_path):
    scorecard = {"collection_id": "tiny-fjord", "method": {"seed": 7, "n_personas": 30}}
    path = tmp_path / "run.json"
    path.write_text(json.dumps(scorecard), encoding="utf-8")
    out = tmp_path / "out"
    code = main(
        [
            "sensitivity",
            "tests/fixtures/tiny.yaml",
            "--from-run",
            str(path),
            "--out",
            str(out),
        ]
    )
    assert code == 3
    written = json.loads((out / "tiny-fjord.sensitivity.json").read_text())
    assert written["status"] == "missing_panel_scores"
    assert "panel_scores" in written["message"]
    assert "max_tokens 320" in written["message"]
    report = analyze_scorecard(scorecard)
    assert report["original_system_prompt"].startswith("You are taking part")
