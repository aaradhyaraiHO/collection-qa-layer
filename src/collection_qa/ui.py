"""Local collection-QA app. Standard library only.

Open http://127.0.0.1:8765 . Styles and scripts are files next to this module,
so the page works without a CDN.
"""

from __future__ import annotations

import json
import mimetypes
import threading
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from collection_qa.cost import estimate_cost, planned_calls
from collection_qa.headout_lookup import HeadoutLookup
from collection_qa.inputs import find_manifest, load_manifest, scaffold, slugify

STATIC = Path(__file__).resolve().parent / "ui_static"
RUNS: dict[str, dict] = {}
RUNS_LOCK = threading.Lock()


def lookup_payload(query: str, fetch) -> dict:
    resolved = HeadoutLookup(fetch).resolve(query)
    status = "LIVE" if resolved.page_live else ("IN_PIPELINE" if resolved.ce_id else "NOT_FOUND")
    note = " ".join(resolved.notes)
    manifest = find_manifest(query)
    if manifest and status == "NOT_FOUND":
        loaded = load_manifest(manifest)
        status = "IN_PIPELINE"
        note = "No live cards. A local input folder is ready."
        if not resolved.name or resolved.name == query:
            resolved.name = loaded.ce_name or query
        resolved.ce_id = resolved.ce_id or loaded.ce_id or None
    return {
        "name": resolved.name,
        "ce_id": resolved.ce_id,
        "status": status,
        "collection_url": resolved.collection_url,
        "product_count": len(resolved.products),
        "note": note,
    }


def estimate_line(personas: int, products: int, mock: bool) -> str:
    calls = planned_calls(
        n_personas=personas,
        n_products=max(products, 1),
        n_surfaces=1,
        gates={"A", "B"},
        completions=1,
    )
    cost = estimate_cost(model="claude-sonnet-5-5", calls=calls)
    if mock:
        return f"Mock mode is free. A live panel of this size would be about ${cost.usd:.2f} ({calls} reactions)."
    return f"About ${cost.usd:.2f} for {calls} Claude reactions at Sonnet rates. This is an estimate."


def save_links(query: str, form: dict) -> Path:
    folder = scaffold(query)
    manifest = folder / "inputs.yaml"
    text = manifest.read_text(encoding="utf-8")

    def put(field: str, value) -> None:
        nonlocal text
        if isinstance(value, list):
            rendered = "[" + ", ".join(_quote(item) for item in value) + "]" if value else "[]"
        else:
            rendered = _quote(value or "")
        text = _replace_field(text, field, rendered)

    put("eos_mmp_link", form.get("eos_mmp_link", ""))
    put("eos_assortment_link", form.get("eos_assortment_link", ""))
    put("eos_content_link", form.get("eos_content_link", ""))
    put("microbrand_url", form.get("microbrand_url", ""))
    put("notes", form.get("notes", ""))
    put("competitor_urls", form.get("competitor_urls") or [])
    put("slack_threads", form.get("slack_threads") or [])
    if str(query).strip().isdigit():
        put("ce_id", str(query).strip())
    else:
        put("ce_name", str(query).strip())
    manifest.write_text(text, encoding="utf-8")
    return folder


def store_upload(query: str, kind: str, filename: str, data: bytes) -> dict:
    if kind not in {"exports", "screenshots"}:
        raise ValueError("kind must be exports or screenshots")
    safe = Path(filename).name
    folder = scaffold(query)
    target = folder / kind / safe
    target.write_bytes(data)
    _append_list(folder / "inputs.yaml", kind, f"{kind}/{safe}")
    thumb = None
    if kind == "screenshots" and data[:8] == b"\x89PNG\r\n\x1a\n" or kind == "screenshots" and data[:2] == b"\xff\xd8":
        import base64

        media = "image/jpeg" if data[:2] == b"\xff\xd8" else "image/png"
        thumb = f"data:{media};base64,{base64.standard_b64encode(data).decode('ascii')}"
    return {"name": safe, "path": f"{kind}/{safe}", "thumbnail": thumb}


def _replace_field(text: str, field: str, rendered: str) -> str:
    lines = text.splitlines()
    out = []
    index = 0
    replaced = False
    while index < len(lines):
        line = lines[index]
        if line.startswith(f"{field}:"):
            out.append(f"{field}: {rendered}")
            replaced = True
            index += 1
            while index < len(lines) and lines[index].startswith(("  -", "\t-", "  ")):
                # Drop a previous block list under this key. Comments stay, they start with #.
                if lines[index].lstrip().startswith("#"):
                    break
                index += 1
            continue
        out.append(line)
        index += 1
    if not replaced:
        out.append(f"{field}: {rendered}")
    return "\n".join(out) + "\n"


def _append_list(path: Path, field: str, item: str) -> None:
    text = path.read_text(encoding="utf-8")
    # Read the current value, then write the field back as a flow list so block items are not duplicated.
    current: list[str] = []
    lines = text.splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith(f"{field}:"):
            inline = line.split(":", 1)[1].strip()
            if inline.startswith("[") and inline.endswith("]"):
                inner = inline[1:-1].strip()
                if inner:
                    current = [part.strip().strip('"') for part in inner.split(",") if part.strip()]
            index += 1
            while index < len(lines) and lines[index].startswith(("  -", "\t-")):
                current.append(lines[index].split("-", 1)[1].strip().strip('"'))
                index += 1
            break
        index += 1
    if item not in current:
        current.append(item)
    rendered = "[" + ", ".join(_quote(value) for value in current) + "]"
    path.write_text(_replace_field(text, field, rendered), encoding="utf-8")


def _quote(value: str) -> str:
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def pilot_index() -> list[dict]:
    folder = Path("reports/live")
    if not folder.exists():
        return []
    rows = []
    for path in sorted(folder.glob("*.json")):
        if ".panel." in path.name or path.name.endswith(".panel.json"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if "collection_name" not in payload or "collection_id" not in payload:
            continue
        rows.append(
            {
                "id": payload["collection_id"],
                "name": payload["collection_name"],
                "ce_id": payload.get("ce_id") or "",
            }
        )
    return rows


def history_rows() -> list[dict]:
    folder = Path("reports/checks")
    index = folder / "history.json"
    if index.exists():
        try:
            rows = json.loads(index.read_text(encoding="utf-8"))
            if isinstance(rows, list):
                return rows
        except json.JSONDecodeError:
            pass
    return []


def remember(row: dict) -> None:
    folder = Path("reports/checks")
    folder.mkdir(parents=True, exist_ok=True)
    rows = [item for item in history_rows() if item.get("html_name") != row.get("html_name")]
    rows.insert(0, row)
    (folder / "history.json").write_text(json.dumps(rows[:40], indent=2) + "\n", encoding="utf-8")


def parse_multipart(body: bytes, content_type: str) -> tuple[dict[str, str], list[tuple[str, str, bytes]]]:
    marker = "boundary="
    if marker not in content_type:
        return {}, []
    boundary = content_type.split(marker, 1)[1].strip().strip('"')
    fields: dict[str, str] = {}
    files: list[tuple[str, str, bytes]] = []
    for chunk in body.split(b"--" + boundary.encode()):
        if b"Content-Disposition" not in chunk:
            continue
        header, _, data = chunk.partition(b"\r\n\r\n")
        data = data.removesuffix(b"\r\n").removesuffix(b"--").removesuffix(b"\r\n")
        text = header.decode("utf-8", "replace")
        name = _disp(text, "name")
        filename = _disp(text, "filename")
        if not name:
            continue
        if filename:
            files.append((name, filename, data))
        else:
            fields[name] = data.decode("utf-8", "replace")
    return fields, files


def _disp(header: str, key: str) -> str:
    token = f'{key}="'
    if token not in header:
        return ""
    return header.split(token, 1)[1].split('"', 1)[0]


def _public_fetch(url: str) -> tuple[int, str]:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": "collection-qa"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return int(getattr(exc, "code", 0) or 0), str(exc)


def _start_run(payload: dict) -> str:
    run_id = uuid.uuid4().hex[:12]
    record = {"id": run_id, "events": [], "done": False, "error": "", "result": None}
    with RUNS_LOCK:
        RUNS[run_id] = record

    def progress(stage, detail, current=None, total=None):
        record["events"].append(
            {"stage": stage, "detail": detail, "current": current, "total": total}
        )

    def work():
        try:
            from collection_qa.check import run_check
            from collection_qa.report import write_report
            from collection_qa.slack_status import EnvSlackClient, SkippingSlack
            import os

            query = payload["query"]
            save_links(query, payload)
            progress("writing", "Saving what you entered")
            token = os.environ.get("SLACK_TOKEN", "")
            slack = EnvSlackClient(token) if token else SkippingSlack()
            report = run_check(
                query,
                fetch=_public_fetch,
                slack=slack,
                out="reports/checks",
                mock=bool(payload.get("mock", True)),
                personas=int(payload.get("personas") or 8),
                seed=7,
                prompt_fn=None,
                progress=progress,
            )
            progress("writing", "Writing the report")
            stem = f"{report['ce']['ce_id'] or 'ce'}-{slugify(report['ce']['name'])}"
            _json_path, _md_path, html_path = write_report(report, "reports/checks", stem)
            result = {
                "name": report["ce"]["name"],
                "verdict": report["verdict"],
                "when": report.get("status", ""),
                "html_name": html_path.name,
                "html_url": "/report/" + html_path.name,
                "inputs": report.get("inputs") or [],
                "view": report.get("view"),
            }
            remember({key: value for key, value in result.items() if key != "view"})
            record["result"] = result
        except Exception as exc:
            record["error"] = str(exc)
        finally:
            record["done"] = True

    threading.Thread(target=work, daemon=True).start()
    return run_id


def serve(port: int = 8765) -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path.startswith("/static/"):
                self._file(STATIC / parsed.path.split("/static/", 1)[1])
                return
            if parsed.path.startswith("/report/"):
                self._file(Path("reports/checks") / parsed.path.split("/report/", 1)[1])
                return
            if parsed.path == "/api/lookup":
                query = parse_qs(parsed.query).get("q", [""])[0]
                self._json(lookup_payload(query, _public_fetch))
                return
            if parsed.path == "/api/estimate":
                args = parse_qs(parsed.query)
                personas = int(args.get("personas", ["8"])[0] or 8)
                products = int(args.get("products", ["8"])[0] or 8)
                mock = args.get("mock", ["1"])[0] != "0"
                self._json({"line": estimate_line(personas, products, mock)})
                return
            if parsed.path == "/api/history":
                self._json(history_rows())
                return
            if parsed.path == "/api/pilots":
                self._json(pilot_index())
                return
            if parsed.path.startswith("/api/pilots/"):
                collection_id = parsed.path.split("/api/pilots/", 1)[1].strip("/")
                if not collection_id or "/" in collection_id or ".." in collection_id:
                    self.send_error(404)
                    return
                from collection_qa.executive import load_pilot

                try:
                    self._json(load_pilot(collection_id))
                except FileNotFoundError:
                    self.send_error(404)
                return
            if parsed.path.startswith("/api/runs/") and parsed.path.endswith("/events"):
                run_id = parsed.path.split("/")[3]
                self._events(run_id)
                return
            if parsed.path in {"/", "/index.html"}:
                self._file(STATIC / "index.html")
                return
            self.send_error(404)

        def do_POST(self):
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length)
            kind = self.headers.get("Content-Type", "")
            if self.path == "/api/upload":
                fields, files = parse_multipart(raw, kind)
                if not files:
                    self._json({"error": "no file"}, 400)
                    return
                _name, filename, data = files[0]
                saved = store_upload(fields.get("query") or "collection", fields.get("kind") or "exports", filename, data)
                self._json(saved)
                return
            if self.path == "/api/runs":
                payload = json.loads(raw.decode("utf-8") or "{}")
                if not str(payload.get("query") or "").strip():
                    self._json({"error": "CE name is required"}, 400)
                    return
                self._json({"id": _start_run(payload)})
                return
            self.send_error(404)

        def _events(self, run_id: str):
            record = RUNS.get(run_id)
            if record is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            sent = 0
            while True:
                events = record["events"][sent:]
                for event in events:
                    self.wfile.write(b"event: progress\n")
                    self.wfile.write(b"data: " + json.dumps(event).encode() + b"\n\n")
                    sent += 1
                if record["done"] and sent >= len(record["events"]):
                    payload = record["result"] or {"error": record["error"]}
                    self.wfile.write(b"event: done\n")
                    self.wfile.write(b"data: " + json.dumps(payload).encode() + b"\n\n")
                    break
                self.wfile.flush()
                import time
                time.sleep(0.2)

        def _json(self, payload, status: int = 200):
            data = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _file(self, path: Path):
            if not path.is_file():
                self.send_error(404)
                return
            data = path.read_bytes()
            media = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if path.suffix in {".html", ".css", ".js"}:
                media += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", media)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, fmt, *args):
            print(f"[ui] {self.address_string()} {fmt % args}")

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Collection QA at http://127.0.0.1:{port}")
    server.serve_forever()
