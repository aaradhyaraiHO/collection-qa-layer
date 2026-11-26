"""Anthropic client with a sqlite cache, plus a deterministic mock writer.

Mock mode does not call the network. It writes a short first-person reaction
whose wording is anchored to a heuristic 1-5 score so a lexical embedder can
recover a spread of ratings. Those reactions are templates, not Claude, and
every scorecard labels them MOCK.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import threading
from dataclasses import dataclass

from collection_qa.anchors import ANCHOR_SETS
from collection_qa.models import CollectionSpec, Product, Surface
from collection_qa.personas import Persona
from collection_qa.prompts import SYSTEM_PROMPT, page_prompt, product_prompt

TIER_RANK = {"budget": 0, "mid": 1, "premium": 2, "luxury": 3}


@dataclass
class LLMResult:
    text: str
    input_tokens: int
    output_tokens: int
    cached: bool
    generator: str


@dataclass
class LLMClient:
    model: str
    mock: bool
    temperature: float = 0.5
    max_tokens: int = 320
    cache_path: str | None = None
    api_key: str | None = None

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self.calls = 0
        self.cache_hits = 0
        self.input_tokens = 0
        self.output_tokens = 0
        if self.cache_path:
            with self._connect() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS llm_cache (
                        key TEXT PRIMARY KEY,
                        response TEXT NOT NULL,
                        input_tokens INTEGER NOT NULL,
                        output_tokens INTEGER NOT NULL
                    )
                    """
                )

    def _connect(self) -> sqlite3.Connection:
        assert self.cache_path
        return sqlite3.connect(self.cache_path, timeout=30)

    def complete(
        self,
        *,
        persona: Persona,
        spec: CollectionSpec,
        product: Product | None,
        surface: Surface | None,
        surface_role: str | None,
        completion_index: int,
    ) -> LLMResult:
        if product is not None:
            user = product_prompt(persona, spec, product)
        else:
            assert surface is not None and surface_role is not None
            user = page_prompt(persona, spec, surface, surface_role)
        key = _cache_key(
            model=self.model,
            mock=self.mock,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            user=user,
            completion_index=completion_index,
        )
        cached = self._read_cache(key)
        if cached is not None:
            self.cache_hits += 1
            self.input_tokens += cached.input_tokens
            self.output_tokens += cached.output_tokens
            return cached

        if self.mock:
            text = mock_reaction(
                persona=persona,
                spec=spec,
                product=product,
                surface=surface,
                completion_index=completion_index,
            )
            result = LLMResult(
                text=text,
                input_tokens=_approx_tokens(SYSTEM_PROMPT + user),
                output_tokens=_approx_tokens(text),
                cached=False,
                generator="mock-template",
            )
        else:
            result = self._anthropic(user)
        self.calls += 1
        self.input_tokens += result.input_tokens
        self.output_tokens += result.output_tokens
        self._write_cache(key, result)
        return result

    def _read_cache(self, key: str) -> LLMResult | None:
        if not self.cache_path:
            return None
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "SELECT response, input_tokens, output_tokens FROM llm_cache WHERE key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return LLMResult(
            text=row[0],
            input_tokens=row[1],
            output_tokens=row[2],
            cached=True,
            generator="mock-template" if self.mock else "anthropic",
        )

    def _write_cache(self, key: str, result: LLMResult) -> None:
        if not self.cache_path:
            return
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO llm_cache (key, response, input_tokens, output_tokens)
                VALUES (?, ?, ?, ?)
                """,
                (key, result.text, result.input_tokens, result.output_tokens),
            )

    def _anthropic(self, user: str) -> LLMResult:
        import anthropic

        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Re-run with --mock to use template reactions."
            )
        client = anthropic.Anthropic(api_key=key)
        message = client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user}],
        )
        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        ).strip()
        usage = message.usage
        return LLMResult(
            text=text,
            input_tokens=int(usage.input_tokens),
            output_tokens=int(usage.output_tokens),
            cached=False,
            generator="anthropic",
        )


def _cache_key(**parts: object) -> str:
    payload = repr(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _stable_id(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:8], 16)


def _band_tier(spec: CollectionSpec, price: float) -> str | None:
    if spec.price_bands is None:
        return None
    for band in spec.price_bands.tiers:
        if band.min_price <= price < band.max_price:
            return band.tier
    return None


def heuristic_score(
    persona: Persona,
    spec: CollectionSpec,
    product: Product | None,
    surface: Surface | None,
) -> tuple[int, list[str]]:
    """A transparent stand-in used only by mock mode. Not a model of demand."""
    score = 3.9
    reasons: list[str] = []
    if product is not None:
        product_tier = None
        if product.price is not None:
            product_tier = _band_tier(spec, product.price)
        elif product.positioning not in {"unknown", "mixed"}:
            product_tier = product.positioning
        if product.price is None:
            score -= 0.3
            reasons.append("I cannot see a clear price, so I hesitate")
        if product_tier in TIER_RANK:
            gap = TIER_RANK[product_tier] - TIER_RANK[persona.budget_tier]
            if gap >= 2:
                score -= 1.8
                reasons.append("the price sits well above what I planned to spend")
            elif gap == 1:
                score -= 0.6
                reasons.append("it is a step more expensive than I expected")
            elif gap <= -2:
                score -= 0.5
                reasons.append("it looks too basic for the kind of trip I want")
            else:
                score += 0.35
                reasons.append("the price level matches what I wanted to spend")

        hours = product.duration_hours_max or product.duration_hours_min or 0
        if persona.trip_type == "family_with_kids" and hours >= 14 and (product.days_min or 1) <= 1:
            score -= 1.3
            reasons.append("a very long single day is hard with kids")
        if persona.trip_type == "family_with_kids" and "private" in product.type:
            score += 0.45
            reasons.append("a private vehicle lets us keep our own pace with the kids")
        if persona.accessibility != "none" and not product.accessibility_noted:
            score -= 1.15
            reasons.append("I cannot tell whether this works with my access needs")
        if not product.cancellation:
            score -= 0.4
            reasons.append("cancellation terms are missing")
        else:
            score += 0.2
            reasons.append("I can see a cancellation policy")
        if product.pickup_status == "unknown":
            score -= 0.25
            reasons.append("pickup is not explained")
        if persona.experience == "first_timer" and product.inclusions:
            score += 0.25
            reasons.append("the inclusions are written out, which helps me as a first-timer")
        if any("exclud" in item.lower() and "park" in item.lower() for item in product.exclusions):
            score -= 0.9 if persona.budget_tier == "budget" else 0.35
            reasons.append("park fees on top of the headline price worry me")
        if persona.experience == "repeat" and product.positioning in {"budget", "mid"}:
            score -= 0.25
            reasons.append("I have done the standard version and want something more specific")
        if "photography" in persona.interests and any(
            "view" in feature.lower() or "deck" in feature.lower() or "photo" in feature.lower()
            for feature in product.features
        ):
            score += 0.2
            reasons.append("the viewing setup matters to me for photos")
    else:
        assert surface is not None
        if len(surface.faqs) >= 4:
            score += 0.35
            reasons.append("the page answers practical questions")
        else:
            score -= 0.45
            reasons.append("I still have practical questions the page does not answer")
        if len(surface.trust_signals) >= 2:
            score += 0.2
            reasons.append("there are visible trust cues")
        if surface.page_type == "microbrand" and surface.not_official_venue_disclaimer is False:
            if persona.experience == "first_timer":
                score -= 0.65
                reasons.append(
                    "I cannot tell whether this site is the operator or a reseller"
                )
            else:
                score -= 0.25
                reasons.append("the site looks branded around the place but I know to check who operates it")
        if len(spec.products) > 12 and persona.experience == "first_timer":
            score -= 0.4
            reasons.append("there are too many choices for a first look")
        missing_price = sum(1 for product in spec.products if product.price is None)
        if spec.products and missing_price / len(spec.products) > 0.5:
            score -= 0.45
            reasons.append("most prices are missing, so I cannot compare")

    if persona.planning_horizon == "last_minute" and product is not None and product.cancellation:
        score += 0.15
    clamped = max(1, min(5, int(round(score))))
    if not reasons:
        reasons.append("nothing on the page settles it for me")
    return clamped, reasons


def mock_reaction(
    *,
    persona: Persona,
    spec: CollectionSpec,
    product: Product | None,
    surface: Surface | None,
    completion_index: int,
) -> str:
    score, reasons = heuristic_score(persona, spec, product, surface)
    set_index = (completion_index + _stable_id(persona.id)) % len(ANCHOR_SETS)
    anchor = ANCHOR_SETS[set_index][score - 1]
    second = ANCHOR_SETS[(set_index + 1) % len(ANCHOR_SETS)][score - 1]
    focus = product.title if product is not None else (surface.hero_title if surface else spec.name)
    reason = reasons[0]
    return (
        f"{anchor} {second} Looking at {focus}, {reason}. "
        f"I am a {persona.age_band} traveler from {persona.source_market} "
        f"on a {persona.trip_type.replace('_', ' ')} trip, {persona.budget_tier} budget, "
        f"{persona.experience.replace('_', ' ')}."
    )
