from collection_qa.personas import default_weights, sample_personas, validate_weights


def test_builtin_weights_sum_to_one_and_differ_by_collection():
    mara, mara_basis = default_weights("masai-mara")
    milford, milford_basis = default_weights("milford-sound")
    generic, generic_basis = default_weights("somewhere-else")
    validate_weights(mara)
    validate_weights(milford)
    validate_weights(generic)
    assert mara["planning_horizon"]["months"] > milford["planning_horizon"]["months"]
    assert milford["planning_horizon"]["last_minute"] > mara["planning_horizon"]["last_minute"]
    assert mara["base"]["nairobi"] > 0.5
    assert milford["base"]["queenstown"] > milford["base"]["te_anau"]
    assert "assumption" in mara_basis
    assert "assumption" in milford_basis
    assert "generic" in generic_basis


def test_sampling_is_seeded_and_labels_the_assumption():
    first = sample_personas("masai-mara", 20, seed=7)
    second = sample_personas("masai-mara", 20, seed=7)
    assert [persona.as_dict() for persona in first.personas] == [persona.as_dict() for persona in second.personas]
    persona = first.personas[0]
    assert persona.trip_type in {"solo", "couple", "family_with_kids", "friends"}
    assert persona.experience in {"first_timer", "repeat"}
    assert "assumption" in persona.assumption_basis
    assert persona.interests


def test_override_changes_the_mix():
    panel = sample_personas(
        "milford-sound",
        40,
        seed=1,
        override={"budget_tier": {"budget": 1.0, "mid": 0, "premium": 0, "luxury": 0}},
    )
    assert all(persona.budget_tier == "budget" for persona in panel.personas)
    assert "overrides" in panel.assumption_basis


def test_large_sample_tracks_mara_couple_weight():
    panel = sample_personas("masai-mara", 4000, seed=11)
    couple_share = panel.counts("trip_type")["couple"] / 4000
    assert abs(couple_share - 0.42) < 0.03
