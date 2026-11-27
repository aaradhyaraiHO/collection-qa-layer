"""Per-CE input folder. Empty placeholders are skipped and shown as not provided.

Precedence when the same fact appears twice: a signed-in EOS fetch, then an
export file, then a screenshot reading, then the manual spreadsheet and notes.
A live headout.com card still wins for that product, because that is the page
a traveller books from.
"""

from __future__ import annotations

import base64
import csv
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from collection_qa.eos import EosDocument, EosParser, EosProduct, HeuristicEosAdapter

PLACEHOLDER_FIELDS = (
    "eos_mmp_link",
    "eos_assortment_link",
    "eos_content_link",
    "eos_exports",
    "screenshots",
    "microbrand_url",
    "competitor_urls",
    "slack_threads",
    "notes",
)

FIELD_HELP = {
    "eos_mmp_link": "Paste https://eos.headout.com/mmp/draft/<uuid>/<page>. The uuid is not the CE id. Do not use the search box; it can create a draft.",
    "eos_assortment_link": "Browser URL of the proposed-assortment screen for this CE. Leave blank to skip.",
    "eos_content_link": "Browser URL of the locked content screen. Leave blank to skip.",
    "eos_exports": "Files you saved from EOS (HTML, JSON, or CSV). Paths are relative to this folder, usually exports/page.html.",
    "screenshots": "PNG or JPG of the assortment or content page. Paths relative to this folder, usually screenshots/assortment.png.",
    "microbrand_url": "Attraction site if one exists (the standalone domain). Leave blank if you do not have one.",
    "competitor_urls": "GetYourGuide, Viator, or the operator's own page. One URL per line.",
    "slack_threads": "Links to the MMP or go-live thread. The tool lists them. It does not post.",
    "notes": "Anything the page does not say: price caveats, season, who to ask.",
}

SOURCE_RANK = {"manual": 1, "screenshot": 2, "eos_export": 3, "eos_live": 4, "headout": 5}


@dataclass
class InputManifest:
    folder: Path
    ce_name: str = ""
    ce_id: str = ""
    eos_mmp_link: str = ""
    eos_assortment_link: str = ""
    eos_content_link: str = ""
    eos_exports: list[str] = field(default_factory=list)
    screenshots: list[str] = field(default_factory=list)
    microbrand_url: str = ""
    competitor_urls: list[str] = field(default_factory=list)
    slack_threads: list[str] = field(default_factory=list)
    notes: str = ""

    def raw(self, name: str):
        return getattr(self, name)

    def is_empty(self, name: str) -> bool:
        value = self.raw(name)
        if value is None:
            return True
        if isinstance(value, str):
            return not value.strip() or value.strip().lower() in {"todo", "tbd", "placeholder"}
        if isinstance(value, list):
            return len([item for item in value if str(item).strip()]) == 0
        return False


def slugify(name: str) -> str:
    base = "".join(char.lower() if char.isalnum() else "-" for char in name).strip("-")
    while "--" in base:
        base = base.replace("--", "-")
    return base or "ce"


def scaffold(query: str, root: Path = Path("inputs")) -> Path:
    """Write inputs/<slug>/inputs.yaml plus empty templates. Existing files are kept."""
    folder = root / slugify(query)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "exports").mkdir(exist_ok=True)
    (folder / "screenshots").mkdir(exist_ok=True)
    manifest = folder / "inputs.yaml"
    if not manifest.exists():
        ce_id = query.strip() if query.strip().isdigit() else ""
        name = "" if ce_id else query.strip()
        manifest.write_text(_template(name, ce_id), encoding="utf-8")
    csv_path = folder / "assortment.csv"
    if not csv_path.exists():
        csv_path.write_text(
            "id,title,price,currency,duration,inclusions,cancellation,pickup,highlights\n",
            encoding="utf-8",
        )
    content = folder / "content.md"
    if not content.exists():
        content.write_text(_CONTENT_TEMPLATE, encoding="utf-8")
    return folder


def load_manifest(path: Path) -> InputManifest:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raw = {}
    folder = path.parent

    def text(name: str) -> str:
        value = raw.get(name) or ""
        return str(value).strip()

    def items(name: str) -> list[str]:
        value = raw.get(name) or []
        if isinstance(value, str):
            value = [value]
        return [str(item).strip() for item in value if str(item).strip()]

    return InputManifest(
        folder=folder,
        ce_name=text("ce_name"),
        ce_id=text("ce_id"),
        eos_mmp_link=text("eos_mmp_link"),
        eos_assortment_link=text("eos_assortment_link"),
        eos_content_link=text("eos_content_link"),
        eos_exports=items("eos_exports"),
        screenshots=items("screenshots"),
        microbrand_url=text("microbrand_url"),
        competitor_urls=items("competitor_urls"),
        slack_threads=items("slack_threads"),
        notes=text("notes"),
    )


def find_manifest(query: str, explicit: str | None = None, root: Path = Path("inputs")) -> Path | None:
    if explicit is not None:
        if not str(explicit).strip():
            return None
        path = Path(explicit)
        return path if path.is_file() else path / "inputs.yaml"
    if not root.exists():
        return None
    needle = query.strip().lower()
    slug = slugify(query)
    direct = root / slug / "inputs.yaml"
    if direct.exists():
        return direct
    for path in sorted(root.glob("*/inputs.yaml")):
        manifest = load_manifest(path)
        if needle and needle in {manifest.ce_id.lower(), manifest.ce_name.lower(), path.parent.name}:
            return path
    return None


class VisionExtractor:
    """Turns a screenshot into products and page copy. Tests pass a fake."""

    def extract(self, path: Path) -> dict:
        raise NotImplementedError


class SidecarVision(VisionExtractor):
    """Reads path.with_suffix('.json') if present. Used when Claude is not called."""

    def extract(self, path: Path) -> dict:
        sidecar = path.with_suffix(".json")
        if not sidecar.exists():
            return {
                "products": [],
                "confidence": "low",
                "please_verify": True,
                "note": f"No reading for {path.name}. Add a sidecar JSON or run without --mock so Claude can look at the image.",
            }
        payload = json.loads(sidecar.read_text(encoding="utf-8"))
        payload.setdefault("confidence", "low")
        payload.setdefault("please_verify", True)
        return payload


class ClaudeVision(VisionExtractor):
    """Claude image read. Not used in tests. The API key stays in the environment."""

    def __init__(self, model: str = "claude-sonnet-5-5"):
        self.model = model

    def extract(self, path: Path) -> dict:
        import anthropic

        media = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
        data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
        client = anthropic.Anthropic(timeout=90.0, max_retries=5)
        message = client.messages.create(
            model=self.model,
            max_tokens=1200,
            system=(
                "You extract a travel collection page from a screenshot. "
                "Reply with JSON only: {products:[{title,price,currency,duration,inclusions,cancellation,pickup}],"
                "hero_title,hero_copy,faqs:[{question,answer}],confidence}. "
                "confidence is high, medium, or low. Do not invent a price you cannot see."
            ),
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "source": {"type": "base64", "media_type": media, "data": data}},
                        {"type": "text", "text": "Extract the assortment and the visible page copy."},
                    ],
                }
            ],
        )
        text = "".join(block.text for block in message.content if getattr(block, "type", None) == "text")
        start, end = text.find("{"), text.rfind("}")
        payload = json.loads(text[start : end + 1]) if start >= 0 else {"products": []}
        payload["please_verify"] = True
        payload["confidence"] = payload.get("confidence") or "low"
        return payload


def manual_document(folder: Path, parser: EosParser | None = None) -> EosDocument | None:
    parser = parser or HeuristicEosAdapter()
    csv_path = folder / "assortment.csv"
    content_path = folder / "content.md"
    products: list[EosProduct] = []
    if csv_path.exists():
        parsed = parser.parse(csv_path.read_text(encoding="utf-8"), str(csv_path))
        products = [item for item in parsed.products if item.title and item.title.lower() != "untitled"]
        if csv_path.read_text(encoding="utf-8").count("\n") <= 1:
            products = []
    hero_title, hero_copy, faqs = _read_content(content_path)
    if not products and not hero_title and not hero_copy and not faqs:
        return None
    return EosDocument(
        source=str(folder / "assortment.csv"),
        stage=None,
        content_locked=bool(faqs or hero_copy),
        hero_title=hero_title,
        hero_copy=hero_copy,
        faqs=faqs,
        products=products,
        notes=["Filled in by hand from assortment.csv and content.md."],
        parser_name="manual",
    )


def _read_content(path: Path) -> tuple[str | None, str | None, list[tuple[str, str]]]:
    if not path.exists():
        return None, None, []
    text = path.read_text(encoding="utf-8").strip()
    if not text or text == _CONTENT_TEMPLATE.strip():
        return None, None, []
    title = None
    hero = []
    faqs: list[tuple[str, str]] = []
    mode = None
    question = None
    answer: list[str] = []
    for line in text.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            mode = None
            continue
        if line.startswith("## "):
            if question and answer:
                faqs.append((question, " ".join(answer).strip()))
            question, answer = None, []
            heading = line[3:].strip().lower()
            mode = "hero" if "hero" in heading else "faq" if "faq" in heading else None
            continue
        if mode == "faq" and line.startswith("### "):
            if question and answer:
                faqs.append((question, " ".join(answer).strip()))
            question = line[4:].strip()
            answer = []
            continue
        if mode == "hero" and line.strip():
            hero.append(line.strip())
        elif mode == "faq" and question and line.strip():
            answer.append(line.strip())
    if question and answer:
        faqs.append((question, " ".join(answer).strip()))
    copy = " ".join(hero).strip() or None
    return title, copy, faqs


def document_from_screenshot(payload: dict, source: str) -> EosDocument:
    products = []
    for index, raw in enumerate(payload.get("products") or []):
        if not isinstance(raw, dict) or not raw.get("title"):
            continue
        inclusions = raw.get("inclusions") or []
        products.append(
            EosProduct(
                id=str(raw.get("id") or f"shot-{index + 1}"),
                title=str(raw["title"]),
                price=_num(raw.get("price")),
                currency=raw.get("currency"),
                duration=raw.get("duration"),
                inclusions=[str(item) for item in inclusions] if isinstance(inclusions, list) else [],
                highlights=[str(item) for item in raw.get("highlights") or []],
                cancellation=raw.get("cancellation"),
                pickup=raw.get("pickup"),
            )
        )
    faqs = []
    for item in payload.get("faqs") or []:
        if isinstance(item, dict) and item.get("question"):
            faqs.append((str(item["question"]), str(item.get("answer") or "")))
    return EosDocument(
        source=source,
        stage=None,
        content_locked=bool(payload.get("hero_copy") or faqs),
        hero_title=payload.get("hero_title"),
        hero_copy=payload.get("hero_copy"),
        faqs=faqs,
        products=products,
        notes=[
            f"Screenshot reading confidence: {payload.get('confidence') or 'low'}. Please verify.",
            payload.get("note") or "",
        ],
        parser_name="screenshot",
    )


def ledger_rows(manifest: InputManifest | None, field_sources: dict[str, str]) -> list[dict]:
    rows = []
    if manifest is None:
        rows.append(
            {
                "field": "inputs.yaml",
                "status": "not provided",
                "source": "",
                "detail": "No inputs/<ce>/inputs.yaml was found. Run collection-qa init.",
            }
        )
        return rows
    for name in PLACEHOLDER_FIELDS:
        empty = manifest.is_empty(name)
        rows.append(
            {
                "field": name,
                "status": "not provided" if empty else "provided",
                "source": "" if empty else "inputs.yaml",
                "detail": FIELD_HELP[name] if empty else _short(manifest.raw(name)),
            }
        )
    for field_name, source in field_sources.items():
        rows.append(
            {
                "field": field_name,
                "status": "used" if source != "not provided" else "not provided",
                "source": "" if source == "not provided" else source,
                "detail": "Which layer supplied this part of the spec.",
            }
        )
    return rows


def _short(value) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def _num(value):
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"[0-9]+(?:\.[0-9]+)?", value.replace(",", ""))
        return float(match.group(0)) if match else None
    return None


@dataclass
class MergedInputs:
    document: EosDocument | None
    field_sources: dict[str, str]
    please_verify: list[str]
    competitors: list[str]
    slack_threads: list[str]
    microbrand_url: str
    notes: str


def _product_dict(product: EosProduct) -> dict:
    return {
        "id": product.id,
        "title": product.title,
        "price": product.price,
        "currency": product.currency,
        "duration": product.duration,
        "inclusions": list(product.inclusions),
        "highlights": list(product.highlights),
        "cancellation": product.cancellation,
        "pickup": product.pickup,
        "url": product.url,
    }


def merge_layers(layers: list[tuple[str, EosDocument]]) -> tuple[EosDocument | None, dict[str, str], list[str]]:
    """layers are lowest precedence first. Later layers overwrite non-empty fields."""
    if not layers:
        return None, {"products": "not provided", "hero_title": "not provided", "hero_copy": "not provided", "faqs": "not provided"}, []
    by_title: dict[str, dict] = {}
    product_source: dict[str, str] = {}
    hero_title = hero_copy = None
    hero_title_source = hero_copy_source = faq_source = "not provided"
    faqs: list[tuple[str, str]] = []
    content_locked = False
    stage = None
    notes: list[str] = []
    verify: list[str] = []
    source_name = "manual"
    for source, document in layers:
        source_name = source
        notes.extend(note for note in document.notes if note)
        if document.content_locked:
            content_locked = True
        if document.stage:
            stage = document.stage
        if document.hero_title:
            hero_title = document.hero_title
            hero_title_source = source
        if document.hero_copy:
            hero_copy = document.hero_copy
            hero_copy_source = source
        if document.faqs:
            faqs = document.faqs
            faq_source = source
        for product in document.products:
            key = product.title.strip().lower()
            current = by_title.get(key, {})
            incoming = _product_dict(product)
            for field_name, value in incoming.items():
                if value not in (None, "", []):
                    current[field_name] = value
                    product_source[f"{key}:{field_name}"] = source
                    if source == "screenshot" and field_name == "title":
                        verify.append(str(value))
            if key not in by_title:
                current.setdefault("title", product.title)
            by_title[key] = current
    products = []
    for index, raw in enumerate(by_title.values()):
        products.append(
            EosProduct(
                id=str(raw.get("id") or f"merged-{index + 1}"),
                title=str(raw.get("title") or "Untitled"),
                price=raw.get("price"),
                currency=raw.get("currency"),
                duration=raw.get("duration"),
                inclusions=raw.get("inclusions") or [],
                highlights=raw.get("highlights") or [],
                cancellation=raw.get("cancellation"),
                pickup=raw.get("pickup"),
                url=raw.get("url"),
            )
        )
    field_sources = {
        "products": source_name if products else "not provided",
        "hero_title": hero_title_source,
        "hero_copy": hero_copy_source,
        "faqs": faq_source,
    }
    # Product-level source is the highest layer that set the title.
    if products:
        origins = {product_source.get(f"{product.title.strip().lower()}:title", source_name) for product in products}
        field_sources["products"] = ", ".join(sorted(origins))
    document = EosDocument(
        source="merged",
        stage=stage,
        content_locked=content_locked,
        hero_title=hero_title,
        hero_copy=hero_copy,
        faqs=faqs,
        products=products,
        notes=notes,
        parser_name="merged",
    )
    return document, field_sources, verify


def collect_layers(
    manifest: InputManifest,
    *,
    parser: EosParser | None = None,
    vision: VisionExtractor | None = None,
    eos_live: EosDocument | None = None,
) -> list[tuple[str, EosDocument]]:
    parser = parser or HeuristicEosAdapter()
    vision = vision or SidecarVision()
    layers: list[tuple[str, EosDocument]] = []
    manual = manual_document(manifest.folder, parser)
    if manual and (manual.products or manual.hero_title or manual.hero_copy or manual.faqs):
        layers.append(("manual", manual))
    for relative in manifest.screenshots:
        path = _resolve(manifest.folder, relative)
        if not path.exists():
            continue
        payload = vision.extract(path)
        layers.append(("screenshot", document_from_screenshot(payload, str(path))))
    for relative in manifest.eos_exports:
        path = _resolve(manifest.folder, relative)
        if not path.exists():
            continue
        layers.append(("eos_export", parser.parse(path.read_text(encoding="utf-8"), str(path))))
    if eos_live and (eos_live.products or eos_live.hero_title or eos_live.hero_copy):
        layers.append(("eos_live", eos_live))
    return layers


def _resolve(folder: Path, relative: str) -> Path:
    path = Path(relative)
    return path if path.is_absolute() else folder / path


def _template(name: str, ce_id: str) -> str:
    lines = [
        "# What to put in this file. Empty means the report says not provided.",
        f"ce_name: {json.dumps(name)}",
        f"ce_id: {json.dumps(ce_id)}  # numeric Headout collection / CE id, if you know it",
        "",
    ]
    for name_key, help_text in FIELD_HELP.items():
        lines.append(f"# {help_text}")
        if name_key in {"eos_exports", "screenshots", "competitor_urls", "slack_threads"}:
            lines.append(f"{name_key}: []")
        else:
            lines.append(f"{name_key}: \"\"")
        lines.append("")
    return "\n".join(lines)


_CONTENT_TEMPLATE = """# Page title

Replace this heading with the collection title. Delete this sentence.

## Hero

Write the sentence under the title. What the trip is, in plain words.

## FAQs

### Can I cancel?

Say the cutoff.

### How do I get there?

Pickup, drive, or meet point.

### Is there wheelchair access?

What you know. If you do not know, delete the question.
"""
