import json
from pathlib import Path

import pytest

from collection_qa.cli import main
from collection_qa.models import load_spec
from collection_qa.pipeline import RunConfig, run_collection


def test_mock_run_writes_labeled_scorecard(tmp_path: Path):
    spec = load_spec("tests/fixtures/tiny.yaml")
    payload = run_collection(
        spec,
        RunConfig(
            mock=True,
            n_personas=12,
            seed=4,
            concurrency=4,
            cache_path=str(tmp_path / "cache.sqlite"),
            embedder="lexical",
            gates={"A", "B"},
        ),
    )
    assert payload["mock"] is True
    assert payload["banner"] and "MOCK" in payload["banner"]
    assert payload["method"]["llm_calls_made"] > 0
    assert payload["cost"]["usd"] > 0
    assert "No API call was made" in payload["cost"]["note"]

    cheap = payload["products"]["cheap-cruise"]["overall"]
    luxury = payload["products"]["luxury-fly"]["overall"]
    for block in (cheap, luxury):
        assert abs(sum(block["pmf"].values()) - 1) < 1e-6
        assert block["n"] == 12
    # Budget-heavy fjord prior should prefer the cheap cruise over the fly option.
    assert cheap["mean"] > luxury["mean"]

    budget = payload["products"]["cheap-cruise"]["by_segment"]["budget_tier"]["budget"]["mean"]
    luxury_for_budget = payload["products"]["luxury-fly"]["by_segment"]["budget_tier"]["budget"]["mean"]
    assert budget > luxury_for_budget

    quotes = payload["quotes"]
    assert quotes
    assert all(quote["generator"] == "mock-template" for quote in quotes)
    assert all(not quote["text"].strip()[:1].isdigit() for quote in quotes)

    out = tmp_path / "reports"
    code = main(
        [
            "run",
            "tests/fixtures/tiny.yaml",
            "--mock",
            "--personas",
            "6",
            "--seed",
            "4",
            "--out",
            str(out),
            "--cache",
            str(tmp_path / "cli.sqlite"),
            "--embedder",
            "lexical",
        ]
    )
    assert code == 0
    written = json.loads((out / "tiny-fjord.json").read_text())
    markdown = (out / "tiny-fjord.md").read_text()
    assert written["mock"] is True
    assert "MOCK OUTPUT" in markdown
    assert "Gate results" in markdown


def test_second_run_uses_the_cache(tmp_path: Path):
    spec = load_spec("tests/fixtures/tiny.yaml")
    config = RunConfig(
        mock=True,
        n_personas=4,
        seed=2,
        cache_path=str(tmp_path / "cache.sqlite"),
        embedder="lexical",
    )
    first = run_collection(spec, config)
    second = run_collection(spec, config)
    assert first["method"]["cache_hits"] == 0
    assert second["method"]["cache_hits"] == second["method"]["llm_calls_made"] + second["method"]["cache_hits"]
    assert second["method"]["llm_calls_made"] == 0
    assert second["method"]["cache_hits"] > 0


def test_cli_refuses_a_live_run_without_a_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    code = main(["run", "tests/fixtures/tiny.yaml", "--personas", "1"])
    assert code == 2


def test_estimate_prints_a_total(capsys: pytest.CaptureFixture[str]):
    code = main(["estimate", "tests/fixtures/tiny.yaml", "--personas", "10", "--completions", "2"])
    assert code == 0
    captured = capsys.readouterr().out
    assert "calls" in captured
    assert "USD" in captured
