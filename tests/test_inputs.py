"""Input folder, merge order, and screenshot readings. No Claude calls."""

from pathlib import Path

from collection_qa.check import run_check
from collection_qa.eos import EosDocument, EosProduct
from collection_qa.inputs import collect_layers, merge_layers, scaffold
from collection_qa.report import render_html, render_markdown


class FixedVision:
    def extract(self, path: Path) -> dict:
        return {
            "confidence": "low",
            "please_verify": True,
            "hero_title": "From the screenshot",
            "products": [
                {
                    "title": "Day cruise",
                    "price": 10,
                    "currency": "NZD",
                    "duration": "2 hours",
                    "inclusions": ["Tea"],
                }
            ],
        }


def test_init_writes_documented_placeholders(tmp_path):
    folder = scaffold("A new fjord", root=tmp_path)
    text = (folder / "inputs.yaml").read_text(encoding="utf-8")
    assert "eos_mmp_link" in text
    assert "Leave blank" in text
    assert (folder / "assortment.csv").exists()
    assert (folder / "content.md").exists()
    assert "screenshots" in text


def test_export_beats_screenshot_and_manual(tmp_path):
    folder = scaffold("Sample cruise", root=tmp_path)
    (folder / "assortment.csv").write_text(
        "id,title,price,currency,duration,inclusions,cancellation,pickup,highlights\n"
        "m1,Day cruise,50,NZD,2 hours,Tea,Free cancellation,Terminal,\n",
        encoding="utf-8",
    )
    (folder / "content.md").write_text("# Manual title\n\n## Hero\n\nManual copy.\n", encoding="utf-8")
    shot = folder / "screenshots" / "page.png"
    shot.parent.mkdir(exist_ok=True)
    shot.write_bytes(b"not-a-real-png")
    export = folder / "exports" / "page.json"
    export.write_text(
        '{"contentLocked": true, "content": {"heroTitle": "Export title", "heroCopy": "Export copy."},'
        '"assortment": [{"id": "e1", "title": "Day cruise", "price": 155, "currency": "NZD", "duration": "2 hours"}]}',
        encoding="utf-8",
    )
    text = (folder / "inputs.yaml").read_text(encoding="utf-8")
    text = text.replace("eos_exports: []", 'eos_exports:\n  - "exports/page.json"')
    text = text.replace("screenshots: []", 'screenshots:\n  - "screenshots/page.png"')
    (folder / "inputs.yaml").write_text(text, encoding="utf-8")
    from collection_qa.inputs import load_manifest

    manifest = load_manifest(folder / "inputs.yaml")
    layers = collect_layers(manifest, vision=FixedVision())
    merged, sources, verify = merge_layers(layers)
    assert merged is not None
    assert merged.products[0].price == 155
    assert merged.hero_title == "Export title"
    assert sources["hero_title"] == "eos_export"
    assert "Day cruise" in verify
    live = EosDocument(
        source="browser",
        stage="content_locked",
        content_locked=True,
        hero_title="Live EOS title",
        hero_copy="Live copy",
        faqs=[],
        products=[EosProduct(id="live", title="Day cruise", price=160, currency="NZD", duration="2 hours")],
        parser_name="live",
    )
    layers.append(("eos_live", live))
    merged, sources, _verify = merge_layers(layers)
    assert merged.products[0].price == 160
    assert sources["hero_title"] == "eos_live"


def test_check_manual_folder_says_what_was_missing(tmp_path):
    folder = scaffold("Offline fjord", root=tmp_path)
    (folder / "assortment.csv").write_text(
        "id,title,price,currency,duration,inclusions,cancellation,pickup,highlights\n"
        "a,Short cruise,99,NZD,2 hours,Tea,Free cancellation up to 24 hours,Meet at the dock,Deck\n",
        encoding="utf-8",
    )
    (folder / "content.md").write_text(
        "# Offline fjord\n\n## Hero\n\nA short cruise.\n\n## FAQs\n\n### Can I cancel?\n\nYes, 24 hours before.\n",
        encoding="utf-8",
    )

    def fetch(_url: str):
        return 404, "no"

    report = run_check(
        "Offline fjord",
        fetch=fetch,
        slack=type("S", (), {"search": lambda self, query: []})(),
        out=tmp_path,
        mock=True,
        personas=3,
        seed=1,
        inputs_path=str(folder / "inputs.yaml"),
        prompt_fn=lambda _prompt: "",
    )
    assert report["status"] == "IN_PIPELINE"
    assert report["products"]
    missing = [row["field"] for row in report["inputs"] if row["status"] == "not provided"]
    assert "eos_mmp_link" in missing
    assert "screenshots" in missing
    text = render_markdown(report)
    html = render_html(report)
    assert "Inputs used / missing" in text
    assert "not provided" in text
    assert "Inputs used / missing" in html
    assert "eos_mmp_link" in html
