from pathlib import Path

from collection_qa.models import load_spec
from collection_qa.runner import run_collection

ROOT = Path(__file__).resolve().parents[1]


def test_mock_run_writes_scorecard_and_keeps_distributions(tmp_path):
    spec = load_spec(ROOT / "tests/fixtures/tiny_collection.yaml")
    scorecard = run_collection(
        spec,
        n_personas=4,
        seed=3,
        dry_run=True,
        embedder_kind="hash",
        completions=2,
        out_dir=tmp_path,
    )
    assert scorecard["meta"]["mode"] == "MOCK"
    assert "MOCK" in scorecard["banner"]
    assert scorecard["meta"]["cost"]["actual_usd"] == 0
    assert scorecard["meta"]["cost"]["estimated_usd"] > 0
    assert (tmp_path / "tiny-safari.scorecard.json").exists()
    assert (tmp_path / "tiny-safari.scorecard.md").exists()
    markdown = (tmp_path / "tiny-safari.scorecard.md").read_text(encoding="utf-8")
    assert markdown.startswith("# MOCK scorecard")
    for row in scorecard["gate_a"]["products"]:
        total = sum(row["distribution"].values())
        assert abs(total - 1) < 1e-3
        assert 1 <= row["mean_pi"] <= 5
    page = scorecard["gate_b"]["page"]
    assert page["mean_pi"] is not None
    assert abs(sum(page["distribution"].values()) - 1) < 1e-3
    assert scorecard["quotes"]
    # Planted price fail blocks Gate A or B.
    assert scorecard["gate_a"]["status"] == "fail" or scorecard["gate_b"]["status"] == "fail"


def test_personas_change_the_ranking_and_ablation_flattens_it():
    spec = load_spec(ROOT / "tests/fixtures/tiny_collection.yaml")
    conditioned = run_collection(spec, n_personas=6, seed=5, dry_run=True, embedder_kind="hash", gate="A")
    means = {row["product_id"]: row["mean_pi"] for row in conditioned["gate_a"]["products"]}
    assert means["cheap"] > means["dear"]
    ablated = run_collection(
        spec,
        n_personas=6,
        seed=5,
        dry_run=True,
        embedder_kind="hash",
        gate="A",
        ablate_personas=True,
    )
    ablated_means = {row["product_id"]: row["mean_pi"] for row in ablated["gate_a"]["products"]}
    assert abs(ablated_means["cheap"] - ablated_means["dear"]) < abs(means["cheap"] - means["dear"])


def test_cli_dry_run(tmp_path):
    from collection_qa.cli import main

    code = main(
        [
            "run",
            str(ROOT / "tests/fixtures/tiny_collection.yaml"),
            "--dry-run",
            "--personas",
            "2",
            "--embedder",
            "hash",
            "--out",
            str(tmp_path),
            "--max-products",
            "2",
        ]
    )
    assert code == 0
    assert (tmp_path / "tiny-safari.scorecard.json").exists()
