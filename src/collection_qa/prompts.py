"""Prompts for free-text booking intent.

The model is asked for prose, never for a 1–5 number. Direct numeric Likert
ratings are the failure mode the SSR paper documents.
"""

from __future__ import annotations

from collection_qa.models import CollectionSpec, Product
from collection_qa.personas import Persona

SYSTEM_PROMPT = (
    "You are taking part in a travel booking study. Impersonate the traveler described "
    "in the prompt and write the way that person would talk. Reply in first person with "
    "3 to 5 sentences about how likely you are to book, and why. Mention concrete details "
    "from the offer: price, duration, what is included, and anything that is confusing or "
    "hard to trust. Do not give a number, a star rating, or a score out of 5. Do not mention "
    "that you are a language model."
)


def _product_block(product: Product) -> str:
    inclusions = ", ".join(product.inclusions) if product.inclusions else f"({product.inclusions_status})"
    rating = "no published rating" if product.rating is None else f"{product.rating} from {product.review_count} reviews"
    return "\n".join(
        [
            f"Title: {product.title}",
            f"Type: {product.product_type}",
            f"Price: {product.price} {product.currency} {product.price_unit}"
            + (f" (original {product.original_price})" if product.original_price not in (None, product.price) else ""),
            f"Duration: {product.duration or 'not stated'}",
            f"Rating: {rating}",
            f"Cancellation: {product.cancellation or 'not stated'}",
            f"Pickup: {product.pickup or product.pickup_status}",
            f"Inclusions: {inclusions}",
            f"Features: {', '.join(product.features) or 'not stated'}",
            f"Accessibility note: {product.accessibility or 'not stated'}",
        ]
    )


def product_user(persona: Persona, product: Product, destination: str) -> str:
    return (
        f"Traveler: {persona.summary()}\n\n"
        f"You are looking at one experience in {destination}.\n"
        f"{_product_block(product)}\n\n"
        "How likely are you to book this experience?"
    )


def page_user(persona: Persona, spec: CollectionSpec) -> str:
    lines = [
        f"Traveler: {persona.summary()}",
        "",
        f"Page: {spec.page.url}",
        f"Page type: {spec.page_type}",
        f"Hero: {spec.page.hero}",
    ]
    if spec.page.meta_description:
        lines.append(f"Meta description: {spec.page.meta_description}")
    if spec.page.usps:
        lines.append("USPs: " + " | ".join(spec.page.usps))
    if spec.page.trust_signals:
        lines.append("Trust signals: " + " | ".join(spec.page.trust_signals))
    if spec.page.faqs:
        lines.append("FAQs:")
        for faq in spec.page.faqs:
            lines.append(f"- {faq.q} {faq.a}")
    else:
        lines.append("FAQs: none were confirmed on the fetched page.")
    lines.append("Experiences on the page:")
    for product in spec.products:
        lines.append(
            f"- {product.title} | {product.price} {product.currency} {product.price_unit} | "
            f"{product.duration or 'duration not stated'} | "
            f"rating {product.rating if product.rating is not None else 'n/a'} "
            f"({product.review_count or 0} reviews)"
        )
    lines.append("")
    lines.append(
        "How likely are you to book something from this page? Say what you would book, "
        "if anything, and what would stop you."
    )
    return "\n".join(lines)
