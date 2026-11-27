"""The in-app report is built from a scorecard, including the live pilots."""

import json
from pathlib import Path

from collection_qa.executive import build_view, load_pilot, panel_from_segment_means, write_panel_file


def test_milford_view_has_the_seven_parts():
    view = load_pilot("milford-sound-cruises")
    assert view["title"] == "Milford Sound cruises"
    assert view["verdict"] in {"Go", "Fix first", "Hold"}
    assert view["likely_to_book"]
    shares = view["likely_to_book"][0]["pmf"]
    assert abs(sum(shares) - 1) < 0.02
    assert view["quotes"]
    assert view["ranking"][0]["mean"] >= view["ranking"][-1]["mean"]
    assert view["fixes"]
    assert {"priority", "issue", "page_link", "what_to_change", "owner", "quote"} <= set(view["fixes"][0])
    assert view["heatmap"]["rows"]
    assert any(cell["faded"] for row in view["heatmap"]["rows"] for cell in row["cells"])
    assert any(dot["faded"] for dot in view["dots"])
    assert view["detail"]["prices"]
    assert view["detail"]["checks"]["warn"] > 0
    assert view["trust"]["points"]
    assert view["trust"]["label"] in {"ROBUST", "WEIGHT-SENSITIVE"}
    assert view["appendix"]["pages"]
    assert any(row["status"] == "not provided" for row in view["appendix"]["inputs"])


def test_mara_pilot_and_panel_file(tmp_path):
    view = load_pilot("masai-mara")
    assert view["ce_id"] == "7324"
    assert view["detail"]["microbrand"]["bars"]
    scorecard = json.loads(Path("reports/live/masai-mara.json").read_text(encoding="utf-8"))
    rows = panel_from_segment_means(scorecard)
    assert len(rows) == 30
    assert rows[0]["scores"]
    written = write_panel_file(Path("reports/live/milford-sound-cruises.json"))
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["panel_scores"]
    assert "not a second Claude run" in payload["provenance"]
    # The heatmap does not depend on those reconstructed rows.
    again = build_view(scorecard)
    assert again["heatmap"]["rows"]
