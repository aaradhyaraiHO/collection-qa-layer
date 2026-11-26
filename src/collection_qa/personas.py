"""Traveler persona sampling.

Default weights are assumptions, labeled on every persona. Safaris from Nairobi
and Milford Sound day trips do not share an audience: the Mara weights put more
mass on couples booking months ahead at mid/premium budgets; the Milford weights
put more mass on shorter planning horizons, budget and mid tiers, and on
Queenstown versus Te Anau as the start point. A collection spec may override
any attribute's weights.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

ASSUMPTION_BASIS = (
    "assumption: default traveler mix for this collection, not a Headout panel or booking extract"
)

# Attribute -> {value: weight}. Weights sum to 1.
WeightTable = dict[str, dict[str, float]]


def _w(**pairs: float) -> dict[str, float]:
    total = sum(pairs.values())
    if abs(total - 1.0) > 1e-9:
        raise ValueError(f"weights sum to {total}, not 1")
    return dict(pairs)


MARA_WEIGHTS: WeightTable = {
    "source_market": _w(US=0.28, UK=0.22, DE=0.12, IN=0.12, AU=0.08, AE=0.08, KE=0.05, other=0.05),
    "age_band": _w(**{"18-24": 0.06, "25-34": 0.22, "35-44": 0.30, "45-54": 0.22, "55-64": 0.14, "65+": 0.06}),
    "trip_type": _w(solo=0.12, couple=0.42, family_with_kids=0.28, friends=0.18),
    "budget_tier": _w(budget=0.12, mid=0.42, premium=0.30, luxury=0.16),
    "planning_horizon": _w(last_minute=0.08, weeks=0.32, months=0.60),
    "experience": _w(first_timer=0.74, repeat=0.26),
    "accessibility": _w(none=0.93, mobility=0.05, other=0.02),
    "interest": _w(big_five=0.34, migration=0.22, photography=0.18, culture=0.14, comfort=0.12),
    "device": _w(mobile=0.64, desktop=0.36),
    "channel": _w(organic=0.30, paid=0.42, direct=0.18, referral=0.10),
    "base": _w(nairobi=0.78, already_in_kenya=0.14, international_arrival=0.08),
}

MILFORD_WEIGHTS: WeightTable = {
    "source_market": _w(AU=0.24, US=0.16, UK=0.14, NZ=0.14, CN=0.10, DE=0.10, IN=0.06, other=0.06),
    "age_band": _w(**{"18-24": 0.16, "25-34": 0.30, "35-44": 0.22, "45-54": 0.16, "55-64": 0.10, "65+": 0.06}),
    "trip_type": _w(solo=0.20, couple=0.34, family_with_kids=0.22, friends=0.24),
    "budget_tier": _w(budget=0.30, mid=0.46, premium=0.18, luxury=0.06),
    "planning_horizon": _w(last_minute=0.28, weeks=0.47, months=0.25),
    "experience": _w(first_timer=0.82, repeat=0.18),
    "accessibility": _w(none=0.94, mobility=0.04, other=0.02),
    "interest": _w(scenery=0.40, photography=0.22, wildlife=0.16, hiking=0.14, ease=0.08),
    "device": _w(mobile=0.70, desktop=0.30),
    "channel": _w(organic=0.28, paid=0.48, direct=0.14, referral=0.10),
    "base": _w(queenstown=0.58, te_anau=0.27, self_drive=0.15),
}

GENERIC_WEIGHTS: WeightTable = {
    "source_market": _w(US=0.25, UK=0.15, DE=0.10, AU=0.10, IN=0.10, other=0.30),
    "age_band": _w(**{"18-24": 0.12, "25-34": 0.28, "35-44": 0.24, "45-54": 0.18, "55-64": 0.12, "65+": 0.06}),
    "trip_type": _w(solo=0.18, couple=0.40, family_with_kids=0.24, friends=0.18),
    "budget_tier": _w(budget=0.22, mid=0.46, premium=0.22, luxury=0.10),
    "planning_horizon": _w(last_minute=0.20, weeks=0.45, months=0.35),
    "experience": _w(first_timer=0.70, repeat=0.30),
    "accessibility": _w(none=0.94, mobility=0.04, other=0.02),
    "interest": _w(highlights=0.40, value=0.25, photography=0.20, ease=0.15),
    "device": _w(mobile=0.66, desktop=0.34),
    "channel": _w(organic=0.34, paid=0.40, direct=0.16, referral=0.10),
    "base": _w(destination=0.70, day_trip_from_hub=0.30),
}

COLLECTION_DEFAULTS: dict[str, WeightTable] = {
    "masai-mara": MARA_WEIGHTS,
    "milford-sound": MILFORD_WEIGHTS,
}


def validate_weights(weights: WeightTable) -> None:
    expected = set(GENERIC_WEIGHTS)
    missing = expected - set(weights)
    if missing:
        raise ValueError(f"persona weights missing attributes: {sorted(missing)}")
    for name, table in weights.items():
        if not table:
            raise ValueError(f"persona weights for {name} are empty")
        total = sum(table.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"persona weights for {name} sum to {total}, not 1")
        if any(value < 0 for value in table.values()):
            raise ValueError(f"persona weights for {name} contain a negative value")


def default_weights(collection_id: str) -> tuple[WeightTable, str]:
    if collection_id in COLLECTION_DEFAULTS:
        basis = (
            f"{ASSUMPTION_BASIS}. Profile '{collection_id}' "
            "is the built-in mix for this pilot, not measured demand."
        )
        return COLLECTION_DEFAULTS[collection_id], basis
    basis = (
        f"{ASSUMPTION_BASIS}. Profile 'generic' was used because '{collection_id}' "
        "has no built-in mix."
    )
    return GENERIC_WEIGHTS, basis


def merge_weights(base: WeightTable, override: dict | None) -> WeightTable:
    if not override:
        return base
    merged: WeightTable = {key: dict(value) for key, value in base.items()}
    for name, table in override.items():
        if name not in merged:
            raise ValueError(f"unknown persona attribute '{name}'")
        merged[name] = {str(k): float(v) for k, v in table.items()}
    validate_weights(merged)
    return merged


def _draw(rng: random.Random, table: dict[str, float]) -> str:
    labels = list(table)
    weights = [table[label] for label in labels]
    return rng.choices(labels, weights=weights, k=1)[0]


@dataclass
class Persona:
    id: str
    source_market: str
    age_band: str
    trip_type: str
    budget_tier: str
    planning_horizon: str
    experience: str
    accessibility: str
    interests: list[str]
    device: str
    channel: str
    base: str
    assumption_basis: str
    ablated: bool = False

    def summary(self) -> str:
        if self.ablated:
            return "A traveler. No age, party, budget, market, or other demographic detail is provided."
        interests = ", ".join(self.interests)
        return (
            f"{self.age_band} traveler from {self.source_market}, traveling as {self.trip_type}, "
            f"{self.budget_tier} budget, planning horizon {self.planning_horizon}, "
            f"{self.experience.replace('_', ' ')}, accessibility {self.accessibility}, "
            f"interest {interests}, starting point {self.base}, "
            f"on {self.device} via {self.channel}."
        )

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "source_market": self.source_market,
            "age_band": self.age_band,
            "trip_type": self.trip_type,
            "budget_tier": self.budget_tier,
            "planning_horizon": self.planning_horizon,
            "experience": self.experience,
            "accessibility": self.accessibility,
            "interests": list(self.interests),
            "device": self.device,
            "channel": self.channel,
            "base": self.base,
            "assumption_basis": self.assumption_basis,
            "ablated": self.ablated,
        }


@dataclass
class PersonaPanel:
    personas: list[Persona]
    weights: WeightTable
    assumption_basis: str
    seed: int

    def by_id(self) -> dict[str, Persona]:
        return {persona.id: persona for persona in self.personas}

    def counts(self, attribute: str) -> dict[str, int]:
        counts: dict[str, int] = {}
        for persona in self.personas:
            value = getattr(persona, attribute if attribute != "interest" else "interests")
            if attribute == "interest":
                value = persona.interests[0]
            counts[value] = counts.get(value, 0) + 1
        return counts


def sample_personas(
    collection_id: str,
    n: int,
    *,
    seed: int = 20261126,
    override: dict | None = None,
    ablate: bool = False,
) -> PersonaPanel:
    if n < 1:
        raise ValueError("persona count must be at least 1")
    base, basis = default_weights(collection_id)
    weights = merge_weights(base, override)
    if override:
        basis += " Spec file overrides are applied on top of that profile."
    rng = random.Random(seed)
    personas: list[Persona] = []
    for index in range(n):
        interest = _draw(rng, weights["interest"])
        personas.append(
            Persona(
                id=f"{collection_id}-{index + 1:03d}",
                source_market=_draw(rng, weights["source_market"]),
                age_band=_draw(rng, weights["age_band"]),
                trip_type=_draw(rng, weights["trip_type"]),
                budget_tier=_draw(rng, weights["budget_tier"]),
                planning_horizon=_draw(rng, weights["planning_horizon"]),
                experience=_draw(rng, weights["experience"]),
                accessibility=_draw(rng, weights["accessibility"]),
                interests=[interest],
                device=_draw(rng, weights["device"]),
                channel=_draw(rng, weights["channel"]),
                base=_draw(rng, weights["base"]),
                assumption_basis=basis,
                ablated=ablate,
            )
        )
    return PersonaPanel(personas=personas, weights=weights, assumption_basis=basis, seed=seed)
