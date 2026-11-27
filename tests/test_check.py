"""CE lookup, Slack stage, EOS parse, and the check report. No network and no model."""

import json
from pathlib import Path

from collection_qa.check import run_check
from collection_qa.eos import HeuristicEosAdapter, eos_login, read_eos_export
from collection_qa.report import write_report
from collection_qa.slack_status import SlackHit, combine_status, infer_stage, summarize_slack

FIXTURES = Path("tests/fixtures/check")


class ScriptedSlack:
    def __init__(self, hits):
        self.hits = hits

    def search(self, query: str):
        return self.hits


def _fetch(cards: bool):
    collection = (FIXTURES / "collection.json").read_text(encoding="utf-8")
    card_body = (FIXTURES / "cards.json").read_text(encoding="utf-8") if cards else '{"result":{"productCards":{"items":[]}}}'

    def fetch(url: str) -> tuple[int, str]:
        if "product-cards" in url:
            return 200, card_body
        if "/collections/3945" in url:
            return 200, collection
        if "search" in url:
            return 200, "https://www.headout.com/milford-sound-cruise-tickets-c-3945/"
        return 404, "missing"

    return fetch


def test_stage_keywords_pick_the_most_advanced():
    hits = [
        SlackHit("Assortment is in proposed assortment"),
        SlackHit("Content lock done, waiting on BOQA"),
    ]
    assert infer_stage(hits) == "boqa"
    status, stage = combine_status(
        page_live=False,
        collection_found=True,
        slack=summarize_slack(ScriptedSlack(hits), ce_id="3945", name="Milford"),
    )
    assert status == "IN_PIPELINE"
    assert stage == "boqa"
    live, _stage = combine_status(
        page_live=True,
        collection_found=True,
        slack=summarize_slack(ScriptedSlack(hits), ce_id="3945", name="Milford"),
    )
    assert live == "LIVE"


def test_live_collection_writes_html_without_eos(tmp_path):
    report = run_check(
        "3945",
        fetch=_fetch(cards=True),
        slack=ScriptedSlack([]),
        out=tmp_path,
        mock=True,
        personas=4,
        seed=7,
        prompt_fn=lambda _prompt: "",
        inputs_path="",
    )
    assert report["status"] == "LIVE"
    assert report["gates"] == ["A", "B"]
    assert report["verdict"] in {"Go", "Fix first"}
    assert report["products"]
    assert report["mock"] is True
    json_path, md_path, html_path = write_report(report, tmp_path, "milford")
    html = html_path.read_text(encoding="utf-8")
    assert "<svg" in html
    assert report["verdict"] in html
    assert "Can we trust it" in html
    assert "Fix table" in md_path.read_text(encoding="utf-8")
    saved = json.loads(json_path.read_text(encoding="utf-8"))
    assert saved["ce"]["ce_id"] == "3945"


def test_pipeline_uses_eos_export_and_slack(tmp_path):
    report = run_check(
        "3945",
        fetch=_fetch(cards=False),
        slack=ScriptedSlack([SlackHit("MMP content lock is done for CE 3945")]),
        out=tmp_path,
        mock=True,
        personas=4,
        seed=3,
        eos_export=str(FIXTURES / "eos_export.json"),
        prompt_fn=lambda _prompt: "",
        inputs_path="",
    )
    assert report["status"] == "IN_PIPELINE"
    assert "B" in report["gates"]
    assert report["verdict"] == "Fix first"
    assert any(row["priority"] == "P0" for row in report["fixes"])
    assert any(row["owner"] for row in report["fixes"])
    assert "unconfirmed" in " ".join(report["appendix"]["eos_notes"]).lower()


def test_missing_ce_holds_without_asking_the_model(tmp_path):
    def fetch(_url: str) -> tuple[int, str]:
        return 404, "no"

    report = run_check(
        "not a real collection",
        fetch=fetch,
        slack=ScriptedSlack([]),
        out=tmp_path,
        mock=True,
        personas=2,
        prompt_fn=lambda _prompt: "",
        inputs_path="",
    )
    assert report["status"] == "NOT_FOUND"
    assert report["verdict"] == "Hold"
    assert report["products"] == []


def test_eos_html_and_json_adapters_extract_the_draft():
    html_doc = read_eos_export(str(FIXTURES / "eos_page.html"))
    assert html_doc.products[0].title == "Draft day cruise"
    assert html_doc.products[0].price == 149
    assert html_doc.products[0].currency == "NZD"
    assert html_doc.content_locked is True
    assert html_doc.hero_title == "Milford Sound draft"
    json_doc = HeuristicEosAdapter().parse((FIXTURES / "eos_export.json").read_text(encoding="utf-8"), "mem")
    assert json_doc.content_locked is True
    assert json_doc.faqs
    assert json_doc.products[0].inclusions == ["Tea"]


def test_eos_login_delegates_to_the_injected_browser(tmp_path):
    seen = {}

    def launcher(profile, url, *, headless, wait_for_enter):
        seen["profile"] = profile
        seen["url"] = url
        seen["headless"] = headless
        seen["wait"] = wait_for_enter
        return "<html></html>"

    path = eos_login(profile_dir=tmp_path / "eos-profile", start_url="https://eos.headout.com/", launcher=launcher)
    assert path == tmp_path / "eos-profile"
    assert seen["headless"] is False
    assert seen["wait"] is True
    assert "eos.headout.com" in seen["url"]
