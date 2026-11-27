"""The local UI shell: bundled styles, uploads, and the cost line."""

from pathlib import Path

from collection_qa.ui import estimate_line, parse_multipart, store_upload


def test_styles_are_bundled_and_use_the_purple_accent():
    root = Path("src/collection_qa/ui_static")
    css = (root / "app.css").read_text(encoding="utf-8")
    html = (root / "index.html").read_text(encoding="utf-8")
    assert "#8000ff" in css
    assert "Inter" in css
    assert "Times" not in css
    assert 'data-panel="collection"' in html
    assert "Pilot reports" in html
    report_js = (root / "report.js").read_text(encoding="utf-8")
    assert "Would they book?" in report_js
    assert "Can we trust it?" in report_js
    assert "Inputs used / missing" in report_js or "inputs used / missing" in report_js
    assert "cdn" not in (root / "charts.js").read_text(encoding="utf-8").lower()
    assert 'href="/static/app.css"' in html


def test_upload_lands_in_the_input_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    saved = store_upload("Harbour cruise", "screenshots", "deck.png", b"\x89PNG\r\n\x1a\nfake")
    assert saved["name"] == "deck.png"
    assert (tmp_path / "inputs" / "harbour-cruise" / "screenshots" / "deck.png").exists()
    text = (tmp_path / "inputs" / "harbour-cruise" / "inputs.yaml").read_text(encoding="utf-8")
    assert "screenshots/deck.png" in text
    assert saved["thumbnail"].startswith("data:image/png")


def test_saving_links_replaces_a_block_list(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from collection_qa.ui import save_links

    save_links("List cruise", {"competitor_urls": ["https://a.example"], "notes": "keep"})
    save_links("List cruise", {"competitor_urls": ["https://b.example"], "notes": "keep"})
    text = (tmp_path / "inputs" / "list-cruise" / "inputs.yaml").read_text(encoding="utf-8")
    assert text.count("https://a.example") == 0
    assert "https://b.example" in text
    import yaml
    yaml.safe_load(text)


def test_multipart_and_mock_cost_line():
    body = (
        b"--BOUND\r\n"
        b'Content-Disposition: form-data; name="query"\r\n\r\n'
        b"3945\r\n"
        b"--BOUND\r\n"
        b'Content-Disposition: form-data; name="file"; filename="page.csv"\r\n'
        b"Content-Type: text/csv\r\n\r\n"
        b"id,title\r\n"
        b"--BOUND--\r\n"
    )
    fields, files = parse_multipart(body, "multipart/form-data; boundary=BOUND")
    assert fields["query"] == "3945"
    assert files[0][1] == "page.csv"
    line = estimate_line(8, 3, True)
    assert "free" in line.lower()
    assert "$" in line
