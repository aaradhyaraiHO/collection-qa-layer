"""Collection spec and scorecard models."""

from __future__ import annotations

from typing import Literal

import yaml
from pydantic import BaseModel, Field

PageType = Literal["headout.com", "microbrand"]
Provenance = Literal["live_headout", "proposed_from_competitors"]
Severity = Literal["pass", "warn", "fail"]


class FAQ(BaseModel):
    question: str
    answer: str


class Surface(BaseModel):
    page_type: PageType
    url: str | None = None
    hero_title: str
    hero_copy: str
    usps: list[str] = Field(default_factory=list)
    faqs: list[FAQ] = Field(default_factory=list)
    faq_capture: Literal["present", "absent", "unknown"] = "present"
    trust_signals: list[str] = Field(default_factory=list)
    discloses_headout: bool | None = None
    not_official_venue_disclaimer: bool | None = None
    authorized_partner_claim: bool | None = None
    notes: list[str] = Field(default_factory=list)


class Product(BaseModel):
    id: str
    title: str
    type: str
    positioning: Literal["budget", "mid", "premium", "luxury", "mixed", "unknown"] = "unknown"
    price: float | None = None
    currency: str | None = None
    price_label: str | None = None
    duration: str | None = None
    duration_hours_min: float | None = None
    duration_hours_max: float | None = None
    days_min: float | None = None
    features: list[str] = Field(default_factory=list)
    rating: float | None = None
    review_count: int | None = None
    inclusions: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    pickup: str | None = None
    pickup_status: Literal["included", "optional", "excluded", "unknown"] = "unknown"
    cancellation: str | None = None
    accessibility_noted: bool = False
    url: str | None = None
    operator: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class PriceClaim(BaseModel):
    product_id: str
    section: str
    price: float
    currency: str
    kind: Literal["from", "original", "varies"] = "from"
    source_url: str


class DurationClaim(BaseModel):
    product_id: str
    section: str
    hours: float
    raw: str
    source_url: str


class Assertion(BaseModel):
    id: str
    type: Literal["min_days_must_mention", "all_products_must_mention", "surface_flag"]
    claim: str
    source_url: str
    min_days: float | None = None
    keywords: list[str] = Field(default_factory=list)
    surface: Literal["primary", "microbrand"] = "primary"
    flag: str | None = None
    expect: bool | None = None
    severity: Literal["warn", "fail"] = "fail"


class AssortmentGap(BaseModel):
    id: str
    claim: str
    observed_in_assortment: bool
    severity: Literal["warn", "fail"] = "warn"
    source_url: str
    note: str = ""


class CompetitorOffer(BaseModel):
    name: str
    seller: str
    price_from: float | None = None
    currency: str | None = None
    duration: str | None = None
    includes: list[str] = Field(default_factory=list)
    url: str
    fetched_on: str
    note: str = ""


class PriceBand(BaseModel):
    tier: Literal["budget", "mid", "premium", "luxury"]
    min_price: float
    max_price: float


class PriceBands(BaseModel):
    currency: str
    tiers: list[PriceBand]
    note: str = ""


class Source(BaseModel):
    url: str
    fetched_on: str
    what: str


class CollectionSpec(BaseModel):
    id: str
    name: str
    destination: str
    ce_id: str | None = None
    provenance: Provenance
    provenance_note: str
    fetched_on: str
    audience_profile: Literal["safari", "fjord_cruise", "custom"] = "custom"
    primary_surface: Surface
    microbrand: Surface | None = None
    products: list[Product]
    price_claims: list[PriceClaim] = Field(default_factory=list)
    duration_claims: list[DurationClaim] = Field(default_factory=list)
    assertions: list[Assertion] = Field(default_factory=list)
    assortment_gaps: list[AssortmentGap] = Field(default_factory=list)
    competitors: list[CompetitorOffer] = Field(default_factory=list)
    price_bands: PriceBands | None = None
    persona_weights: dict | None = None
    sources: list[Source]
    unknowns: list[str]

    def surfaces(self) -> list[tuple[str, Surface]]:
        found = [("primary", self.primary_surface)]
        if self.microbrand is not None:
            found.append(("microbrand", self.microbrand))
        return found

    def product_by_id(self, product_id: str) -> Product | None:
        for product in self.products:
            if product.id == product_id:
                return product
        return None


def load_spec(path: str) -> CollectionSpec:
    with open(path, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle)
    return CollectionSpec.model_validate(raw)


class Issue(BaseModel):
    gate: Literal["A", "B", "deterministic"]
    code: str
    severity: Severity
    message: str
    evidence: dict = Field(default_factory=dict)


class DistributionSummary(BaseModel):
    n: int
    pmf: dict[str, float]
    mean: float


class Quote(BaseModel):
    persona_id: str
    persona_label: str
    stimulus_id: str
    stimulus_title: str
    text: str
    mean_pi: float
    generator: str
