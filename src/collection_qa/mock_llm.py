"""Rule-based stand-in for the booking-intent LLM.

Used by --dry-run and by tests. The text is conditioned on the persona and the
product so SSR has ranking signal. An ablated persona gets the same middling
reaction for every product, which is the failure mode the SSR paper reports
when demographics are removed.

This is not a model of real travelers. Scorecards say so.
"""

from __future__ import annotations

from collection_qa.models import CollectionSpec, Product
from collection_qa.personas import Persona

# Per-person caps in the product's currency. Mock-only. Not an FX table.
_CAPS = {
    "USD": {"budget": 400.0, "mid": 900.0, "premium": 1800.0, "luxury": 8000.0},
    "NZD": {"budget": 250.0, "mid": 520.0, "premium": 1100.0, "luxury": 4500.0},
}
_PARTY = {"solo": 1.0, "couple": 2.0, "family_with_kids": 4.0, "friends": 3.0}


def _per_person_price(persona: Persona, product: Product) -> float | None:
    if product.price is None:
        return None
    if product.price_unit == "per_group":
        return product.price / _PARTY[persona.trip_type]
    return product.price


def fit_score(persona: Persona, product: Product) -> float:
    """0 = would not book, 1 = would book. Assumptions are local to the mock."""
    if persona.ablated:
        return 0.55
    score = 0.5
    caps = _CAPS.get(product.currency)
    unit = _per_person_price(persona, product)
    if caps and unit is not None:
        cap = caps[persona.budget_tier]
        if unit <= cap * 0.75:
            score += 0.22
        elif unit <= cap:
            score += 0.08
        elif unit <= cap * 1.5:
            score -= 0.16
        else:
            score -= 0.32
    tags = set(product.tags)
    hours = product.duration_hours_min or 0.0
    if "fly_in" in tags or "luxury" in tags:
        score += {"budget": -0.22, "mid": -0.05, "premium": 0.08, "luxury": 0.2}[persona.budget_tier]
    if hours >= 24 * 6:
        score += 0.12 if persona.planning_horizon == "months" else -0.18 if persona.planning_horizon == "last_minute" else 0
        if persona.trip_type == "family_with_kids":
            score -= 0.06
    elif hours and hours <= 20:
        score += 0.08 if persona.planning_horizon == "last_minute" else -0.04
    if "from_queenstown" in tags and (hours or 0) >= 10:
        score += 0.1 if persona.base == "queenstown" else -0.12 if persona.base == "te_anau" else 0
        if persona.trip_type == "family_with_kids":
            score -= 0.16
    if "from_te_anau" in tags:
        score += 0.12 if persona.base == "te_anau" else 0.02
    if "terminal_cruise" in tags and persona.base == "queenstown":
        score -= 0.08
    if persona.accessibility == "mobility":
        if product.accessibility and "not fully wheelchair" in product.accessibility.lower():
            score -= 0.4
        else:
            score -= 0.05
    if persona.experience == "first_timer" and product.multi_variant:
        score -= 0.04
    if product.review_count == 0:
        score -= 0.06
    return max(0.0, min(1.0, score))


def page_fit(persona: Persona, spec: CollectionSpec) -> float:
    if persona.ablated:
        return 0.55
    scores = [fit_score(persona, product) for product in spec.products]
    scores.sort(reverse=True)
    top = scores[:3] or [0.5]
    score = sum(top) / len(top)
    if not spec.page.faqs and persona.experience == "first_timer":
        score -= 0.1
    if spec.page_type == "microbrand" and persona.experience == "first_timer":
        score -= 0.04
    units = {product.price_unit for product in spec.products}
    if len(units) > 1 and persona.budget_tier == "budget":
        score -= 0.06
    return max(0.0, min(1.0, score))


def _bucket(score: float) -> int:
    if score < 0.28:
        return 1
    if score < 0.45:
        return 2
    if score < 0.58:
        return 3
    if score < 0.74:
        return 4
    return 5


def _money(product: Product) -> str:
    if product.price is None:
        return "the unpublished price"
    return f"{product.price:g} {product.currency} {product.price_unit.replace('_', ' ')}"


def react_product(persona: Persona, product: Product) -> str:
    bucket = _bucket(fit_score(persona, product))
    money = _money(product)
    duration = product.duration or "an unstated duration"
    who = "I" if persona.ablated else _who(persona)
    if bucket == 1:
        return (
            f"I would not book this. {money} for {duration} is the wrong trip for {who}, "
            f"and {product.title} does not solve the way we actually travel."
        )
    if bucket == 2:
        return (
            f"I probably would not book this. {product.title} is {duration} at {money}, "
            f"which is a stretch for {who}, so I would keep looking rather than book it."
        )
    if bucket == 3:
        return (
            f"I am unsure about {product.title}. {money} and {duration} could work for {who}, "
            "but I am not convinced the card tells me what I would actually get."
        )
    if bucket == 4:
        return (
            f"I would probably book this. {product.title} at {money} for {duration} fits this trip "
            f"for {who}, as long as the inclusions on the card are the ones in the booking."
        )
    return (
        f"I would book this. {product.title} at {money} for {duration} is exactly the experience "
        f"{who} came for, and I am ready to book it."
    )


def react_page(persona: Persona, spec: CollectionSpec) -> str:
    bucket = _bucket(page_fit(persona, spec))
    who = "I" if persona.ablated else _who(persona)
    if bucket == 1:
        return (
            f"I would not book from this page. The mix of {spec.name} options does not fit {who}, "
            "and I would leave rather than pick one."
        )
    if bucket == 2:
        return (
            f"I probably would not book from this {spec.name} page. A few titles are close for {who}, "
            "but I am unlikely to book until the prices and the plan are easier to compare."
        )
    if bucket == 3:
        return (
            f"I am unsure about booking from this page. {spec.name} is why {who} is looking, "
            "but I am not convinced which card is the one to reserve."
        )
    if bucket == 4:
        return (
            f"I would probably book from this page. There is an option that fits this trip for {who}, "
            f"and the {spec.page_type.replace('_', ' ')} gives me enough to choose."
        )
    return (
        f"I would book from this page. {spec.name} has the experience {who} wants, "
        "and I am ready to book it."
    )


def _who(persona: Persona) -> str:
    party = {
        "solo": "me traveling alone",
        "couple": "the two of us",
        "family_with_kids": "our family with kids",
        "friends": "our group of friends",
    }[persona.trip_type]
    return f"{party} on a {persona.budget_tier} budget"
