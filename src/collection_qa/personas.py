"""Synthetic traveler panels.

Weights are priors, not Headout booking mix. Safaris and fjord day-cruises do
not share an audience, so the two built-in profiles differ on purpose. Every
default is tagged as an assumption. A collection spec may override axes.

The paper's no-demographics ablation is the reason these fields exist: without
a persona, SSR distributions can look human while product ranking collapses.
"""

from __future__ import annotations

import random
from typing import Mapping

from pydantic import BaseModel, Field

ASSUMPTION_NOTE = (
    "Assumption, not measured Headout demand. Replace with booking-mix weights "
    "before a segment gap is used as a go-live gate. Axes are sampled "
    "independently; real travelers are correlated."
)

# label -> weight. Weights need not be pre-normalized.
SAFARI_WEIGHTS: dict[str, dict[str, float]] = {
    "source_market": {
        "United States": 0.22,
        "United Kingdom": 0.20,
        "Germany": 0.12,
        "India": 0.14,
        "United Arab Emirates": 0.10,
        "France": 0.08,
        "Australia": 0.08,
        "China": 0.06,
    },
    "age_band": {
        "18-24": 0.06,
        "25-34": 0.24,
        "35-44": 0.28,
        "45-54": 0.22,
        "55-64": 0.14,
        "65+": 0.06,
    },
    "trip_type": {
        "solo": 0.18,
        "couple": 0.42,
        "family_with_kids": 0.22,
        "friends": 0.18,
    },
    "budget_tier": {"budget": 0.15, "mid": 0.35, "premium": 0.30, "luxury": 0.20},
    "planning_horizon": {
        "last_minute": 0.08,
        "weeks_1_4": 0.20,
        "months_1_3": 0.42,
        "months_3_plus": 0.30,
    },
    "experience": {"first_timer": 0.75, "repeat": 0.25},
    "accessibility": {"none": 0.93, "mobility": 0.05, "sensory": 0.02},
    "device_channel": {"mobile_web": 0.60, "desktop": 0.32, "app": 0.08},
}

FJORD_CRUISE_WEIGHTS: dict[str, dict[str, float]] = {
    "source_market": {
        "Australia": 0.26,
        "United States": 0.16,
        "United Kingdom": 0.12,
        "China": 0.12,
        "New Zealand": 0.12,
        "Germany": 0.08,
        "Japan": 0.08,
        "India": 0.06,
    },
    "age_band": {
        "18-24": 0.12,
        "25-34": 0.26,
        "35-44": 0.22,
        "45-54": 0.18,
        "55-64": 0.14,
        "65+": 0.08,
    },
    "trip_type": {
        "solo": 0.16,
        "couple": 0.36,
        "family_with_kids": 0.26,
        "friends": 0.22,
    },
    "budget_tier": {"budget": 0.28, "mid": 0.42, "premium": 0.22, "luxury": 0.08},
    "planning_horizon": {
        "last_minute": 0.18,
        "weeks_1_4": 0.34,
        "months_1_3": 0.32,
        "months_3_plus": 0.16,
    },
    "experience": {"first_timer": 0.82, "repeat": 0.18},
    "accessibility": {"none": 0.90, "mobility": 0.08, "sensory": 0.02},
    "device_channel": {"mobile_web": 0.70, "desktop": 0.22, "app": 0.08},
}

SAFARI_INTERESTS: dict[str, float] = {
    "big_five": 0.22,
    "great_migration": 0.18,
    "photography": 0.16,
    "maasai_culture": 0.12,
    "luxury_camps": 0.12,
    "birding": 0.08,
    "balloon": 0.12,
}

FJORD_INTERESTS: dict[str, float] = {
    "scenery": 0.24,
    "photography": 0.18,
    "wildlife": 0.16,
    "hiking": 0.10,
    "short_on_time": 0.14,
    "weather_comfort": 0.10,
    "food_onboard": 0.08,
}

PROFILES = {
    "safari": (SAFARI_WEIGHTS, SAFARI_INTERESTS),
    "fjord_cruise": (FJORD_CRUISE_WEIGHTS, FJORD_INTERESTS),
}

REQUIRED_AXES = (
    "source_market",
    "age_band",
    "trip_type",
    "budget_tier",
    "planning_horizon",
    "experience",
    "accessibility",
    "device_channel",
)


class Persona(BaseModel):
    id: str
    source_market: str
    age_band: str
    trip_type: str
    budget_tier: str
    planning_horizon: str
    experience: str
    accessibility: str
    interests: list[str]
    device_channel: str
    profile: str
    weights_are_assumptions: bool = True

    def label(self) -> str:
        access = "" if self.accessibility == "none" else f", accessibility: {self.accessibility}"
        return (
            f"{self.age_band} {self.trip_type.replace('_', ' ')} from {self.source_market}, "
            f"{self.budget_tier} budget, {self.experience.replace('_', ' ')}, "
            f"planning {self.planning_horizon.replace('_', ' ')}, via {self.device_channel}"
            f"{access}; interests: {', '.join(self.interests)}"
        )


class PersonaPanel(BaseModel):
    profile: str
    assumption_note: str = ASSUMPTION_NOTE
    weights: dict[str, dict[str, float]]
    interest_weights: dict[str, float]
    personas: list[Persona] = Field(default_factory=list)


def _normalize(weights: Mapping[str, float]) -> dict[str, float]:
    total = float(sum(weights.values()))
    if total <= 0:
        raise ValueError("weights must sum to a positive number")
    return {key: float(value) / total for key, value in weights.items()}


def _choice(rng: random.Random, weights: Mapping[str, float]) -> str:
    labels = list(weights)
    return rng.choices(labels, weights=[weights[label] for label in labels], k=1)[0]


def _sample_interests(rng: random.Random, weights: Mapping[str, float], k: int = 2) -> list[str]:
    labels = list(weights)
    picked: list[str] = []
    pool = dict(weights)
    for _ in range(min(k, len(labels))):
        choice = _choice(rng, pool)
        picked.append(choice)
        del pool[choice]
        if not pool:
            break
    return picked


def resolve_weights(
    profile: str,
    override: dict | None = None,
) -> tuple[dict[str, dict[str, float]], dict[str, float]]:
    if profile == "custom" and not override:
        raise ValueError("audience_profile 'custom' requires persona_weights on the spec")
    if profile not in PROFILES and profile != "custom":
        raise ValueError(f"unknown audience profile {profile!r}")
    base_axes, base_interests = PROFILES.get(profile, ({}, {}))
    axes = {name: dict(values) for name, values in base_axes.items()}
    interests = dict(base_interests)
    if override:
        for name, values in override.get("axes", {}).items():
            axes[name] = dict(values)
        if "interests" in override:
            interests = dict(override["interests"])
    missing = [name for name in REQUIRED_AXES if name not in axes]
    if missing:
        raise ValueError(f"persona weights missing axes: {missing}")
    return axes, interests


def sample_personas(
    *,
    n: int,
    profile: str,
    seed: int,
    override: dict | None = None,
) -> PersonaPanel:
    axes, interests = resolve_weights(profile, override)
    normalized = {name: _normalize(values) for name, values in axes.items()}
    rng = random.Random(seed)
    personas: list[Persona] = []
    for index in range(n):
        personas.append(
            Persona(
                id=f"p{index + 1:04d}",
                source_market=_choice(rng, normalized["source_market"]),
                age_band=_choice(rng, normalized["age_band"]),
                trip_type=_choice(rng, normalized["trip_type"]),
                budget_tier=_choice(rng, normalized["budget_tier"]),
                planning_horizon=_choice(rng, normalized["planning_horizon"]),
                experience=_choice(rng, normalized["experience"]),
                accessibility=_choice(rng, normalized["accessibility"]),
                interests=_sample_interests(rng, interests),
                device_channel=_choice(rng, normalized["device_channel"]),
                profile=profile,
            )
        )
    return PersonaPanel(
        profile=profile,
        weights=normalized,
        interest_weights=_normalize(interests) if interests else {},
        personas=personas,
    )
