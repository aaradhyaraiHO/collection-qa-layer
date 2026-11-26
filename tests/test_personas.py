import random

import pytest

from collection_qa.personas import (
    ASSUMPTION_NOTE,
    FJORD_CRUISE_WEIGHTS,
    SAFARI_WEIGHTS,
    sample_personas,
)


def _share(personas, field, value):
    return sum(getattr(persona, field) == value for persona in personas) / len(personas)


def test_sample_is_reproducible_and_labeled_as_an_assumption():
    first = sample_personas(n=40, profile="safari", seed=11)
    second = sample_personas(n=40, profile="safari", seed=11)
    assert [persona.model_dump() for persona in first.personas] == [
        persona.model_dump() for persona in second.personas
    ]
    assert first.assumption_note == ASSUMPTION_NOTE
    assert all(persona.weights_are_assumptions for persona in first.personas)


def test_required_fields_are_filled():
    panel = sample_personas(n=25, profile="fjord_cruise", seed=3)
    for persona in panel.personas:
        assert persona.source_market
        assert persona.age_band
        assert persona.trip_type in {"solo", "couple", "family_with_kids", "friends"}
        assert persona.budget_tier in {"budget", "mid", "premium", "luxury"}
        assert persona.planning_horizon
        assert persona.experience in {"first_timer", "repeat"}
        assert persona.accessibility in {"none", "mobility", "sensory"}
        assert len(persona.interests) == 2
        assert persona.device_channel in {"mobile_web", "desktop", "app"}
        assert persona.label()


def test_safari_and_fjord_priors_are_different():
    assert SAFARI_WEIGHTS["source_market"]["Australia"] < FJORD_CRUISE_WEIGHTS["source_market"]["Australia"]
    assert SAFARI_WEIGHTS["budget_tier"]["luxury"] > FJORD_CRUISE_WEIGHTS["budget_tier"]["luxury"]
    safari = sample_personas(n=6000, profile="safari", seed=1)
    fjord = sample_personas(n=6000, profile="fjord_cruise", seed=1)
    assert _share(safari.personas, "budget_tier", "luxury") > _share(fjord.personas, "budget_tier", "luxury")
    assert _share(fjord.personas, "source_market", "Australia") > _share(
        safari.personas, "source_market", "Australia"
    )
    # Frequencies land near the stated prior.
    assert abs(_share(safari.personas, "budget_tier", "budget") - 0.15) < 0.02
    assert abs(_share(fjord.personas, "planning_horizon", "last_minute") - 0.18) < 0.02


def test_override_replaces_one_axis():
    panel = sample_personas(
        n=400,
        profile="safari",
        seed=5,
        override={"axes": {"budget_tier": {"budget": 1, "mid": 0, "premium": 0, "luxury": 0}}},
    )
    assert {persona.budget_tier for persona in panel.personas} == {"budget"}


def test_custom_profile_requires_weights():
    with pytest.raises(ValueError):
        sample_personas(n=2, profile="custom", seed=1)


def test_weights_are_normalized():
    panel = sample_personas(n=1, profile="safari", seed=0)
    for weights in panel.weights.values():
        assert abs(sum(weights.values()) - 1) < 1e-9


def test_sampler_does_not_depend_on_global_random_state():
    random.seed(123)
    first = sample_personas(n=5, profile="safari", seed=9)
    random.seed(999)
    second = sample_personas(n=5, profile="safari", seed=9)
    assert [persona.id for persona in first.personas] == [persona.id for persona in second.personas]
    assert [persona.source_market for persona in first.personas] == [
        persona.source_market for persona in second.personas
    ]
