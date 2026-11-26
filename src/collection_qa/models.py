"""Collection spec models. YAML and JSON load into these dataclasses."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Faq:
    q: str
    a: str


@dataclass
class Section:
    id: str
    heading: str
    body: str


@dataclass
class Claim:
    id: str
    text: str
    source_url: str
    expects_tag: str
    min_duration_days: float | None = None
    severity: str = "warn"
    counter_quote: str | None = None


@dataclass
class PriceObservation:
    amount: float
    currency: str
    source: str
    source_url: str
    note: str = ""


@dataclass
class Product:
    id: str
    title: str
    url: str
    product_type: str
    price: float | None
    original_price: float | None
    currency: str
    price_unit: str
    duration: str | None
    duration_hours_min: float | None
    duration_hours_max: float | None
    tags: list[str] = field(default_factory=list)
    features: list[str] = field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    inclusions: list[str] = field(default_factory=list)
    inclusions_status: str = "unknown"
    exclusions: list[str] = field(default_factory=list)
    pickup_status: str = "not_stated"
    pickup: str | None = None
    cancellation: str | None = None
    accessibility: str | None = None
    multi_variant: bool = False
    other_prices_exist: bool = False
    best_discount_percent: float = 0
    api_guest_count: int | None = None
    popularity_rank: int | None = None
    page_ssr_rank: int | None = None
    price_observations: list[PriceObservation] = field(default_factory=list)
    notes: str | None = None

    @property
    def duration_days_min(self) -> float | None:
        if self.duration_hours_min is None:
            return None
        return self.duration_hours_min / 24.0


@dataclass
class Benchmark:
    id: str
    seller: str
    url: str
    fetched_at: str
    title: str
    price_from: float | None
    currency: str | None
    price_unit: str | None
    tag: str
    comparability: str
    note: str


@dataclass
class PageContent:
    url: str
    hero: str
    meta_description: str | None = None
    usps: list[str] = field(default_factory=list)
    trust_signals: list[str] = field(default_factory=list)
    faqs: list[Faq] = field(default_factory=list)
    sections: list[Section] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    rating_note: str | None = None
    duration_claim_hours: float | None = None
    duration_claim_text: str | None = None
    longform_in_ssr: bool | None = None


@dataclass
class CollectionSpec:
    id: str
    name: str
    destination: str
    page_type: str
    catalog_status: str
    fetched_at: str
    currency: str
    page: PageContent
    products: list[Product]
    collection_id: str | None = None
    ce_id: str | None = None
    collection_type: str | None = None
    primary_city_code: str | None = None
    scope_keywords: list[str] = field(default_factory=list)
    lead_product_id: str | None = None
    sources: list[dict] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)
    outside_collection: list[Product] = field(default_factory=list)
    benchmarks: list[Benchmark] = field(default_factory=list)
    persona_weights: dict | None = None
    also_surfaces: list[dict] = field(default_factory=list)

    def product_by_id(self) -> dict[str, Product]:
        return {product.id: product for product in self.products}

    def lead_product(self) -> Product | None:
        if not self.lead_product_id:
            return self.products[0] if self.products else None
        return self.product_by_id().get(self.lead_product_id)


def _req(data: dict, key: str, ctx: str):
    if key not in data or data[key] is None:
        raise ValueError(f"{ctx} is missing '{key}'")
    return data[key]


def _product(raw: dict, ctx: str) -> Product:
    observations = [
        PriceObservation(
            amount=float(item["amount"]),
            currency=str(item["currency"]),
            source=str(item.get("source", "")),
            source_url=str(item.get("source_url", "")),
            note=str(item.get("note", "")),
        )
        for item in raw.get("price_observations") or []
    ]
    price = raw.get("price")
    return Product(
        id=str(_req(raw, "id", ctx)),
        title=str(_req(raw, "title", ctx)),
        url=str(raw.get("url") or ""),
        product_type=str(raw.get("product_type") or raw.get("type") or "experience"),
        price=None if price is None else float(price),
        original_price=None if raw.get("original_price") is None else float(raw["original_price"]),
        currency=str(raw.get("currency") or ""),
        price_unit=str(raw.get("price_unit") or "per_person"),
        duration=raw.get("duration"),
        duration_hours_min=None if raw.get("duration_hours_min") is None else float(raw["duration_hours_min"]),
        duration_hours_max=None if raw.get("duration_hours_max") is None else float(raw["duration_hours_max"]),
        tags=[str(tag) for tag in raw.get("tags") or []],
        features=[str(item) for item in raw.get("features") or []],
        rating=None if raw.get("rating") is None else float(raw["rating"]),
        review_count=None if raw.get("review_count") is None else int(raw["review_count"]),
        inclusions=[str(item) for item in raw.get("inclusions") or []],
        inclusions_status=str(raw.get("inclusions_status") or "unknown"),
        exclusions=[str(item) for item in raw.get("exclusions") or []],
        pickup_status=str(raw.get("pickup_status") or "not_stated"),
        pickup=raw.get("pickup"),
        cancellation=raw.get("cancellation"),
        accessibility=raw.get("accessibility"),
        multi_variant=bool(raw.get("multi_variant")),
        other_prices_exist=bool(raw.get("other_prices_exist")),
        best_discount_percent=float(raw.get("best_discount_percent") or 0),
        api_guest_count=None if raw.get("api_guest_count") is None else int(raw["api_guest_count"]),
        popularity_rank=None if raw.get("popularity_rank") is None else int(raw["popularity_rank"]),
        page_ssr_rank=None if raw.get("page_ssr_rank") is None else int(raw["page_ssr_rank"]),
        price_observations=observations,
        notes=raw.get("notes"),
    )


def spec_from_dict(data: dict) -> CollectionSpec:
    page_raw = _req(data, "page", "spec")
    page = PageContent(
        url=str(_req(page_raw, "url", "page")),
        hero=str(_req(page_raw, "hero", "page")),
        meta_description=page_raw.get("meta_description"),
        usps=[str(item) for item in page_raw.get("usps") or []],
        trust_signals=[str(item) for item in page_raw.get("trust_signals") or []],
        faqs=[Faq(q=str(item["q"]), a=str(item["a"])) for item in page_raw.get("faqs") or []],
        sections=[
            Section(id=str(item["id"]), heading=str(item["heading"]), body=str(item["body"]))
            for item in page_raw.get("sections") or []
        ],
        claims=[
            Claim(
                id=str(item["id"]),
                text=str(item["text"]),
                source_url=str(item.get("source_url") or ""),
                expects_tag=str(item["expects_tag"]),
                min_duration_days=None if item.get("min_duration_days") is None else float(item["min_duration_days"]),
                severity=str(item.get("severity") or "warn"),
                counter_quote=item.get("counter_quote"),
            )
            for item in page_raw.get("claims") or []
        ],
        rating=None if page_raw.get("rating") is None else float(page_raw["rating"]),
        review_count=None if page_raw.get("review_count") is None else int(page_raw["review_count"]),
        rating_note=page_raw.get("rating_note"),
        duration_claim_hours=None
        if page_raw.get("duration_claim_hours") is None
        else float(page_raw["duration_claim_hours"]),
        duration_claim_text=page_raw.get("duration_claim_text"),
        longform_in_ssr=page_raw.get("longform_in_ssr"),
    )
    products = [_product(item, f"products[{index}]") for index, item in enumerate(data.get("products") or [])]
    if not products:
        raise ValueError("spec needs at least one product")
    outside = [_product(item, f"outside[{index}]") for index, item in enumerate(data.get("outside_collection") or [])]
    benchmarks = [
        Benchmark(
            id=str(item["id"]),
            seller=str(item.get("seller") or ""),
            url=str(item.get("url") or ""),
            fetched_at=str(item.get("fetched_at") or ""),
            title=str(item.get("title") or ""),
            price_from=None if item.get("price_from") is None else float(item["price_from"]),
            currency=item.get("currency"),
            price_unit=item.get("price_unit"),
            tag=str(item.get("tag") or ""),
            comparability=str(item.get("comparability") or "currency_unknown"),
            note=str(item.get("note") or ""),
        )
        for item in data.get("benchmarks") or []
    ]
    return CollectionSpec(
        id=str(_req(data, "id", "spec")),
        name=str(_req(data, "name", "spec")),
        destination=str(_req(data, "destination", "spec")),
        page_type=str(_req(data, "page_type", "spec")),
        catalog_status=str(_req(data, "catalog_status", "spec")),
        fetched_at=str(_req(data, "fetched_at", "spec")),
        currency=str(_req(data, "currency", "spec")),
        page=page,
        products=products,
        collection_id=None if data.get("collection_id") is None else str(data["collection_id"]),
        ce_id=None if data.get("ce_id") is None else str(data["ce_id"]),
        collection_type=data.get("collection_type"),
        primary_city_code=data.get("primary_city_code"),
        scope_keywords=[str(item) for item in data.get("scope_keywords") or []],
        lead_product_id=None if data.get("lead_product_id") is None else str(data["lead_product_id"]),
        sources=list(data.get("sources") or []),
        unknowns=[str(item) for item in data.get("unknowns") or []],
        outside_collection=outside,
        benchmarks=benchmarks,
        persona_weights=data.get("persona_weights"),
        also_surfaces=list(data.get("also_surfaces") or []),
    )


def load_spec(path: str | Path) -> CollectionSpec:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if file_path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"{file_path} did not contain a mapping")
    return spec_from_dict(data)
