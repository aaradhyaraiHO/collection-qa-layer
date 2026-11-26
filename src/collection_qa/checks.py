"""Deterministic collection checks and the numeric thresholds for SSR means.

Thresholds are assumptions. They are not fitted to Headout CVR. The calibration
plan in collection_qa.anchors says how to replace them.
"""

from __future__ import annotations

from collection_qa.models import Assertion, CollectionSpec, Issue, Product, Surface

# SSR mean purchase intent. Higher is better. Assumption until a CVR backtest.
PAGE_MEAN_PASS = 3.6
PAGE_MEAN_WARN = 3.2
SEGMENT_MEAN_PASS = 3.4
SEGMENT_MEAN_WARN = 2.8
PRODUCT_MEAN_PASS = 3.3
PRODUCT_MEAN_WARN = 2.6

# Relative gap between two "from" prices for the same product.
PRICE_REL_PASS = 0.03
PRICE_REL_WARN = 0.10

# Absolute gap, in hours, between two duration statements for the same product.
DURATION_HOURS_PASS = 1.0
DURATION_HOURS_WARN = 4.0

# Share of products missing a critical field.
MISSING_RATE_WARN = 0.0
MISSING_RATE_FAIL = 0.25

CHOICE_OVERLOAD_WARN = 12
CHOICE_OVERLOAD_FAIL = 20

# Two products cannibalise when they share type and length and sit within this
# relative price gap. Purchase-intent delta is applied later by the pipeline.
CANNIBAL_PRICE_REL = 0.15
CANNIBAL_PI_DELTA = 0.25

FAQ_TOPICS = {
    "cancellation": ("cancel", "refund"),
    "getting_there": ("pickup", "getting there", "drive", "coach", "transfer", "parking"),
    "access": ("wheelchair", "access", "mobility", "stroller"),
}


def rate_higher_is_better(value: float, *, pass_at: float, warn_at: float) -> str:
    if value >= pass_at:
        return "pass"
    if value >= warn_at:
        return "warn"
    return "fail"


def rate_lower_is_better(value: float, *, pass_at: float, warn_at: float) -> str:
    if value <= pass_at:
        return "pass"
    if value <= warn_at:
        return "warn"
    return "fail"


def _issue(gate: str, code: str, severity: str, message: str, **evidence: object) -> Issue:
    return Issue(gate=gate, code=code, severity=severity, message=message, evidence=dict(evidence))


def relative_gap(a: float, b: float) -> float:
    baseline = min(abs(a), abs(b))
    if baseline == 0:
        return 0.0 if a == b else float("inf")
    return abs(a - b) / baseline


def run_deterministic_checks(spec: CollectionSpec) -> list[Issue]:
    issues: list[Issue] = []
    issues.extend(_price_consistency(spec))
    issues.extend(_duration_consistency(spec))
    issues.extend(_missing_fields(spec))
    issues.extend(_currency(spec))
    issues.extend(_choice_overload(spec))
    issues.extend(_price_ladder(spec))
    issues.extend(_close_products(spec))
    issues.extend(_assertions(spec))
    issues.extend(_gaps(spec))
    issues.extend(_surface_content(spec))
    return issues


def _price_consistency(spec: CollectionSpec) -> list[Issue]:
    grouped: dict[tuple[str, str, str], list] = {}
    for claim in spec.price_claims:
        if claim.kind == "varies":
            continue
        grouped.setdefault((claim.product_id, claim.kind, claim.currency), []).append(claim)
    issues: list[Issue] = []
    if not grouped:
        return [
            _issue(
                "deterministic",
                "price_consistency",
                "pass",
                "No comparable price claims were captured, so nothing conflicted.",
                compared=0,
            )
        ]
    for (product_id, kind, currency), claims in sorted(grouped.items()):
        prices = [claim.price for claim in claims]
        if len(prices) < 2:
            continue
        gap = relative_gap(min(prices), max(prices))
        severity = rate_lower_is_better(gap, pass_at=PRICE_REL_PASS, warn_at=PRICE_REL_WARN)
        sections = ", ".join(f"{claim.section}={claim.price:g}" for claim in claims)
        product = spec.product_by_id(product_id)
        title = product.title if product else product_id
        issues.append(
            _issue(
                "deterministic",
                "price_consistency",
                severity,
                f"{title}: {kind} prices in {currency} differ by {gap:.1%} across sections ({sections}).",
                product_id=product_id,
                kind=kind,
                currency=currency,
                relative_gap=round(gap, 4),
                pass_at=PRICE_REL_PASS,
                warn_at=PRICE_REL_WARN,
            )
        )
    if not issues:
        issues.append(
            _issue(
                "deterministic",
                "price_consistency",
                "pass",
                "Every product with more than one price claim of the same kind agrees within the pass band.",
            )
        )
    return issues


def _duration_consistency(spec: CollectionSpec) -> list[Issue]:
    grouped: dict[str, list] = {}
    for claim in spec.duration_claims:
        grouped.setdefault(claim.product_id, []).append(claim)
    issues: list[Issue] = []
    for product_id, claims in sorted(grouped.items()):
        if len(claims) < 2:
            continue
        hours = [claim.hours for claim in claims]
        gap = max(hours) - min(hours)
        severity = rate_lower_is_better(gap, pass_at=DURATION_HOURS_PASS, warn_at=DURATION_HOURS_WARN)
        product = spec.product_by_id(product_id)
        title = product.title if product else product_id
        shown = ", ".join(f"{claim.section}={claim.raw}" for claim in claims)
        issues.append(
            _issue(
                "deterministic",
                "duration_consistency",
                severity,
                f"{title}: duration statements differ by {gap:g} hours ({shown}).",
                product_id=product_id,
                hours_gap=gap,
                pass_at=DURATION_HOURS_PASS,
                warn_at=DURATION_HOURS_WARN,
            )
        )
    return issues


def _missing_rate(missing: int, total: int) -> str:
    if total == 0:
        return "pass"
    rate = missing / total
    if rate <= MISSING_RATE_WARN:
        return "pass"
    if rate <= MISSING_RATE_FAIL:
        return "warn"
    return "fail"


def _missing_fields(spec: CollectionSpec) -> list[Issue]:
    total = len(spec.products)
    checks = {
        "duration": [product for product in spec.products if not product.duration],
        "cancellation": [product for product in spec.products if not product.cancellation],
        "pickup": [product for product in spec.products if product.pickup_status == "unknown"],
    }
    issues = []
    for field, missing_products in checks.items():
        severity = _missing_rate(len(missing_products), total)
        verb = "is" if len(missing_products) == 1 else "are"
        issues.append(
            _issue(
                "deterministic",
                f"missing_{field}",
                severity,
                (
                    f"{len(missing_products)} of {total} products {verb} missing {field}."
                    if missing_products or total == 0
                    else f"Every product states {field}."
                ),
                missing_ids=[product.id for product in missing_products],
                rate=(len(missing_products) / total) if total else 0.0,
                warn_above=MISSING_RATE_WARN,
                fail_above=MISSING_RATE_FAIL,
            )
        )
    return issues


def _currency(spec: CollectionSpec) -> list[Issue]:
    currencies = {product.currency for product in spec.products if product.price is not None and product.currency}
    claim_currencies = {claim.currency for claim in spec.price_claims}
    together = currencies | claim_currencies
    if len(together) <= 1:
        return [
            _issue(
                "deterministic",
                "currency_consistency",
                "pass",
                "Prices that were captured use a single currency."
                if together
                else "No numeric prices were captured to compare.",
                currencies=sorted(together),
            )
        ]
    return [
        _issue(
            "deterministic",
            "currency_consistency",
            "fail",
            f"Prices are mixed across currencies: {', '.join(sorted(together))}.",
            currencies=sorted(together),
        )
    ]


def _choice_overload(spec: CollectionSpec) -> list[Issue]:
    count = len(spec.products)
    if count >= CHOICE_OVERLOAD_FAIL:
        severity = "fail"
    elif count >= CHOICE_OVERLOAD_WARN:
        severity = "warn"
    else:
        severity = "pass"
    return [
        _issue(
            "A",
            "choice_overload",
            severity,
            f"The assortment has {count} products (warn at {CHOICE_OVERLOAD_WARN}, fail at {CHOICE_OVERLOAD_FAIL}).",
            count=count,
            warn_at=CHOICE_OVERLOAD_WARN,
            fail_at=CHOICE_OVERLOAD_FAIL,
        )
    ]


def _price_ladder(spec: CollectionSpec) -> list[Issue]:
    if spec.price_bands is None:
        return [
            _issue(
                "A",
                "price_ladder",
                "warn",
                "No price bands were defined, so ladder coverage was not scored.",
            )
        ]
    priced = [product for product in spec.products if product.price is not None]
    if not spec.products or len(priced) / len(spec.products) < 0.5:
        return [
            _issue(
                "A",
                "price_ladder",
                "warn",
                "Fewer than half the products have a numeric price, so the ladder cannot be judged.",
                priced=len(priced),
                products=len(spec.products),
            )
        ]
    issues = []
    for band in spec.price_bands.tiers:
        matches = [
            product
            for product in priced
            if product.currency == spec.price_bands.currency
            and band.min_price <= product.price < band.max_price
        ]
        severity = "pass" if matches else "warn"
        issues.append(
            _issue(
                "A",
                "price_ladder",
                severity,
                (
                    f"{band.tier} ({spec.price_bands.currency} {band.min_price:g}–{band.max_price:g}) "
                    f"has {len(matches)} product(s)."
                ),
                tier=band.tier,
                product_ids=[product.id for product in matches],
            )
        )
    return issues


def _same_shelf(left: Product, right: Product) -> bool:
    if left.type != right.type:
        return False
    if left.days_min is not None and right.days_min is not None:
        return left.days_min == right.days_min
    if left.duration_hours_min is not None and right.duration_hours_min is not None:
        return abs(left.duration_hours_min - right.duration_hours_min) <= 1
    return False


def _close_products(spec: CollectionSpec) -> list[Issue]:
    """Price-only cannibalisation. The pipeline adds purchase-intent proximity."""
    issues: list[Issue] = []
    products = spec.products
    for index, left in enumerate(products):
        for right in products[index + 1 :]:
            if not _same_shelf(left, right):
                continue
            if left.price is None or right.price is None:
                continue
            if left.currency != right.currency:
                continue
            gap = relative_gap(left.price, right.price)
            if gap <= CANNIBAL_PRICE_REL:
                issues.append(
                    _issue(
                        "A",
                        "cannibalisation",
                        "warn",
                        f"{left.title} and {right.title} share a shelf and their prices differ by only {gap:.1%}.",
                        product_ids=[left.id, right.id],
                        relative_gap=round(gap, 4),
                        threshold=CANNIBAL_PRICE_REL,
                    )
                )
    return issues


def cannibalisation_from_intent(
    spec: CollectionSpec,
    means: dict[str, float],
) -> list[Issue]:
    issues: list[Issue] = []
    products = spec.products
    for index, left in enumerate(products):
        for right in products[index + 1 :]:
            if not _same_shelf(left, right):
                continue
            if left.id not in means or right.id not in means:
                continue
            price_close = False
            if left.price is not None and right.price is not None and left.currency == right.currency:
                price_close = relative_gap(left.price, right.price) <= CANNIBAL_PRICE_REL
            elif left.price is None and right.price is None and left.positioning == right.positioning:
                price_close = True
            pi_gap = abs(means[left.id] - means[right.id])
            if price_close and pi_gap < CANNIBAL_PI_DELTA:
                issues.append(
                    _issue(
                        "A",
                        "cannibalisation_intent",
                        "warn",
                        (
                            f"{left.title} and {right.title} draw almost the same purchase intent "
                            f"(means {means[left.id]:.2f} vs {means[right.id]:.2f}) on the same shelf."
                        ),
                        product_ids=[left.id, right.id],
                        mean_delta=round(pi_gap, 3),
                        threshold=CANNIBAL_PI_DELTA,
                    )
                )
    return issues


def _blob(product: Product) -> str:
    """Traveler-facing text only. Analyst notes are not part of the listing."""
    parts = [product.title, *product.features, *product.inclusions, product.duration or ""]
    return " ".join(parts).lower()


def _assertion_result(spec: CollectionSpec, assertion: Assertion) -> Issue:
    if assertion.type == "surface_flag":
        return _surface_flag(spec, assertion)
    if assertion.type == "min_days_must_mention":
        pool = [
            product
            for product in spec.products
            if product.days_min is not None and assertion.min_days is not None and product.days_min >= assertion.min_days
        ]
    elif assertion.type == "all_products_must_mention":
        pool = [product for product in spec.products if product.inclusions]
    else:
        raise ValueError(f"unknown assertion type {assertion.type}")
    needles = [keyword.lower() for keyword in assertion.keywords]
    missed = [product for product in pool if not any(needle in _blob(product) for needle in needles)]
    if not pool:
        severity = "warn"
        message = f"{assertion.claim} — no products were in scope, so the claim was not tested."
    elif missed:
        severity = assertion.severity
        message = (
            f"{assertion.claim} — {len(missed)} of {len(pool)} in-scope products do not mention "
            f"{', '.join(assertion.keywords)}."
        )
    else:
        severity = "pass"
        message = f"{assertion.claim} — in-scope products mention the required terms."
    return _issue(
        "B",
        f"assertion:{assertion.id}",
        severity,
        message,
        missed_ids=[product.id for product in missed],
        source_url=assertion.source_url,
    )


def _surface_flag(spec: CollectionSpec, assertion: Assertion) -> Issue:
    surface = spec.primary_surface if assertion.surface == "primary" else spec.microbrand
    if surface is None:
        return _issue(
            "B",
            f"assertion:{assertion.id}",
            "warn",
            f"{assertion.claim} — that surface was not in the spec.",
            source_url=assertion.source_url,
        )
    actual = getattr(surface, assertion.flag or "", None)
    if actual is None:
        severity = "warn"
        detail = "the flag was not observed (unknown), not a confirmed contradiction"
    elif actual == assertion.expect:
        severity = "pass"
        detail = f"{assertion.flag} is {actual}"
    else:
        severity = assertion.severity
        detail = f"{assertion.flag} is {actual}, expected {assertion.expect}"
    return _issue(
        "B",
        f"assertion:{assertion.id}",
        severity,
        f"{assertion.claim} — {detail}.",
        actual=actual,
        expect=assertion.expect,
        source_url=assertion.source_url,
    )


def _assertions(spec: CollectionSpec) -> list[Issue]:
    return [_assertion_result(spec, assertion) for assertion in spec.assertions]


def _gaps(spec: CollectionSpec) -> list[Issue]:
    issues = []
    for gap in spec.assortment_gaps:
        if gap.observed_in_assortment:
            severity = "pass"
            message = f"{gap.claim} A matching product is in the assortment."
        else:
            severity = gap.severity
            message = f"{gap.claim} No matching product was confirmed in this assortment."
        if gap.note:
            message = f"{message} {gap.note}"
        issues.append(
            _issue(
                "A",
                f"gap:{gap.id}",
                severity,
                message,
                source_url=gap.source_url,
            )
        )
    return issues


def _faq_text(surface: Surface) -> str:
    return " ".join(f"{item.question} {item.answer}" for item in surface.faqs).lower()


def _surface_content(spec: CollectionSpec) -> list[Issue]:
    issues: list[Issue] = []
    for role, surface in spec.surfaces():
        if surface.faq_capture == "unknown":
            issues.append(
                _issue(
                    "B",
                    "faq_capture_unknown",
                    "warn",
                    f"{role} surface ({surface.page_type}) did not include an FAQ block in the capture. "
                    "Absence is not confirmed.",
                    surface=role,
                    url=surface.url,
                )
            )
        elif not surface.faqs:
            issues.append(
                _issue(
                    "B",
                    "faq_missing",
                    "warn",
                    f"{role} surface ({surface.page_type}) has no FAQs in the capture.",
                    surface=role,
                    url=surface.url,
                )
            )
        else:
            text = _faq_text(surface)
            missing_topics = [
                topic for topic, needles in FAQ_TOPICS.items() if not any(needle in text for needle in needles)
            ]
            severity = "pass" if not missing_topics else "warn"
            issues.append(
                _issue(
                    "B",
                    "faq_topics",
                    severity,
                    (
                        f"{role} FAQs cover cancellation, getting there, and access."
                        if not missing_topics
                        else f"{role} FAQs do not mention: {', '.join(missing_topics)}."
                    ),
                    surface=role,
                    missing_topics=missing_topics,
                )
            )
        if surface.page_type == "microbrand":
            if surface.not_official_venue_disclaimer is False:
                issues.append(
                    _issue(
                        "B",
                        "microbrand_disclaimer",
                        "warn",
                        f"The microbrand at {surface.url or role} does not show a "
                        "'not the official venue or operator site' line. "
                        "First-time visitors can read an attraction-branded domain as the operator.",
                        surface=role,
                        url=surface.url,
                        discloses_headout=surface.discloses_headout,
                    )
                )
            elif surface.not_official_venue_disclaimer is True:
                issues.append(
                    _issue(
                        "B",
                        "microbrand_disclaimer",
                        "pass",
                        f"{role} microbrand states it is not the official venue or operator site.",
                        surface=role,
                        url=surface.url,
                    )
                )
            if surface.discloses_headout is False:
                issues.append(
                    _issue(
                        "B",
                        "microbrand_headout_disclosure",
                        "fail",
                        f"{role} microbrand does not disclose that Headout operates the site.",
                        surface=role,
                        url=surface.url,
                    )
                )
    return issues


def intent_issues(
    *,
    scope: str,
    gate: str,
    means: dict[str, float],
    pass_at: float,
    warn_at: float,
    code: str,
) -> list[Issue]:
    issues = []
    for key, mean in sorted(means.items()):
        severity = rate_higher_is_better(mean, pass_at=pass_at, warn_at=warn_at)
        if severity == "pass":
            continue
        issues.append(
            _issue(
                gate,
                code,
                severity,
                f"{scope} '{key}' mean purchase intent is {mean:.2f} "
                f"(pass ≥ {pass_at}, warn ≥ {warn_at}).",
                key=key,
                mean=round(mean, 3),
                pass_at=pass_at,
                warn_at=warn_at,
            )
        )
    return issues
