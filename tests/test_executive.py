"""The in-app report reads the regenerated live panel, not a synthetic roster."""

from pathlib import Path

from collection_qa.executive import load_pilot


def test_milford_uses_the_real_panel_and_the_80_mix():
    view = load_pilot("milford-sound-cruises")
    assert view["title"] == "Milford Sound cruises"
    assert view["likely_to_book"]
    assert abs(sum(view["likely_to_book"][0]["pmf"]) - 1) < 0.02
    assert view["heatmap"]["rows"]
    assert any(cell["faded"] for row in view["heatmap"]["rows"] for cell in row["cells"])
    couple = next(row for row in view["heatmap"]["rows"] if row["label"] == "couple")
    assert couple["cells"][0]["n"] >= 8
    assert not couple["cells"][0]["faded"]
    trust = view["trust"]
    assert trust["page_low"] == 3.26
    assert trust["page_high"] == 3.36
    assert {row["label"] for row in trust["dimensions"]} >= {
        "budget tier",
        "planning horizon",
        "source market",
        "trip type",
    }
    details = {item["label"]: item["detail"] for item in trust["highlights"]}
    assert details["Top 3 held"] == "74%"
    assert details["Flyover stays weak"] == "99%"
    assert "segment means" not in trust["note"].lower()
    assert "not a second" not in trust["note"].lower()
    assert not list(Path("reports/live").glob("*.panel.json"))


def test_mara_rank_hold_rates_come_from_the_real_mix():
    view = load_pilot("masai-mara")
    details = {item["label"]: item["detail"] for item in view["trust"]["highlights"]}
    assert details["Top 3 held"] == "78%"
    assert details["Bottom 3 held"] == "52%"
    assert len(view["trust"]["dimensions"]) == 4
