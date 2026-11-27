"""Read an EOS MMP page with the user's own browser session.

EOS is behind the user's Headout sign-in. This module never stores a password
and never clicks. `collection-qa eos-login` opens a headed Chromium with a
persistent profile. Later fetches only open a URL the user pasted, or a known
MMP uuid. Opening a CE from the search box can create a draft, so that path
is refused.

Sign-in is Google-only: eos.headout.com redirects to auth.headout.com/ui/login.
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

AUTH_LOGIN_URL = "https://auth.headout.com/ui/login"
EOS_HOME_URL = "https://eos.headout.com/"

# The MMP uuid is not the CE id. These were read from signed-in draft URLs.
KNOWN_MMP_UUIDS = {
    "3945": "f5889f6f-0a8a-4b5e-801f-e7544cb4e623",
    "7324": "45678f7d-0e69-42b8-9317-3ea10dd79fef",
}

MMP_PAGES = (
    "ce-identity",
    "current-assortment",
    "product-content",
)

UNMAPPED_SIDEBAR = (
    "CE deep research",
    "Keyword research",
    "Competitor research",
    "Proposed assortment",
    "CE level todos",
    "Supply Onboarding Studio",
    "Assortment review",
)

# Confirmed by a signed-in, read-only pass. Not a CSS selector dump: the pages
# are identified by their headings, tabs, and the columns that were on screen.
EOS_STRUCTURE = """
Sign-in: eos.headout.com redirects to auth.headout.com/ui/login. The only
control is "Sign in with Google".

Home: https://eos.headout.com/ has "Search or jump to…" (Ctrl+K) with tabs
Tools / Combined entities / MMPs. A result row shows the CE name, city and
country, the owner email, and the CE id (Milford Sound Cruises 3945, Masai
Mara 7324). Choosing a result can create a draft MMP. Do not open search.
Paste an /mmp/draft/<uuid>/<page> URL, or use a known uuid.

Draft URL: https://eos.headout.com/mmp/draft/<mmp-uuid>/<page>
The uuid is not the CE id. The CE id is in the sidebar title, "Name - 3945".
Known uuids: 3945 = f5889f6f-0a8a-4b5e-801f-e7544cb4e623,
7324 = 45678f7d-0e69-42b8-9317-3ea10dd79fef.

ce-identity?subStep=ce-summary: heading "CE identity", tabs CE summary / MB setup.
Fields: CE ID, Market, Region, General configuration (Collection ID, Collection
URL to scorpio.headout.com/admin/information_architecture/collection/<id>/change/).
Tags: Managed, Collection, New CE. New CE means the collection is not live.

current-assortment: tabs Overview / Availability / Custom fields / Pricing / Pax.
One row per tour group. Columns include Experience/Property/Variant/Vendor,
Revenue, Rev Share %, Orders, AOV, Clicks, Clicks %, S2O, S2C, C2O, Rev/Click,
CR %, TR %, Lead time %, Pax/Order. A new CE says "This CE is new, so there is
no live assortment to review yet."

product-content: steps Assortment overview, Experience names, Content generation,
Lock content for Hedwig. "Content Generation Status: Not started" or "Locked".
Groups "Ready for content generation" and "Locked". Columns: Name, Content
source, Variants ("2/3 ready"). An expanded row shows Current MB highlights,
Current inclusions, Current exclusions, Variant differentiation, Variant ID,
Tour ID. Rows can be tagged New or New Variant.

Not on these pages: prices, cancellation, pickup, images, and any export button.
Those stay in the screenshot, export, and manual placeholders.

Status: a New CE tag or an empty live assortment is IN_PIPELINE. Content status
Locked means Gate B is ready. Assortment rows that show revenue are LIVE.
""".strip()

# Older imports used this name. The text is the confirmed map, not a guess list.
UNCONFIRMED_SELECTORS = EOS_STRUCTURE

EOS_MISSING_FIELDS = (
    ("price", "EOS has no price on the assortment or content pages. Use a screenshot, a saved export, or assortment.csv."),
    ("cancellation", "EOS does not show a cancellation cutoff. Add it in the manual notes or a screenshot."),
    ("pickup", "EOS does not show pickup. Add it in the manual notes or a screenshot."),
    ("images", "EOS does not show product images on the pages that were mapped."),
    ("export_button", "No export button was on these pages. Save the page yourself or paste a screenshot."),
)


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
    revenue: float | None = None
    variant_id: str | None = None
    tour_id: str | None = None
    variants_ready: str | None = None
    row_tag: str | None = None


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
    ce_id: str | None = None
    ce_name: str | None = None
    mmp_uuid: str | None = None
    market: str | None = None
    region: str | None = None
    tags: list[str] = field(default_factory=list)
    is_new_ce: bool = False
    empty_live_assortment: bool = False
    live_assortment: bool = False
    content_status: str | None = None
    page: str | None = None


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

    def _from_html(self, document: str, source: str) -> EosDocument:
        plain = _plain(document)
        if _is_confirmed_page(plain):
            return _from_confirmed(plain, source, parser_name=self.name)
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
        notes = []
        if not products and not parser.hero_title:
            notes.append("HTML parser found no assortment cards or hero.")
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
            "Saved JSON is a manual export. The signed-in EOS pages do not show prices, cancellation, pickup, images, or an export button."
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
            notes=["CSV is a manual export. EOS pages do not show price, cancellation, pickup, or images, and there is no export button."],
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


_MMP_URL = re.compile(
    r"https://eos\.headout\.com/mmp/draft/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:/([a-z0-9-]+))?",
    re.IGNORECASE,
)


def parse_mmp_url(url: str) -> tuple[str | None, str | None]:
    """Return (mmp uuid, page slug) from a pasted draft URL. Neither is the CE id."""
    match = _MMP_URL.search(url or "")
    if not match:
        return None, None
    return match.group(1).lower(), match.group(2)


def ce_id_for_uuid(mmp_uuid: str | None) -> str | None:
    if not mmp_uuid:
        return None
    for ce_id, known in KNOWN_MMP_UUIDS.items():
        if known == mmp_uuid.lower():
            return ce_id
    return None


def mmp_url_for(ce_id: str, page: str = "ce-identity") -> str | None:
    uuid = KNOWN_MMP_UUIDS.get(str(ce_id))
    if not uuid:
        return None
    return f"https://eos.headout.com/mmp/draft/{uuid}/{page}"


def prefer_mmp_url(pasted: str, ce_id: str | None = None, page: str = "ce-identity") -> str | None:
    """Use a pasted draft URL. Fall back to a known uuid. Never build a search URL."""
    uuid, found_page = parse_mmp_url(pasted)
    if uuid:
        return f"https://eos.headout.com/mmp/draft/{uuid}/{found_page or page}"
    if ce_id:
        return mmp_url_for(ce_id, page)
    return None


def describe_mmp_link(url: str) -> dict:
    uuid, page = parse_mmp_url(url)
    if not uuid:
        return {
            "ok": False,
            "line": (
                "Paste a URL like https://eos.headout.com/mmp/draft/<uuid>/<page>. "
                "The search box can create a draft, so this field does not open search."
            ),
        }
    ce_id = ce_id_for_uuid(uuid)
    line = f"MMP {uuid}"
    if page:
        line += f" · {page}"
    if ce_id:
        line += f" · CE {ce_id}"
    line += ". Read-only. Prices, cancellation, pickup, and images are not on these pages."
    return {"ok": True, "uuid": uuid, "page": page, "ce_id": ce_id, "line": line}


def opens_search(url: str) -> bool:
    """True when following the URL would use the home search instead of a saved draft."""
    from urllib.parse import urlparse

    parsed = urlparse(url or "")
    host = parsed.netloc.lower()
    if host.endswith("auth.headout.com"):
        return False
    if not host.endswith("eos.headout.com"):
        return False
    path = parsed.path.rstrip("/")
    if path in {"", "/"}:
        return True
    return path.startswith("/search") or "jump" in path


def classify_eos(document: EosDocument) -> tuple[str, str | None]:
    """Map a parsed EOS page to LIVE or IN_PIPELINE, plus a stage name."""
    if document.live_assortment or any((item.revenue or 0) > 0 for item in document.products):
        stage = "content_locked" if document.content_locked else (document.stage or "live_assortment")
        return "LIVE", stage
    if document.is_new_ce or document.empty_live_assortment:
        stage = "content_locked" if document.content_locked else (document.stage or "new_ce")
        return "IN_PIPELINE", stage
    return "IN_PIPELINE", document.stage


def eos_missing_rows() -> list[dict]:
    return [
        {"field": name, "status": "not provided", "source": "eos", "detail": detail}
        for name, detail in EOS_MISSING_FIELDS
    ]


def _plain(document: str) -> str:
    import html as html_lib

    text = re.sub(r"<[^>]+>", " ", document)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _is_confirmed_page(text: str) -> bool:
    lowered = text.lower()
    return any(
        marker in lowered
        for marker in (
            "ce identity",
            "current assortment",
            "content generation status",
            "no live assortment to review yet",
            "tgid:",
        )
    )


def _from_confirmed(text: str, source: str, parser_name: str) -> EosDocument:
    uuid, page = parse_mmp_url(source)
    ce_id = None
    ce_name = None
    sidebar = re.search(r"([A-Z][A-Za-z0-9' &:.\-]{2,80}?)\s+-\s+(\d{3,6})\b", text)
    if sidebar and "CE identity" not in sidebar.group(1):
        ce_name = sidebar.group(1).strip(" -")
        ce_id = sidebar.group(2)
    ce_field = re.search(r"\bCE ID\s+(\d{3,6})\b", text)
    if ce_field:
        ce_id = ce_field.group(1)
    ce_id = ce_id or ce_id_for_uuid(uuid)
    market = _between(text, "Market", "Region")
    region = _between(text, "Region", "General configuration")
    tags = []
    identity_head = text
    if "CE ID" in text:
        identity_head = text.split("CE ID", 1)[0]
    for tag in ("New CE", "Managed", "Collection"):
        if tag == "Collection" and "CE identity" not in text:
            continue
        if tag in identity_head or (tag == "New CE" and tag in text):
            tags.append(tag)
    is_new = "New CE" in tags
    empty = "no live assortment to review yet" in text.lower()
    content_status = None
    status_match = re.search(r"Content Generation Status:?\s*(Not started|Locked)", text, re.IGNORECASE)
    if status_match:
        content_status = status_match.group(1).capitalize() if status_match.group(1).lower() == "locked" else "Not started"
        if status_match.group(1).lower() == "locked":
            content_status = "Locked"
    locked = content_status == "Locked"
    products = _tour_groups(text)
    live = any((item.revenue or 0) > 0 for item in products) and not empty
    notes = [detail for _name, detail in EOS_MISSING_FIELDS]
    if empty:
        notes.append("This CE is new, so there is no live assortment to review yet.")
    for name in UNMAPPED_SIDEBAR:
        if name in text:
            notes.append(f"Sidebar page “{name}” is visible and not mapped yet.")
    stage = None
    if locked:
        stage = "content_locked"
    elif content_status == "Not started":
        stage = "content_not_started"
    elif empty or is_new:
        stage = "new_ce"
    elif live:
        stage = "live_assortment"
    page_kind = page
    lowered = text.lower()
    if "content generation status" in lowered or "product content" in lowered:
        page_kind = page_kind or "product-content"
    elif "current assortment" in lowered:
        page_kind = page_kind or "current-assortment"
    elif "ce identity" in lowered:
        page_kind = page_kind or "ce-identity"
    return EosDocument(
        source=source,
        stage=stage,
        content_locked=locked,
        hero_title=ce_name,
        hero_copy=None,
        faqs=[],
        products=products,
        notes=notes,
        parser_name=parser_name,
        ce_id=ce_id,
        ce_name=ce_name,
        mmp_uuid=uuid,
        market=market,
        region=region,
        tags=tags,
        is_new_ce=is_new,
        empty_live_assortment=empty,
        live_assortment=live,
        content_status=content_status,
        page=page_kind,
    )


def _between(text: str, start: str, end: str) -> str | None:
    match = re.search(rf"{re.escape(start)}\s+(.+?)\s+{re.escape(end)}\b", text)
    if not match:
        return None
    value = match.group(1).strip()
    return value[:80] or None


def _tour_groups(text: str) -> list[EosProduct]:
    found: dict[str, EosProduct] = {}
    for match in re.finditer(
        r"([A-Z][^$]{4,180}?)\s+TGID:\s*(\d+)\s+\$([0-9][0-9,]*)",
        text,
    ):
        title = _clean_title(match.group(1))
        tgid = match.group(2)
        revenue = float(match.group(3).replace(",", ""))
        found[tgid] = EosProduct(id=f"tg-{tgid}", title=title, revenue=revenue, price=None)
    for match in re.finditer(
        r"([A-Z][^$]{4,180}?)\s+TGID:\s*(\d+)(?:\s+(New Variant|New))?(?:\s+(\d+/\d+)\s+ready)?",
        text,
    ):
        tgid = match.group(2)
        title = _clean_title(match.group(1))
        product = found.get(tgid) or EosProduct(id=f"tg-{tgid}", title=title, price=None)
        product.row_tag = match.group(3) or product.row_tag
        product.variants_ready = match.group(4) or product.variants_ready
        if not product.title:
            product.title = title
        found[tgid] = product
    highlight = re.search(
        r"Current MB highlights\s+(.+?)\s+Current inclusions\s+(.+?)\s+Current exclusions",
        text,
    )
    variant = re.search(r"Variant ID:\s*(\d+)\s+Tour ID:\s*(\d+)", text)
    if found and (highlight or variant):
        first = next(iter(found.values()))
        if highlight:
            first.highlights = [part.strip(" •") for part in re.split(r"\s+•\s+", highlight.group(1)) if part.strip()]
            inclusion = highlight.group(2).strip()
            if inclusion and inclusion.lower() != "no content available":
                first.inclusions = [inclusion]
        if variant:
            first.variant_id = variant.group(1)
            first.tour_id = variant.group(2)
    return list(found.values())


def _clean_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title).strip(" -•")
    title = re.sub(r"^(Name|Overview|Ready for content generation(?:\s+\d+)?|Locked(?:\s+\d+)?)\s+", "", title)
    return title.strip()


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
    if opens_search(url):
        raise ValueError(
            "Opening EOS search can create a draft MMP. Paste an "
            "https://eos.headout.com/mmp/draft/<uuid>/<page> URL instead."
        )
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
            print("Sign in with Google. EOS redirects to auth.headout.com. There is no password field.")
            print("Press Enter here after you are back on EOS. The session stays in the profile.")
            print("Do not use search to open a CE. That can create a draft. Paste the MMP URL instead.")
            input()
            html = page.content()
        else:
            page.wait_for_timeout(1500)
            html = page.content()
        context.close()
        return html
