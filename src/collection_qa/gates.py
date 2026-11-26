"""Gate A (post-assortment) and Gate B (post-content-lock).

Gate A looks at per-product intent, the price ladder by segment, competitor
notes, cannibalisation, and choice overload. Gate B looks at page-level intent
and the content checks (trust, FAQs, claims). Deterministic checks are filed
on the gate they belong to. Synthetic PI never blocks go-live.
"""

from __future__ import annotations

import re
from collections import defaultdict

import numpy as np

from collection_qa.checks import CheckResult, _result
from collection_qa.models import CollectionSpec, Product
from collection_qa.personas import Persona
from collection_qa.thresholds import (
    CANNIBAL_JACCARD,
    CANNIBAL_PRICE_RATIO,
    CHOICE_OVERLOAD_N,
    PI_PASS,
    PI_WARN,
    SEVERITY_RANK,
)

_STOP = {"from", "with", "and", "the", "for", "per", "via"}


def _tokens(title: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]+", title.lower()) if token not in _STOP and len(token) > 2}


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def cannibalisation_pairs(spec: CollectionSpec) -> list[dict]:
    products = spec.products
    token_map = {product.id: _tokens(product.title) for product in products}
    pairs: list[dict] = []
    for i, left in enumerate(products):
        for right in products[i + 1 :]:
            if left.price is None or right.price is None or left.price_unit != right.price_unit:
                continue
            high = max(left.price, right.price)
            low = min(left.price, right.price)
            if low <= 0 or high / low > CANNIBAL_PRICE_RATIO:
                continue
            if (left.duration or "") != (right.duration or ""):
                continue
            score = _jaccard(token_map[left.id], token_map[right.id])
            if score < CANNIBAL_JACCARD:
                continue
            pairs.append(
                {
                    "a": left.id,
                    "b": right.id,
                    "a_title": left.title,
                    "b_title": right.title,
                    "jaccard": round(score, 3),
                    "price_a": left.price,
                    "price_b": right.price,
                    "currency": left.currency,
                    "duration": left.duration,
                }
            )
    pairs.sort(key=lambda item: item["jaccard"], reverse=True)
    return pairs


def choice_overload(spec: CollectionSpec, product_means: dict[str, float] | None = None) -> CheckResult | None:
    count = len(spec.products)
    if count < CHOICE_OVERLOAD_N:
        return _result(
            "choice_overload",
            "pass",
            "A",
            f"{count} products is under the review trigger of {CHOICE_OVERLOAD_N}. That trigger is an assumption, not a Headout limit.",
        )
    spread = None
    if product_means:
        values = [product_means[p.id] for p in spec.products if p.id in product_means]
        if len(values) >= 2:
            spread = float(np.std(values))
    message = (
        f"{count} products on one collection. The review trigger is {CHOICE_OVERLOAD_N}, "
        "which is an assumption for this QA layer, not a Headout policy."
    )
    if spread is not None:
        message += f" Synthetic mean PI standard deviation across products is {spread:.2f}."
    return _result("choice_overload", "warn", "A", message, evidence={"n": count, "pi_std": spread})


def _pi_severity(mean: float) -> str:
    if mean >= PI_PASS:
        return "pass"
    if mean >= PI_WARN:
        return "warn"
    return "fail"


def synthetic_product_issues(product_means: dict[str, float], products: dict[str, Product]) -> list[CheckResult]:
    results: list[CheckResult] = []
    for product_id, mean in sorted(product_means.items()):
        severity = _pi_severity(mean)
        if severity == "pass":
            continue
        title = products[product_id].title if product_id in products else product_id
        results.append(
            CheckResult(
                id="synthetic_product_pi",
                severity=severity,
                gate="A",
                blocks_go_live=False,
                message=(
                    f"Synthetic mean booking intent for {title} is {mean:.2f}. "
                    f"Pass ≥ {PI_PASS}, warn ≥ {PI_WARN}, below that is a research fail. "
                    "These bands are uncalibrated and do not block go-live."
                ),
                product_ids=[product_id],
                evidence={"mean_pi": round(mean, 3)},
            )
        )
    return results


def synthetic_page_issue(mean: float | None) -> CheckResult | None:
    if mean is None:
        return None
    severity = _pi_severity(mean)
    return CheckResult(
        id="synthetic_page_pi",
        severity=severity,
        gate="B",
        blocks_go_live=False,
        message=(
            f"Synthetic mean booking intent for the page is {mean:.2f}. "
            f"Pass ≥ {PI_PASS}, warn ≥ {PI_WARN}. Uncalibrated; does not block go-live."
        ),
        evidence={"mean_pi": round(mean, 3)},
    )


def price_ladder_fit(
    spec: CollectionSpec,
    personas: list[Persona],
    means_by_product_and_persona: dict[tuple[str, str], float],
) -> list[CheckResult]:
    """Within one price unit, does a segment's intent rise toward the prices that fit it?"""
    results: list[CheckResult] = []
    by_persona = {persona.id: persona for persona in personas if not persona.ablated}
    for unit in ("per_person", "per_group"):
        products = [p for p in spec.products if p.price_unit == unit and p.price is not None]
        if len(products) < 4:
            continue
        products.sort(key=lambda product: product.price or 0)
        third = max(1, len(products) // 3)
        cheap = products[:third]
        expensive = products[-third:]
        for tier in ("budget", "luxury"):
            members = [persona_id for persona_id, persona in by_persona.items() if persona.budget_tier == tier]
            if len(members) < 3:
                continue
            def tier_mean(group: list[Product]) -> float:
                values = [
                    means_by_product_and_persona[(product.id, persona_id)]
                    for product in group
                    for persona_id in members
                    if (product.id, persona_id) in means_by_product_and_persona
                ]
                return float(np.mean(values)) if values else float("nan")

            cheap_mean = tier_mean(cheap)
            expensive_mean = tier_mean(expensive)
            if np.isnan(cheap_mean) or np.isnan(expensive_mean):
                continue
            gap = expensive_mean - cheap_mean
            severity = "pass"
            if tier == "budget" and gap > 0.15:
                severity = "warn"
            if tier == "luxury" and gap < -0.15:
                severity = "warn"
            results.append(
                _result(
                    "price_ladder_fit",
                    severity,
                    "A",
                    (
                        f"{tier} personas, {unit}: mean PI {cheap_mean:.2f} on the cheaper third "
                        f"and {expensive_mean:.2f} on the dearer third (gap {gap:+.2f}). "
                        "Budget intent should not rise with price; luxury intent should not fall. "
                        "This uses synthetic scores and does not block go-live."
                    ),
                    [product.id for product in cheap + expensive],
                    {
                        "tier": tier,
                        "unit": unit,
                        "cheap_mean": round(float(cheap_mean), 3),
                        "expensive_mean": round(float(expensive_mean), 3),
                    },
                )
            )
    return results


def rollup(checks: list[CheckResult], gate: str) -> str:
    relevant = [item for item in checks if item.gate in (gate, "both") and item.severity in ("warn", "fail")]
    if any(item.severity == "fail" and item.blocks_go_live for item in relevant):
        return "fail"
    if any(item.severity == "warn" for item in relevant):
        return "warn"
    return "pass"


def research_status(checks: list[CheckResult], gate: str) -> str:
    relevant = [
        item
        for item in checks
        if item.gate in (gate, "both") and item.id.startswith("synthetic_") and item.severity in ("warn", "fail", "pass")
    ]
    if not relevant:
        return "not_run"
    worst = max(SEVERITY_RANK[item.severity] for item in relevant)
    for name, rank in SEVERITY_RANK.items():
        if rank == worst:
            return name
    return "pass"


def top_and_bottom(means: dict[str, float], products: dict[str, Product], k: int = 3) -> dict:
    ordered = sorted(means.items(), key=lambda item: item[1], reverse=True)
    def pack(rows: list[tuple[str, float]]) -> list[dict]:
        packed = []
        for product_id, mean in rows:
            product = products.get(product_id)
            packed.append(
                {
                    "product_id": product_id,
                    "title": product.title if product else product_id,
                    "mean_pi": round(mean, 3),
                    "price": product.price if product else None,
                    "currency": product.currency if product else None,
                    "price_unit": product.price_unit if product else None,
                }
            )
        return packed

    return {"top": pack(ordered[:k]), "bottom": pack(list(reversed(ordered[-k:])))}


def segment_means(
    personas: list[Persona],
    product_ids: list[str],
    cell_means: dict[tuple[str, str], float],
    attribute: str,
) -> dict[str, dict[str, float]]:
    grouped: dict[str, list[Persona]] = defaultdict(list)
    for persona in personas:
        if persona.ablated:
            continue
        grouped[getattr(persona, attribute)].append(persona)
    output: dict[str, dict[str, float]] = {}
    for label, members in grouped.items():
        per_product: dict[str, float] = {}
        for product_id in product_ids:
            values = [cell_means[(product_id, persona.id)] for persona in members if (product_id, persona.id) in cell_means]
            if values:
                per_product[product_id] = float(np.mean(values))
        output[label] = per_product
    return output
