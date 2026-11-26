"""Fetch and parse an EOS MMP page with the user's own browser session.

EOS is behind the user's Headout sign-in. This module never stores a password.
`collection-qa eos-login` opens a headed Chromium with a persistent profile
directory. Later fetches reuse that profile. The directory is local and gitignored.

The DOM of eos.headout.com was not available when this parser was written.
Selectors and JSON keys below are an adapter contract, not a confirmed map.
Replace `HeuristicEosAdapter` once someone checks them in a signed-in session.
"""

from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Protocol

DEFAULT_PROFILE = Path.home() / ".collection-qa" / "eos-profile"
DEFAULT_EOS_URL = "https://eos.headout.com/"

UNCONFIRMED_SELECTORS = """
Unconfirmed against a signed-in EOS page. Treat parses as best-effort until
someone verifies these in the browser and updates HeuristicEosAdapter.

HTML, guessed:
- stage: [data-testid="mmp-stage"], [data-stage]
- assortment card: [data-testid="assortment-card"], article.assortment-card
- title: h3, .product-title, [data-field="title"]
- price: [data-field="price"], .price
- duration: [data-field="duration"]
- inclusions: .inclusions li
- hero: h1, [data-field="hero-title"]
- hero copy: [data-field="hero-copy"]
- FAQ: .faq-item, details
- content lock: [data-content-locked], text "content locked"

JSON keys, guessed: stage, contentLocked, assortment, products, tourGroups,
content.heroTitle, content.heroCopy, content.faqs, content.highlights.
CSV columns, guessed: id, title, price, currency, duration, inclusions.
""".strip()


@dataclass
class EosProduct:
    id: str
    title: str
    price: float | None = None
    currency: str | None = None
    duration: str | None = None
    inclusions: list[str] = field(default_factory=list)
    highlights: list[str] = field(default_factory=list)
    cancellation: str | None = None
    pickup: str | None = None
    url: str | None = None


@dataclass
class EosDocument:
    source: str
    stage: str | None
    content_locked: bool
    hero_title: str | None
    hero_copy: str | None
    faqs: list[tuple[str, str]]
    products: list[EosProduct]
    notes: list[str] = field(default_factory=list)
    parser_name: str = "heuristic"


class EosParser(Protocol):
    name: str

    def parse(self, document: str, source: str) -> EosDocument:
        """Turn an export or a saved page into assortment and content fields."""


class _CardParser(HTMLParser):
    """Pulls a small set of guessed attributes. Misses are recorded, not invented."""

    def __init__(self):
        super().__init__()
        self.stage: str | None = None
        self.content_locked = False
        self.hero_title: str | None = None
        self.hero_copy: str | None = None
        self.faqs: list[tuple[str, str]] = []
        self.products: list[dict] = []
        self._capture: str | None = None
        self._current: dict | None = None
        self._faq_q: str | None = None
        self._buffer: list[str] = []

    def handle_starttag(self, tag, attrs):
        data = {key: value for key, value in attrs}
        testid = data.get("data-testid", "")
        field_name = data.get("data-field", "")
        if data.get("data-stage"):
            self.stage = data["data-stage"]
        if data.get("data-content-locked", "").lower() in {"true", "1", "yes"}:
            self.content_locked = True
        if testid == "mmp-stage" or field_name == "stage":
            self._capture = "stage"
        elif testid == "assortment-card" or "assortment-card" in data.get("class", ""):
            self._current = {"inclusions": [], "highlights": []}
            self.products.append(self._current)
        elif field_name == "title" or tag == "h3":
            self._capture = "title"
        elif field_name == "price" or "price" in data.get("class", ""):
            self._capture = "price"
        elif field_name == "duration":
            self._capture = "duration"
        elif field_name in {"hero-title"} or tag == "h1":
            self._capture = "hero"
        elif field_name == "hero-copy":
            self._capture = "hero_copy"
        elif "faq-item" in data.get("class", "") or tag == "details":
            self._capture = "faq"
        elif tag == "li" and self._current is not None and "inclusion" in data.get("class", ""):
            self._capture = "inclusion"
        self._buffer = []

    def handle_data(self, data):
        if data and data.strip():
            self._buffer.append(data.strip())
            if "content locked" in data.lower() or "content lock" in data.lower():
                self.content_locked = True

    def handle_endtag(self, tag):
        text = " ".join(self._buffer).strip()
        self._buffer = []
        if not text or not self._capture:
            return
        if self._capture == "stage":
            self.stage = text
        elif self._capture == "title" and self._current is not None:
            self._current["title"] = text
        elif self._capture == "price" and self._current is not None:
            self._current["price_text"] = text
        elif self._capture == "duration" and self._current is not None:
            self._current["duration"] = text
        elif self._capture == "hero":
            self.hero_title = text
        elif self._capture == "hero_copy":
            self.hero_copy = text
        elif self._capture == "inclusion" and self._current is not None:
            self._current["inclusions"].append(text)
        elif self._capture == "faq":
            if self._faq_q is None:
                self._faq_q = text
            else:
                self.faqs.append((self._faq_q, text))
                self._faq_q = None
        self._capture = None


def _price_from_text(text: str) -> tuple[float | None, str | None]:
    match = re.search(r"([A-Z]{3})?\s*([0-9]+(?:\.[0-9]+)?)", text.replace(",", ""))
    if not match:
        return None, None
    currency = match.group(1)
    return float(match.group(2)), currency


class HeuristicEosAdapter:
    """JSON, CSV, then guessed HTML. name is the adapter id stored on the parse."""

    name = "heuristic"

    def parse(self, document: str, source: str) -> EosDocument:
        stripped = document.strip()
        if not stripped:
            return EosDocument(
                source=source,
                stage=None,
                content_locked=False,
                hero_title=None,
                hero_copy=None,
                faqs=[],
                products=[],
                notes=["EOS export was empty."],
                parser_name=self.name,
            )
        if stripped[0] in "{[":
            try:
                return self._from_json(json.loads(stripped), source)
            except json.JSONDecodeError:
                pass
        if stripped.lower().startswith("id,") or "title,price" in stripped.lower().splitlines()[0]:
            return self._from_csv(stripped, source)
        return self._from_html(stripped, source)

    def _from_json(self, payload, source: str) -> EosDocument:
        if isinstance(payload, list):
            payload = {"assortment": payload}
        if not isinstance(payload, dict):
            return self._empty(source, "JSON root was not an object or a product list.")
        content = payload.get("content") if isinstance(payload.get("content"), dict) else {}
        stage = payload.get("stage") or payload.get("mmpStage")
        if isinstance(payload.get("mmp"), dict):
            stage = stage or payload["mmp"].get("stage")
        locked = bool(
            payload.get("contentLocked")
            or payload.get("content_locked")
            or content.get("locked")
            or (isinstance(stage, str) and "content" in stage.lower() and "lock" in stage.lower())
        )
        raw_products = (
            payload.get("assortment")
            or payload.get("products")
            or payload.get("tourGroups")
            or content.get("products")
            or []
        )
        products = []
        notes = [
            "JSON keys are unconfirmed against EOS. See collection_qa.eos.UNCONFIRMED_SELECTORS."
        ]
        if not isinstance(raw_products, list):
            notes.append("Assortment field was present but not a list.")
            raw_products = []
        for index, raw in enumerate(raw_products):
            if not isinstance(raw, dict):
                continue
            inclusions = raw.get("inclusions") or []
            highlights = raw.get("highlights") or raw.get("features") or []
            products.append(
                EosProduct(
                    id=str(raw.get("id") or raw.get("tgid") or f"eos-{index + 1}"),
                    title=str(raw.get("title") or raw.get("name") or "Untitled"),
                    price=_num(raw.get("price") or raw.get("fromPrice")),
                    currency=raw.get("currency"),
                    duration=raw.get("duration"),
                    inclusions=[str(item) for item in inclusions] if isinstance(inclusions, list) else [],
                    highlights=[str(item) for item in highlights] if isinstance(highlights, list) else [],
                    cancellation=raw.get("cancellation"),
                    pickup=raw.get("pickup"),
                    url=raw.get("url"),
                )
            )
        faqs = []
        for item in content.get("faqs") or payload.get("faqs") or []:
            if isinstance(item, dict) and item.get("question"):
                faqs.append((str(item["question"]), str(item.get("answer") or "")))
        return EosDocument(
            source=source,
            stage=str(stage) if stage else None,
            content_locked=locked,
            hero_title=content.get("heroTitle") or payload.get("heroTitle"),
            hero_copy=content.get("heroCopy") or content.get("description") or payload.get("heroCopy"),
            faqs=faqs,
            products=products,
            notes=notes,
            parser_name=self.name,
        )

    def _from_csv(self, document: str, source: str) -> EosDocument:
        reader = csv.DictReader(io.StringIO(document))
        products = []
        for index, row in enumerate(reader):
            lowered = {key.lower().strip(): value for key, value in row.items() if key}
            inclusions = lowered.get("inclusions") or ""
            products.append(
                EosProduct(
                    id=lowered.get("id") or f"csv-{index + 1}",
                    title=lowered.get("title") or "Untitled",
                    price=_num(lowered.get("price")),
                    currency=lowered.get("currency"),
                    duration=lowered.get("duration"),
                    inclusions=[part.strip() for part in inclusions.split("|") if part.strip()],
                    cancellation=lowered.get("cancellation"),
                    pickup=lowered.get("pickup"),
                )
            )
        return EosDocument(
            source=source,
            stage=None,
            content_locked=False,
            hero_title=None,
            hero_copy=None,
            faqs=[],
            products=products,
            notes=["CSV columns are unconfirmed. Content lock cannot be seen in a product CSV."],
            parser_name=self.name,
        )

    def _from_html(self, document: str, source: str) -> EosDocument:
        parser = _CardParser()
        parser.feed(document)
        products = []
        for index, raw in enumerate(parser.products):
            price, currency = _price_from_text(raw.get("price_text") or "")
            products.append(
                EosProduct(
                    id=f"html-{index + 1}",
                    title=raw.get("title") or "Untitled",
                    price=price,
                    currency=currency,
                    duration=raw.get("duration"),
                    inclusions=raw.get("inclusions") or [],
                )
            )
        notes = [UNCONFIRMED_SELECTORS]
        if not products and not parser.hero_title:
            notes.append("HTML parser found no assortment cards or hero. Selectors likely differ.")
        return EosDocument(
            source=source,
            stage=parser.stage,
            content_locked=parser.content_locked,
            hero_title=parser.hero_title,
            hero_copy=parser.hero_copy,
            faqs=parser.faqs,
            products=products,
            notes=notes,
            parser_name=self.name,
        )

    def _empty(self, source: str, note: str) -> EosDocument:
        return EosDocument(
            source=source,
            stage=None,
            content_locked=False,
            hero_title=None,
            hero_copy=None,
            faqs=[],
            products=[],
            notes=[note],
            parser_name=self.name,
        )


def _num(value) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        price, _currency = _price_from_text(value)
        return price
    return None


def read_eos_export(path: str, parser: EosParser | None = None) -> EosDocument:
    parser = parser or HeuristicEosAdapter()
    text = Path(path).read_text(encoding="utf-8")
    return parser.parse(text, source=str(path))


def eos_login(profile_dir: Path | None = None, start_url: str = DEFAULT_EOS_URL, launcher=None) -> Path:
    """Open a headed browser so the user can sign in. The profile stays on disk."""
    profile = Path(profile_dir or DEFAULT_PROFILE)
    profile.mkdir(parents=True, exist_ok=True)
    launch = launcher or _launch_persistent
    launch(profile, start_url, headless=False, wait_for_enter=True)
    return profile


def fetch_eos_page(url: str, profile_dir: Path | None = None, launcher=None) -> str:
    profile = Path(profile_dir or DEFAULT_PROFILE)
    if not profile.exists():
        raise FileNotFoundError(
            f"No EOS browser profile at {profile}. Run `collection-qa eos-login` first, "
            "or pass --eos-export with a page you saved while signed in."
        )
    launch = launcher or _launch_persistent
    return launch(profile, url, headless=True, wait_for_enter=False)


def _launch_persistent(profile: Path, url: str, *, headless: bool, wait_for_enter: bool) -> str:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "Playwright is not installed. Install the eos extra: pip install 'collection-qa[eos]', "
            "then `playwright install chromium`. Or pass --eos-export and skip the browser."
        ) from exc
    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile),
            headless=headless,
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(url)
        if wait_for_enter:
            print(f"Sign in to EOS in the browser window ({url}).")
            print("Press Enter here after the MMP page is visible. The session stays in the profile.")
            input()
            html = page.content()
        else:
            page.wait_for_timeout(1500)
            html = page.content()
        context.close()
        return html
