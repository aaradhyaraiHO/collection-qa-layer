"""Travel booking-intent anchor sets for semantic similarity rating.

Six sets of five statements, averaged the way the SSR paper averages its six
reference sets (arXiv 2510.08338). These sentences are a first draft for
booking a trip. They were not optimized on Headout survey data. The paper's
anchors were manually tuned on 57 personal-care surveys, so transfer is part
of the calibration plan, not something this file claims to have finished.

Each statement contains a short cue. The hash embedder used in tests and in
offline mock runs keys off those cues. The real sentence-transformers embedder
uses the full sentence.
"""

from __future__ import annotations

# Cue phrases, rating 1..5. Longer negative cues are listed so "would not book"
# is not mistaken for "would book".
INTENT_CUES: dict[int, tuple[str, ...]] = {
    1: ("i would not book", "no intention of booking", "skip this entirely"),
    2: ("probably would not book", "unlikely to book", "keep looking rather than book"),
    3: ("i am unsure", "on the fence", "not convinced"),
    4: ("probably book", "likely to book", "fits this trip"),
    5: ("i would book", "ready to book", "exactly the experience"),
}


ANCHOR_SETS: dict[str, tuple[str, str, str, str, str]] = {
    "booking_plain": (
        "I would not book this experience.",
        "I probably would not book this experience.",
        "I am unsure whether I would book this experience.",
        "I would probably book this experience.",
        "I would book this experience.",
    ),
    "booking_now": (
        "I have no intention of booking this trip.",
        "I might look later, but I am unlikely to book this now.",
        "I am on the fence about booking this trip.",
        "I am likely to book this trip.",
        "I am ready to book this trip now.",
    ),
    "fit_for_me": (
        "I would not book this. It does not fit my trip at all.",
        "I probably would not book this. It is a poor fit for how I travel.",
        "I am unsure. This could fit my trip, but I am not convinced.",
        "This fits this trip well, so I would probably book it.",
        "This is exactly the experience I want, and I would book it.",
    ),
    "value": (
        "I would not book this at this price.",
        "I probably would not book this because the price is too high for me.",
        "I am unsure whether this price is worth it.",
        "The price is fair enough that I would probably book this.",
        "I would book this at this price.",
    ),
    "choose_over_others": (
        "I would skip this entirely and not consider it.",
        "I would keep looking rather than book this.",
        "I am unsure and might choose this only if nothing else worked.",
        "I would probably book this over most alternatives on the page.",
        "This is the one I would book from this page.",
    ),
    "commitment": (
        "I would not book this. I will leave it.",
        "I am unlikely to book this and go ahead.",
        "I am unsure and undecided about booking.",
        "I expect I would probably book this.",
        "I am ready to book this.",
    ),
}


def anchor_set_ids() -> list[str]:
    return list(ANCHOR_SETS)


def iter_anchors() -> list[tuple[str, int, str]]:
    """Return (set_id, rating 1-5, statement) in set order."""
    rows: list[tuple[str, int, str]] = []
    for set_id, statements in ANCHOR_SETS.items():
        if len(statements) != 5:
            raise ValueError(f"anchor set {set_id} must have 5 statements")
        for offset, text in enumerate(statements):
            rows.append((set_id, offset + 1, text))
    return rows
