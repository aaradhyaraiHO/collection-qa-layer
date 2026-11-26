"""Deterministic checks against the collection spec.

These do not call a model. They compare fields that were seeded from public
pages: prices, durations, pickup, cancellation, inclusion claims, and whether
a microbrand says who operates it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from collection_qa.models import CollectionSpec, Product
from collection_qa.thresholds import (
    DURATION_SPAN_HOURS,
    DURATION_SPAN_RATIO,
    PRICE_REL_PASS,
    PRICE_REL_WARN,
)


@dataclass
class CheckResult:
    id: str
    severity: str
    gate: str
    blocks_go_live: bool
    message: str
    product_ids: list[str] = field(default_factory=list)
    evidence: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "gate": self.gate,
            "blocks_go_live": self.blocks_go_live,
            "message": self.message,
            "product_ids": list(self.product_ids),
            "evidence": self.evidence,
        }


def _result(check_id: str, severity: str, gate: str, message: str, product_ids: list[str] | None = None, evidence: dict | None = None) -> CheckResult:
    return CheckResult(
        id=check_id,
        severity=severity,
        gate=gate,
        blocks_go_live=severity == "fail",
        message=message,
        product_ids=product_ids or [],
        evidence=evidence or {},
    )


def check_price_consistency(spec: CollectionSpec) -> list[CheckResult]:
    results: list[CheckResult] = []
    drifts: list[dict] = []
    for product in spec.products:
        if product.price is None or product.price == 0:
            continue
        for obs in product.price_observations:
            if obs.currency != product.currency:
                continue
            relative = abs(obs.amount - product.price) / product.price
            drifts.append(
                {
                    "product_id": product.id,
                    "catalog": product.price,
                    "observed": obs.amount,
                    "relative": round(relative, 4),
                    "source": obs.source,
                }
            )
            if relative <= PRICE_REL_PASS:
                continue
            severity = "warn" if relative <= PRICE_REL_WARN else "fail"
            results.append(
                _result(
                    "price_consistency",
                    severity,
                    "both",
                    (
                        f"{product.title} is {product.price:g} {product.currency} in the catalog "
                        f"and {obs.amount:g} {obs.currency} on {obs.source} "
                        f"({relative:.1%} apart). Same-currency gaps above {PRICE_REL_PASS:.1%} "
                        f"are flagged; above {PRICE_REL_WARN:.0%} fail."
                    ),
                    [product.id],
                    {"relative": relative, "note": obs.note},
                )
            )
    if not any(item.severity in ("warn", "fail") and item.id == "price_consistency" for item in results):
        results.append(
            _result(
                "price_consistency",
                "pass",
                "both",
                (
                    f"Same-currency price observations sit within {PRICE_REL_PASS:.1%} of the catalog "
                    "from-price. Wider gaps fail. Cross-currency figures are not converted."
                ),
                evidence={"compared": drifts},
            )
        )
    cross = [
        product.id
        for product in spec.products
        for obs in product.price_observations
        if obs.currency and obs.currency != product.currency
    ]
    if cross:
        results.append(
            _result(
                "currency_surface",
                "info",
                "both",
                (
                    "At least one price observation uses a different currency from the catalog. "
                    "Headout renders from-prices in the visitor currency. Those figures are stored "
                    "and not treated as a mismatch."
                ),
                cross,
            )
        )
    return results


def check_price_units(spec: CollectionSpec) -> list[CheckResult]:
    units = sorted({product.price_unit for product in spec.products if product.price is not None})
    if len(units) > 1:
        per_group = [product.id for product in spec.products if product.price_unit == "per_group"]
        return [
            _result(
                "mixed_price_units",
                "warn",
                "A",
                (
                    "From-prices on this collection use more than one unit "
                    f"({', '.join(units)}). A single list will not read as a price ladder "
                    "unless every card shows the unit. Per-group ids are listed."
                ),
                per_group,
                {"units": units},
            )
        ]
    return [
        _result(
            "mixed_price_units",
            "pass",
            "A",
            f"From-prices share one unit ({units[0] if units else 'none'}).",
        )
    ]


def check_required_fields(spec: CollectionSpec) -> list[CheckResult]:
    results: list[CheckResult] = []
    missing_duration = [p.id for p in spec.products if not p.duration]
    missing_cancel = [p.id for p in spec.products if not p.cancellation]
    variant_pickup = [p.id for p in spec.products if p.pickup_status == "variant_dependent"]
    missing_pickup = [p.id for p in spec.products if p.pickup_status == "not_stated"]
    results.append(
        _result(
            "duration_present",
            "fail" if missing_duration else "pass",
            "both",
            "Every product has a duration."
            if not missing_duration
            else "Some products have no duration.",
            missing_duration,
        )
    )
    results.append(
        _result(
            "cancellation_present",
            "fail" if missing_cancel else "pass",
            "both",
            "Every product has a cancellation statement."
            if not missing_cancel
            else "Some products have no cancellation statement.",
            missing_cancel,
        )
    )
    if missing_pickup:
        results.append(
            _result(
                "pickup_stated",
                "fail",
                "both",
                "Some products do not state a meeting point or say that pickup is not included.",
                missing_pickup,
            )
        )
    if variant_pickup:
        results.append(
            _result(
                "pickup_stated",
                "warn",
                "both",
                (
                    "Pickup or transfers are marked as depending on the option selected. "
                    "The collection card does not name the meeting point."
                ),
                variant_pickup,
            )
        )
    if not missing_pickup and not variant_pickup:
        results.append(
            _result(
                "pickup_stated",
                "pass",
                "both",
                "Every product states a pickup or meeting point, or states that pickup is not included.",
            )
        )
    return results


def check_duration_span(spec: CollectionSpec) -> list[CheckResult]:
    wide: list[str] = []
    for product in spec.products:
        lo, hi = product.duration_hours_min, product.duration_hours_max
        if lo is None or hi is None or lo <= 0:
            continue
        if hi >= lo * DURATION_SPAN_RATIO and (hi - lo) >= DURATION_SPAN_HOURS:
            wide.append(product.id)
    if not wide:
        return [
            _result(
                "duration_span",
                "pass",
                "A",
                "No product card stretches a short experience and a much longer variant into one duration.",
            )
        ]
    return [
        _result(
            "duration_span",
            "warn",
            "A",
            (
                "These cards publish a duration range at least "
                f"{DURATION_SPAN_RATIO:.0f}× wide and at least {DURATION_SPAN_HOURS:.0f} hours across. "
                "The from-price is then hard to read as one experience."
            ),
            wide,
        )
    ]


def check_duration_claim(spec: CollectionSpec) -> list[CheckResult]:
    claim = spec.page.duration_claim_hours
    lead = spec.lead_product()
    if claim is None or lead is None or lead.duration_hours_min is None or lead.duration_hours_max is None:
        return []
    span = lead.duration_hours_max - lead.duration_hours_min
    if span < DURATION_SPAN_HOURS:
        return [
            _result(
                "duration_claim",
                "pass",
                "B",
                "The page duration claim sits on a lead product with a narrow duration.",
                [lead.id],
            )
        ]
    inside = lead.duration_hours_min - 0.05 <= claim <= lead.duration_hours_max + 0.05
    return [
        _result(
            "duration_claim",
            "warn",
            "B",
            (
                f"The page says “{spec.page.duration_claim_text}” ({claim:g} hours). "
                f"The lead card {lead.title} is {lead.duration}. "
                + (
                    "The claimed length sits inside that range, so the line is not false, but it hides the range."
                    if inside
                    else "The claimed length sits outside the lead card's range."
                )
            ),
            [lead.id],
            {"claim_hours": claim, "inside_range": inside},
        )
    ]


def check_zero_reviews(spec: CollectionSpec) -> list[CheckResult]:
    zeros = [p.id for p in spec.products if (p.review_count or 0) == 0]
    if not zeros:
        return [_result("zero_reviews", "pass", "A", "Every product has at least one review on the card.")]
    return [
        _result(
            "zero_reviews",
            "warn",
            "A",
            f"{len(zeros)} of {len(spec.products)} products have 0 reviews on the collection card.",
            zeros,
        )
    ]


def check_scope(spec: CollectionSpec) -> list[CheckResult]:
    if not spec.scope_keywords:
        return []
    off = [
        product.id
        for product in spec.products
        if not any(keyword.lower() in product.title.lower() for keyword in spec.scope_keywords)
    ]
    if not off:
        return [
            _result(
                "assortment_scope",
                "pass",
                "A",
                f"Every product title contains one of: {', '.join(spec.scope_keywords)}.",
            )
        ]
    return [
        _result(
            "assortment_scope",
            "warn",
            "A",
            (
                "These product titles do not contain the collection scope keywords "
                f"({', '.join(spec.scope_keywords)}). Confirm they belong on this collection."
            ),
            off,
        )
    ]


def _offenders_for_claim(spec: CollectionSpec, claim) -> list[Product]:
    offenders: list[Product] = []
    for product in spec.products:
        if claim.min_duration_days is not None:
            days = product.duration_days_min
            if days is None or days + 1e-6 < claim.min_duration_days:
                continue
        if claim.expects_tag not in product.tags:
            offenders.append(product)
    return offenders


def check_claims(spec: CollectionSpec) -> list[CheckResult]:
    results: list[CheckResult] = []
    if not spec.page.claims:
        return results
    for claim in spec.page.claims:
        offenders = _offenders_for_claim(spec, claim)
        if not offenders:
            results.append(
                _result(
                    "inclusion_claim",
                    "pass",
                    "B",
                    f"Claim '{claim.text}' matches the tagged products it applies to.",
                    evidence={"claim_id": claim.id},
                )
            )
            continue
        counter = f" The same page also says: {claim.counter_quote}" if claim.counter_quote else ""
        results.append(
            _result(
                "inclusion_claim",
                claim.severity if claim.severity in ("warn", "fail") else "warn",
                "B",
                (
                    f"The page says “{claim.text}”. "
                    f"{len(offenders)} product(s) meet the duration condition and do not carry "
                    f"the tag '{claim.expects_tag}'."
                    + counter
                ),
                [product.id for product in offenders],
                {"claim_id": claim.id, "source_url": claim.source_url},
            )
        )
    return results


def check_reseller_disclosure(spec: CollectionSpec) -> list[CheckResult]:
    if spec.page_type != "microbrand":
        return [
            _result(
                "reseller_disclosure",
                "pass",
                "B",
                "This spec is a headout.com collection, so the official-versus-reseller line is the marketplace frame.",
            )
        ]
    blob = " ".join(
        [spec.page.hero, spec.page.meta_description or "", *spec.page.usps, *spec.page.trust_signals]
        + [section.body for section in spec.page.sections]
        + [f"{faq.q} {faq.a}" for faq in spec.page.faqs]
    ).lower()
    names_operator = "headout" in blob
    disclaimer = "not the venue" in blob or "not the official" in blob
    if names_operator and disclaimer:
        return [
            _result(
                "reseller_disclosure",
                "pass",
                "B",
                "The microbrand names Headout and says it is not the venue site.",
            )
        ]
    if names_operator:
        return [
            _result(
                "reseller_disclosure",
                "warn",
                "B",
                (
                    "The microbrand text names Headout, and the fetched copy does not contain a sentence "
                    "that this is not the venue's website. Travelers can still read the domain as the operator."
                ),
                evidence={"url": spec.page.url},
            )
        ]
    return [
        _result(
            "reseller_disclosure",
            "fail",
            "B",
            "The microbrand text fetched for this spec does not name the operator.",
            evidence={"url": spec.page.url},
        )
    ]


def check_faq_coverage(spec: CollectionSpec) -> list[CheckResult]:
    if spec.page.faqs:
        topics = {
            "cancellation": ("cancel",),
            "inclusions": ("includ", "park fee"),
            "duration_or_days": ("how many days", "how long", "duration"),
            "suitability": ("famil", "children", "access", "wheelchair"),
        }
        blob = " ".join(f"{faq.q} {faq.a}" for faq in spec.page.faqs).lower()
        missing = [name for name, cues in topics.items() if not any(cue in blob for cue in cues)]
        if not missing:
            return [_result("faq_coverage", "pass", "B", "Confirmed FAQs cover cancellation, inclusions, duration, and suitability.")]
        return [
            _result(
                "faq_coverage",
                "warn",
                "B",
                "Confirmed FAQs are missing these topics: " + ", ".join(missing) + ".",
                evidence={"missing": missing},
            )
        ]
    note = ""
    if spec.page.longform_in_ssr is False:
        note = " The collection SSR payload's long-form body was empty, which matches other Headout collection pages, so a client-rendered guide may still exist."
    return [
        _result(
            "faq_coverage",
            "warn",
            "B",
            "No FAQ question and answer was confirmed in the fetched page." + note,
        )
    ]


def check_accessibility(spec: CollectionSpec) -> list[CheckResult]:
    limited = [
        product.id
        for product in spec.products
        if product.accessibility and "not fully wheelchair" in product.accessibility.lower()
    ]
    if not limited:
        return []
    faq_blob = " ".join(f"{faq.q} {faq.a}" for faq in spec.page.faqs).lower()
    if "wheelchair" in faq_blob or "accessib" in faq_blob:
        return [
            _result(
                "accessibility_disclosure",
                "pass",
                "B",
                "A product notes limited wheelchair access and the FAQs discuss access.",
                limited,
            )
        ]
    return [
        _result(
            "accessibility_disclosure",
            "warn",
            "B",
            (
                "A fetched product page says the cruise is not fully wheelchair accessible. "
                "The confirmed collection copy does not say so."
            ),
            limited,
        )
    ]


def check_outside_collection(spec: CollectionSpec) -> list[CheckResult]:
    if not spec.outside_collection:
        return []
    return [
        _result(
            "outside_collection",
            "warn",
            "A",
            (
                "Headout publishes related products that are not in this collection. "
                "Titles: " + "; ".join(product.title for product in spec.outside_collection) + "."
            ),
            [product.id for product in spec.outside_collection],
        )
    ]


def check_benchmarks(spec: CollectionSpec) -> list[CheckResult]:
    results: list[CheckResult] = []
    for bench in spec.benchmarks:
        if bench.comparability != "comparable" or bench.price_from is None or bench.currency != spec.currency:
            results.append(
                _result(
                    "competitor_gap",
                    "info",
                    "A",
                    (
                        f"{bench.seller} lists “{bench.title}”"
                        + (f" from {bench.price_from:g} {bench.currency}." if bench.price_from is not None else ".")
                        + f" Comparability is '{bench.comparability}'. {bench.note}"
                    ),
                    evidence={"benchmark_id": bench.id, "url": bench.url},
                )
            )
            continue
        covered = [
            product
            for product in spec.products
            if bench.tag in product.tags
            and product.price is not None
            and product.currency == bench.currency
            and product.price <= bench.price_from * 1.15
        ]
        if covered:
            results.append(
                _result(
                    "competitor_gap",
                    "pass",
                    "A",
                    f"{bench.seller} price band for {bench.tag} is covered by an in-collection product.",
                    [product.id for product in covered],
                )
            )
        else:
            results.append(
                _result(
                    "competitor_gap",
                    "warn",
                    "A",
                    (
                        f"No in-collection product tagged {bench.tag} is within 15% of "
                        f"{bench.seller}'s from-price ({bench.price_from:g} {bench.currency}). {bench.note}"
                    ),
                    evidence={"benchmark_id": bench.id},
                )
            )
    return results


def run_checks(spec: CollectionSpec) -> list[CheckResult]:
    results: list[CheckResult] = []
    for fn in (
        check_price_consistency,
        check_price_units,
        check_required_fields,
        check_duration_span,
        check_duration_claim,
        check_zero_reviews,
        check_scope,
        check_claims,
        check_reseller_disclosure,
        check_faq_coverage,
        check_accessibility,
        check_outside_collection,
        check_benchmarks,
    ):
        results.extend(fn(spec))
    return results
