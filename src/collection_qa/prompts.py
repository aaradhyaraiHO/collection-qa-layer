"""Prompts for free-text booking intent.

The model is asked for prose, never a 1-5 number. Direct Likert ratings are the
failure mode in arXiv 2510.08338: models pile up on 3 and almost never use 1 or 5.
"""

from __future__ import annotations

from collection_qa.models import CollectionSpec, Product, Surface
from collection_qa.personas import Persona

SYSTEM_PROMPT = (
    "You are taking part in a travel-booking research interview. "
    "Impersonate the traveler described in the question. "
    "Speak in the first person as that traveler, not as an analyst. "
    "Reply in English only, even if this traveler would normally speak another language. "
    "The sentences used to score your answer are English, so a reply in another language cannot be scored. "
    "Use 2 to 4 sentences and no more than 80 words, then stop. "
    "Name what appeals to you and what would stop you. "
    "Do not reply with a number, a star rating, or a Likert score. "
    "Do not mention that you are a language model."
)


def _product_block(product: Product) -> str:
    lines = [
        f"Product: {product.title}",
        f"Type: {product.type}",
        f"Positioning: {product.positioning}",
    ]
    if product.price is None:
        lines.append(
            "Price: not shown on the page we captured"
            + (f" ({product.price_label})" if product.price_label else "")
        )
    else:
        label = product.price_label or "from"
        lines.append(f"Price: {label} {product.price:g} {product.currency or ''}".rstrip())
    if product.duration:
        lines.append(f"Duration: {product.duration}")
    if product.operator:
        lines.append(f"Operator named on the listing: {product.operator}")
    else:
        lines.append("Operator named on the listing: not stated")
    if product.rating is not None:
        reviews = f" from {product.review_count} reviews" if product.review_count else ""
        lines.append(f"Rating: {product.rating}/5{reviews}")
    lines.append("Features: " + ("; ".join(product.features) if product.features else "not stated"))
    lines.append("Inclusions: " + ("; ".join(product.inclusions) if product.inclusions else "not stated"))
    lines.append("Exclusions: " + ("; ".join(product.exclusions) if product.exclusions else "not stated"))
    lines.append(
        "Pickup: "
        + (product.pickup if product.pickup else f"status {product.pickup_status}, no detail written")
    )
    lines.append("Cancellation: " + (product.cancellation or "not stated"))
    if product.notes:
        lines.append("Notes from the page capture: " + " | ".join(product.notes))
    return "\n".join(lines)


def _surface_block(spec: CollectionSpec, surface: Surface, role: str) -> str:
    faqs = surface.faqs[:8]
    faq_text = (
        "\n".join(f"- Q: {item.question} A: {item.answer}" for item in faqs)
        if faqs
        else "- none captured"
    )
    products = "\n".join(
        f"- {product.title} | {product.type} | "
        + (
            f"{product.price:g} {product.currency}"
            if product.price is not None
            else "price not shown"
        )
        + (f" | {product.duration}" if product.duration else "")
        for product in spec.products
    )
    trust = "\n".join(f"- {item}" for item in surface.trust_signals) or "- none captured"
    usps = "\n".join(f"- {item}" for item in surface.usps) or "- none captured"
    disclaimer = surface.not_official_venue_disclaimer
    return "\n".join(
        [
            f"Page role: {role}",
            f"Page type: {surface.page_type}",
            f"URL: {surface.url or 'unknown'}",
            f"Collection: {spec.name} ({spec.destination})",
            f"Hero title: {surface.hero_title}",
            f"Hero copy: {surface.hero_copy}",
            f"USPs:\n{usps}",
            f"Trust signals:\n{trust}",
            f"Headout identity disclosed on this surface: {surface.discloses_headout}",
            f"Explicit 'not the official venue/operator site' disclaimer observed: {disclaimer}",
            f"Authorized-partner claim observed: {surface.authorized_partner_claim}",
            f"FAQs:\n{faq_text}",
            f"Products on the collection ({len(spec.products)}):\n{products}",
        ]
    )


def persona_preamble(persona: Persona) -> str:
    access = (
        "No accessibility need called out."
        if persona.accessibility == "none"
        else f"Accessibility need: {persona.accessibility}."
    )
    return "\n".join(
        [
            "Traveler to impersonate:",
            f"- Source market: {persona.source_market}",
            f"- Age band: {persona.age_band}",
            f"- Trip party: {persona.trip_type.replace('_', ' ')}",
            f"- Budget tier: {persona.budget_tier}",
            f"- Planning horizon: {persona.planning_horizon.replace('_', ' ')}",
            f"- Experience with this kind of trip: {persona.experience.replace('_', ' ')}",
            f"- {access}",
            f"- Interests: {', '.join(persona.interests)}",
            f"- Booking on: {persona.device_channel.replace('_', ' ')}",
        ]
    )


def product_prompt(persona: Persona, spec: CollectionSpec, product: Product) -> str:
    return "\n\n".join(
        [
            persona_preamble(persona),
            f"You are looking at one experience on a {spec.name} collection page before it is your turn to book.",
            _product_block(product),
            "How likely are you to book this experience, and why?",
        ]
    )


def page_prompt(persona: Persona, spec: CollectionSpec, surface: Surface, role: str) -> str:
    return "\n\n".join(
        [
            persona_preamble(persona),
            "You landed on this collection page and you are deciding whether to book something from it.",
            _surface_block(spec, surface, role),
            "How likely are you to book from this page, and why?",
        ]
    )
