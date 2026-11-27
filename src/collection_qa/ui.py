"""A small local form. No extra packages.

Open http://127.0.0.1:8765 , type a CE name, paste links, and optionally give
file paths that already sit in the input folder. Run writes the HTML report.
"""

from __future__ import annotations

import html
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from collection_qa.inputs import find_manifest, scaffold

PAGE = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Collection QA</title>
<style>
body { font-family: Georgia, serif; max-width: 720px; margin: 2rem auto; }
label { display: block; margin-top: 0.8rem; }
input, textarea { width: 100%; }
button { margin-top: 1rem; padding: 0.5rem 1rem; }
</style></head><body>
<h1>Check a collection</h1>
<p>Paste what you have. Leave a box empty if you do not have it. The report will say not provided.</p>
<form method="post" action="/run">
<label>CE name or id <input name="query" required></label>
<label>EOS MMP link <input name="eos_mmp_link" placeholder="https://eos.headout.com/mmp/draft/..."></label>
<label>EOS assortment link <input name="eos_assortment_link"></label>
<label>EOS content link <input name="eos_content_link"></label>
<label>Microbrand URL <input name="microbrand_url"></label>
<label>Competitor URLs, one per line <textarea name="competitor_urls" rows="3"></textarea></label>
<label>Slack thread links, one per line <textarea name="slack_threads" rows="2"></textarea></label>
<label>Notes <textarea name="notes" rows="3"></textarea></label>
<label><input type="checkbox" name="mock" value="1" checked> Mock reactions (no Claude spend)</label>
<button type="submit">Run</button>
</form>
<p>Drop exports and screenshots into the folder this creates under inputs/, then run again. Paths in inputs.yaml are picked up automatically.</p>
</body></html>
"""


def _form(body: bytes) -> dict[str, str]:
    parsed = urllib.parse.parse_qs(body.decode("utf-8"), keep_blank_values=True)
    return {key: values[0] for key, values in parsed.items()}


def _write_links(query: str, form: dict[str, str]) -> Path:
    folder = scaffold(query)
    manifest = find_manifest(query, root=Path("inputs"))
    assert manifest is not None
    text = manifest.read_text(encoding="utf-8")

    def put(field: str, value: str) -> None:
        nonlocal text
        lines = []
        replaced = False
        for line in text.splitlines():
            if line.startswith(f"{field}:"):
                rendered = "[]" if value == "[]" else json_string(value) if not value.startswith("[") else value
                if field in {"competitor_urls", "slack_threads"} and value and not value.startswith("["):
                    items = [part.strip() for part in value.splitlines() if part.strip()]
                    rendered = "[" + ", ".join(json_string(item) for item in items) + "]" if items else "[]"
                lines.append(f"{field}: {rendered}")
                replaced = True
            else:
                lines.append(line)
        if not replaced:
            lines.append(f"{field}: {json_string(value)}")
        text = "\n".join(lines) + "\n"

    put("eos_mmp_link", form.get("eos_mmp_link", "").strip())
    put("eos_assortment_link", form.get("eos_assortment_link", "").strip())
    put("eos_content_link", form.get("eos_content_link", "").strip())
    put("microbrand_url", form.get("microbrand_url", "").strip())
    put("competitor_urls", form.get("competitor_urls", "").strip())
    put("slack_threads", form.get("slack_threads", "").strip())
    put("notes", form.get("notes", "").strip())
    if form.get("query") and not form["query"].strip().isdigit():
        put("ce_name", form["query"].strip())
    elif form.get("query", "").strip().isdigit():
        put("ce_id", form["query"].strip())
    manifest.write_text(text, encoding="utf-8")
    return folder


def json_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def serve(port: int = 8765) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/report/"):
                target = Path("reports/checks") / self.path.split("/report/", 1)[1]
                if target.is_file():
                    data = target.read_bytes()
                    kind = "text/html" if target.suffix == ".html" else "text/plain"
                    self.send_response(200)
                    self.send_header("Content-Type", f"{kind}; charset=utf-8")
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            body = PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            form = _form(self.rfile.read(length))
            query = form.get("query", "").strip()
            if not query:
                self.send_error(400, "CE name is required")
                return
            _write_links(query, form)
            from collection_qa.cli import main

            code = main(
                [
                    "check",
                    query,
                    "--out",
                    "reports/checks",
                    "--no-prompt",
                    "--personas",
                    "8",
                    "--seed",
                    "7",
                ]
                + (["--mock"] if form.get("mock") else [])
            )
            message = "The check finished." if code == 0 else f"The check exited with status {code}."
            link = ""
            folder = Path("reports/checks")
            if folder.exists():
                html_files = sorted(folder.glob("*.check.html"), key=lambda path: path.stat().st_mtime, reverse=True)
                if html_files:
                    link = f'<p><a href="/report/{html.escape(html_files[0].name)}">Open the HTML report</a></p>'
            body = f"<!DOCTYPE html><html><body><p>{html.escape(message)}</p>{link}<p><a href='/'>Back</a></p></body></html>"
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, fmt, *args):
            print(f"[ui] {self.address_string()} {fmt % args}")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Collection QA form at http://127.0.0.1:{port}")
    server.serve_forever()
