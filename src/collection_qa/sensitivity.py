"""Persona-mix sensitivity. Reweights scored reactions. No new LLM calls.

The panel was drawn from a design mix P. A scenario is another mix Q on the
same independent axes. Each persona is reweighted by Q(attrs) / P(attrs).
The base scenario uses Q = P, so every persona has weight 1 and the blended
mean matches the unweighted scorecard mean.

A segment mean is the average of the personas already in that cell. Changing
how often the mix samples that cell does not change the cell. When the blended
page number moves, read the segments.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from collection_qa.checks import (
    PAGE_MEAN_PASS,
    PAGE_MEAN_WARN,
    PRODUCT_MEAN_PASS,
    PRODUCT_MEAN_WARN,
    cannibalisation_from_intent,
    intent_issues,
    relative_ranking_issues,
)
from collection_qa.models import CollectionSpec

SHIFT_AXES = ("trip_type", "budget_tier", "source_market", "planning_horizon")
ROBUST_RATE = 0.90
PAGE_MOVE = 0.05
MIN_CELL_DEFAULT = 8
TARGET_CELL_DEFAULT = 15
DEFAULT_SHIFT = 0.20
DEFAULT_DIRICHLET = 40
DEFAULT_CONCENTRATION = 50.0

WEIGHT_DEPENDENT_CODES = {
    "product_intent",
    "page_intent",
    "relative_rank",
    "score_compression",
    "cannibalisation_intent",
}

SEGMENT_RECOMMENDATION = (
    "The blended page purchase intent is weight-sensitive. Read the per-segment "
    "results instead of the single blended number. A segment mean is the average "
    "of the personas already in that cell. It does not depend on how often the "
    "mix tried to sample that cell."
)

MISSING_PANEL_NOTE = """
This scorecard has no panel_scores, so the mix cannot be reweighted without new model calls.

The committed live files store aggregated pmfs, segment means, a handful of quotes, the design weights, and the seed. They do not store each persona's attributes together with that persona's purchase-intent mean.

Regenerate from the live sqlite cache. The cache key is the hash of model, mock flag, the client temperature field (0.5, even though Sonnet 5.5 is not sent a temperature), max_tokens, the system prompt, the user prompt, and the completion index. The live run used max_tokens 320 and the system prompt from before the English-only wording change. A re-run with today's prompt or with the 640 token cap will miss the cache and call Claude again.

Use the same seed (7), 30 personas, model claude-sonnet-5-5, and embedder sentence-transformers/all-MiniLM-L6-v2 if the new means should match these files. The regenerated scorecard will contain panel_scores. Then run:

collection-qa sensitivity <spec> --from-run <regenerated.json> --out reports/live/sensitivity
""".strip()

ORIGINAL_SYSTEM_PROMPT = (
    "You are taking part in a travel-booking research interview. "
    "Impersonate the traveler described in the question. "
    "Speak in the first person as that traveler, not as an analyst. "
    "Reply in 2 to 4 sentences about how likely you are to book what is shown. "
    "Name what appeals to you and what would stop you. "
    "Do not reply with a number, a star rating, or a Likert score. "
    "Do not mention that you are a language model."
)


def shift_axis(weights: dict[str, float], level: str, delta: float) -> dict[str, float] | None:
    """Move one level by `delta` probability points and rescale the others.

    The level is clipped to [0, 1]. Returns None when the clip leaves the mix unchanged.
    """
    if level not in weights:
        raise KeyError(level)
    current = float(weights[level])
    target = min(1.0, max(0.0, current + delta))
    if abs(target - current) < 1e-12:
        return None
    others = {key: float(value) for key, value in weights.items() if key != level}
    remaining = 1.0 - target
    other_sum = sum(others.values())
    if other_sum <= 0:
        scaled = {key: 0.0 for key in others}
    else:
        scaled = {key: value / other_sum * remaining for key, value in others.items()}
    scaled[level] = target
    return scaled


def normalize_axis(weights: dict[str, float]) -> dict[str, float]:
    total = float(sum(weights.values()))
    if total <= 0:
        raise ValueError("axis weights must sum to a positive number")
    return {key: float(value) / total for key, value in weights.items()}


def importance_ratio(
    attributes: dict[str, str],
    base: dict[str, dict[str, float]],
    scenario: dict[str, dict[str, float]],
) -> float:
    """Q(attrs) / P(attrs) under independent axes. Unchanged axes contribute 1."""
    ratio = 1.0
    for axis, base_axis in base.items():
        scenario_axis = scenario.get(axis, base_axis)
        level = attributes[axis]
        base_p = float(base_axis[level])
        if base_p <= 0:
            raise ValueError(f"base weight for {axis}={level} is 0; this persona cannot be reweighted")
        ratio *= float(scenario_axis[level]) / base_p
    return ratio


def weighted_mean(values: list[float], ratios: list[float]) -> float:
    if len(values) != len(ratios) or not values:
        raise ValueError("values and ratios must be the same non-empty length")
    weight_sum = float(sum(ratios))
    if weight_sum <= 0:
        raise ValueError("importance weights sum to 0")
    return float(sum(value * ratio for value, ratio in zip(values, ratios)) / weight_sum)


def kish_ess(ratios: list[float]) -> float:
    total = float(sum(ratios))
    squares = float(sum(ratio * ratio for ratio in ratios))
    if squares <= 0:
        return 0.0
    return (total * total) / squares


def kendall_tau(order_a: list[str], order_b: list[str]) -> float:
    """Tau-a on two rankings of the same items. 1 means the same order."""
    if order_a == order_b:
        return 1.0
    rank_b = {item: index for index, item in enumerate(order_b)}
    sequence = [rank_b[item] for item in order_a]
    count = len(sequence)
    concordant = discordant = 0
    for left in range(count):
        for right in range(left + 1, count):
            if sequence[left] < sequence[right]:
                concordant += 1
            elif sequence[left] > sequence[right]:
                discordant += 1
    pairs = count * (count - 1) / 2
    if pairs == 0:
        return 1.0
    return (concordant - discordant) / pairs


def spearman(order_a: list[str], order_b: list[str]) -> float:
    if order_a == order_b:
        return 1.0
    rank_b = {item: index for index, item in enumerate(order_b)}
    xs = list(range(len(order_a)))
    ys = [rank_b[item] for item in order_a]
    return _pearson(xs, ys)


def _pearson(xs: list[float], ys: list[float]) -> float:
    count = len(xs)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    spread_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    spread_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if spread_x == 0 or spread_y == 0:
        return 1.0
    return numerator / (spread_x * spread_y)


def rank_order(means: dict[str, float]) -> list[str]:
    return [item for item, _ in sorted(means.items(), key=lambda pair: (-pair[1], pair[0]))]


def top_bottom(order: list[str], k: int = 3) -> tuple[list[str], list[str]]:
    if not order:
        return [], []
    size = min(k, len(order))
    return order[:size], list(reversed(order[-size:]))


def additional_personas(panel_size: int, level_weight: float, target: int) -> int:
    """How many more draws make the expected count in this cell reach `target`."""
    if level_weight <= 0:
        return target
    needed = math.ceil(target / level_weight)
    return max(0, needed - panel_size)


def one_at_a_time(
    base: dict[str, dict[str, float]],
    shift: float,
    axes: tuple[str, ...] = SHIFT_AXES,
) -> list[dict]:
    scenarios = []
    for axis in axes:
        if axis not in base:
            continue
        for level in base[axis]:
            for delta, label in ((shift, f"+{shift:.0%}"), (-shift, f"-{shift:.0%}")):
                moved = shift_axis(base[axis], level, delta)
                if moved is None:
                    continue
                mix = {name: dict(weights) for name, weights in base.items()}
                mix[axis] = moved
                scenarios.append(
                    {
                        "id": f"oat:{axis}:{level}:{label}",
                        "kind": "one_at_a_time",
                        "axis": axis,
                        "level": level,
                        "delta": delta,
                        "weights": mix,
                    }
                )
    return scenarios


def dirichlet_scenarios(
    base: dict[str, dict[str, float]],
    count: int,
    concentration: float,
    seed: int,
    axes: tuple[str, ...] = SHIFT_AXES,
) -> list[dict]:
    """Independent Dirichlet draws per axis, with mean equal to the base mix."""
    if count <= 0:
        return []
    if concentration <= 0:
        raise ValueError("concentration must be positive")
    rng = np.random.default_rng(seed)
    scenarios = []
    for index in range(count):
        mix = {name: dict(weights) for name, weights in base.items()}
        for axis in axes:
            if axis not in base:
                continue
            labels = list(base[axis])
            alpha = np.array([concentration * base[axis][label] for label in labels], dtype=float)
            draw = rng.dirichlet(alpha)
            mix[axis] = {label: float(value) for label, value in zip(labels, draw)}
        scenarios.append(
            {
                "id": f"dirichlet:{index:03d}",
                "kind": "dirichlet",
                "axis": None,
                "level": None,
                "delta": None,
                "weights": mix,
            }
        )
    return scenarios


def _issue_identity(issue: dict) -> tuple:
    evidence = issue.get("evidence") or {}
    if "product_ids" in evidence:
        token = tuple(sorted(evidence["product_ids"]))
    else:
        token = evidence.get("key", evidence.get("product_id", evidence.get("surface")))
    return (issue["code"], token)


def _severity_map(issues: list[dict]) -> dict[tuple, str]:
    found = {}
    for issue in issues:
        if issue["code"] not in WEIGHT_DEPENDENT_CODES:
            continue
        found[_issue_identity(issue)] = issue["severity"]
    return found


def _weighted_gate_issues(
    product_means: dict[str, float],
    page_means: dict[str, float],
    titles: dict[str, str],
) -> list[dict]:
    issues = []
    if product_means:
        issues.extend(
            issue.model_dump()
            for issue in intent_issues(
                scope="product",
                gate="A",
                means=product_means,
                pass_at=PRODUCT_MEAN_PASS,
                warn_at=PRODUCT_MEAN_WARN,
                code="product_intent",
            )
        )
        issues.extend(
            issue.model_dump() for issue in relative_ranking_issues(product_means, titles)
        )
        # cannibalisation_from_intent needs a spec. Build a tiny stand-in via the
        # public function only when we have a spec. The caller passes issues
        # computed with the spec when one is available.
    if page_means:
        issues.extend(
            issue.model_dump()
            for issue in intent_issues(
                scope="page",
                gate="B",
                means=page_means,
                pass_at=PAGE_MEAN_PASS,
                warn_at=PAGE_MEAN_WARN,
                code="page_intent",
            )
        )
    return issues


def _cell_flags(
    panel: list[dict],
    base: dict[str, dict[str, float]],
    *,
    min_cell: int,
    target_cell: int,
) -> list[dict]:
    flags = []
    panel_size = len(panel)
    for axis in SHIFT_AXES:
        if axis not in base:
            continue
        counts: dict[str, int] = {level: 0 for level in base[axis]}
        for row in panel:
            level = row["attributes"].get(axis)
            if level in counts:
                counts[level] += 1
        for level, count in counts.items():
            if count >= min_cell:
                continue
            weight = float(base[axis][level])
            more = additional_personas(panel_size, weight, target_cell)
            flags.append(
                {
                    "axis": axis,
                    "level": level,
                    "n": count,
                    "base_weight": round(weight, 4),
                    "min_cell": min_cell,
                    "target_cell": target_cell,
                    "additional_personas": more,
                    "message": (
                        f"{axis}={level} has {count} personas in a panel of {panel_size} "
                        f"(design weight {weight:.0%}). That is too few to reweight reliably. "
                        f"Sample about {more} more personas (panel size {panel_size + more}) "
                        f"so this cell's expected count reaches {target_cell}."
                    ),
                }
            )
    return flags


def _blend(
    panel: list[dict],
    stimulus_id: str,
    ratios_by_id: dict[str, float],
) -> float | None:
    values = []
    ratios = []
    for row in panel:
        score = row["scores"].get(stimulus_id)
        if score is None:
            continue
        values.append(float(score["mean"]))
        ratios.append(ratios_by_id[row["persona_id"]])
    if not values or float(sum(ratios)) <= 0:
        return None
    return weighted_mean(values, ratios)


def analyze_panel(
    panel: list[dict],
    base_weights: dict[str, dict[str, float]],
    *,
    product_ids: list[str],
    page_ids: list[str],
    titles: dict[str, str],
    base_issues: list[dict],
    spec: CollectionSpec | None = None,
    shift: float = DEFAULT_SHIFT,
    n_dirichlet: int = DEFAULT_DIRICHLET,
    concentration: float = DEFAULT_CONCENTRATION,
    seed: int = 7,
    min_cell: int = MIN_CELL_DEFAULT,
    target_cell: int = TARGET_CELL_DEFAULT,
) -> dict:
    base = {axis: normalize_axis(weights) for axis, weights in base_weights.items()}
    scenarios = [{"id": "base", "kind": "base", "axis": None, "level": None, "delta": None, "weights": base}]
    scenarios.extend(one_at_a_time(base, shift))
    scenarios.extend(dirichlet_scenarios(base, n_dirichlet, concentration, seed))

    def ratios_for(mix: dict[str, dict[str, float]]) -> dict[str, float]:
        return {
            row["persona_id"]: importance_ratio(row["attributes"], base, mix) for row in panel
        }

    def product_means_for(ratio_map: dict[str, float]) -> dict[str, float]:
        found = {}
        for product_id in product_ids:
            value = _blend(panel, product_id, ratio_map)
            if value is not None:
                found[product_id] = value
        return found

    def page_means_for(ratio_map: dict[str, float]) -> dict[str, float]:
        found = {}
        for page_id in page_ids:
            value = _blend(panel, page_id, ratio_map)
            if value is not None:
                found[page_id] = value
        return found

    def segment_orders(axis: str) -> dict[str, list[str]]:
        """Unweighted product order inside each cell. Invariant to the mix."""
        levels = sorted({row["attributes"][axis] for row in panel if axis in row["attributes"]})
        orders = {}
        for level in levels:
            members = [row for row in panel if row["attributes"].get(axis) == level]
            means = {}
            for product_id in product_ids:
                scores = [
                    float(row["scores"][product_id]["mean"])
                    for row in members
                    if product_id in row["scores"]
                ]
                if scores:
                    means[product_id] = sum(scores) / len(scores)
            if means:
                orders[level] = rank_order(means)
        return orders

    segment_rank = {axis: segment_orders(axis) for axis in ("trip_type", "budget_tier")}

    evaluated = []
    for scenario in scenarios:
        ratio_map = ratios_for(scenario["weights"])
        ratio_list = [ratio_map[row["persona_id"]] for row in panel]
        ess = kish_ess(ratio_list)
        products = product_means_for(ratio_map)
        pages = page_means_for(ratio_map)
        order = rank_order(products)
        issues = _weighted_gate_issues(products, pages, titles)
        if spec is not None and products:
            issues.extend(
                issue.model_dump() for issue in cannibalisation_from_intent(spec, products)
            )
        top, bottom = top_bottom(order)
        evaluated.append(
            {
                "id": scenario["id"],
                "kind": scenario["kind"],
                "axis": scenario["axis"],
                "level": scenario["level"],
                "delta": scenario["delta"],
                "ess": round(ess, 2),
                "reliable": True,
                "page_means": {key: round(value, 4) for key, value in pages.items()},
                "product_order": order,
                "top3": top,
                "bottom3": bottom,
                "issues": _severity_map(issues),
            }
        )

    base_eval = evaluated[0]
    base_ess = base_eval["ess"]
    # A mix that piles onto a handful of personas is not evidence. A small panel
    # is still evidence about itself, so the floor cannot sit above the base ESS.
    ess_floor = min(float(min_cell), base_ess * 0.5) if base_ess >= 5 else base_ess * 0.5
    for row in evaluated[1:]:
        row["reliable"] = row["ess"] >= ess_floor
    reliable = [row for row in evaluated[1:] if row["reliable"]]
    dropped = [row["id"] for row in evaluated[1:] if not row["reliable"]]

    def stability_row(row: dict) -> dict:
        return {
            "id": row["id"],
            "kind": row["kind"],
            "axis": row["axis"],
            "kendall_tau": round(kendall_tau(base_eval["product_order"], row["product_order"]), 4),
            "spearman": round(spearman(base_eval["product_order"], row["product_order"]), 4),
            "top3_overlap": len(set(base_eval["top3"]) & set(row["top3"])),
            "bottom3_overlap": len(set(base_eval["bottom3"]) & set(row["bottom3"])),
            "top3_same": set(row["top3"]) == set(base_eval["top3"]),
            "bottom3_same": set(row["bottom3"]) == set(base_eval["bottom3"]),
            "page_means": row["page_means"],
        }

    stability = [stability_row(row) for row in reliable]
    taus = [row["kendall_tau"] for row in stability]
    spears = [row["spearman"] for row in stability]
    base_issue_map = _severity_map(base_issues)
    # Prefer the recomputed base so identities match the scenario issues.
    if base_eval["issues"]:
        base_issue_map = base_eval["issues"]

    findings = []
    flip_slots = 0
    flipped_slots = 0
    for identity, severity in sorted(base_issue_map.items(), key=lambda item: (item[0][0], str(item[0][1]))):
        if severity == "pass":
            continue
        holds = 0
        for row in reliable:
            flip_slots += 1
            scenario_severity = row["issues"].get(identity, "pass")
            if scenario_severity == severity:
                holds += 1
            else:
                flipped_slots += 1
        rate = holds / len(reliable) if reliable else 1.0
        findings.append(
            {
                "kind": "gate",
                "code": identity[0],
                "key": identity[1] if not isinstance(identity[1], tuple) else list(identity[1]),
                "base_severity": severity,
                "hold_rate": round(rate, 4),
                "verdict": "ROBUST" if rate >= ROBUST_RATE else "WEIGHT-SENSITIVE",
            }
        )

    for label, flag in (("top3", "top3_same"), ("bottom3", "bottom3_same")):
        holds = sum(1 for row in stability if row[flag])
        rate = holds / len(stability) if stability else 1.0
        findings.append(
            {
                "kind": "ranking",
                "code": label,
                "key": base_eval[label],
                "base_severity": "set",
                "hold_rate": round(rate, 4),
                "verdict": "ROBUST" if rate >= ROBUST_RATE else "WEIGHT-SENSITIVE",
            }
        )

    for axis, orders in segment_rank.items():
        findings.append(
            {
                "kind": "segment_rank",
                "code": axis,
                "key": "unweighted cells",
                "orders": {level: order for level, order in orders.items()},
                "base_severity": "invariant",
                "hold_rate": 1.0,
                "verdict": "ROBUST",
                "note": (
                    "Unweighted product order inside this segment. It does not use the mix weights."
                ),
            }
        )

    page_sensitive = False
    page_detail = {}
    for page_id, base_mean in base_eval["page_means"].items():
        moved = 0
        values = []
        for row in reliable:
            value = row["page_means"].get(page_id)
            if value is None:
                continue
            values.append(value)
            if abs(value - base_mean) > PAGE_MOVE:
                moved += 1
        move_rate = moved / len(reliable) if reliable else 0.0
        sensitive = move_rate > (1 - ROBUST_RATE)
        page_detail[page_id] = {
            "base_mean": round(base_mean, 4),
            "scenario_min": round(min(values), 4) if values else None,
            "scenario_max": round(max(values), 4) if values else None,
            "share_moving_more_than": round(move_rate, 4),
            "move_threshold": PAGE_MOVE,
            "verdict": "WEIGHT-SENSITIVE" if sensitive else "ROBUST",
        }
        page_sensitive = page_sensitive or sensitive
    for finding in findings:
        if finding["kind"] == "gate" and finding["code"] == "page_intent" and finding["verdict"] == "WEIGHT-SENSITIVE":
            page_sensitive = True

    by_axis: dict[str, dict[str, list[float]]] = {}
    for row in stability:
        if row["kind"] != "one_at_a_time" or not row["axis"]:
            continue
        bucket = by_axis.setdefault(row["axis"], {"page_delta": [], "tau_drop": []})
        bucket["tau_drop"].append(1 - row["kendall_tau"])
        for page_id, base_mean in base_eval["page_means"].items():
            value = row["page_means"].get(page_id)
            if value is not None:
                bucket["page_delta"].append(abs(value - base_mean))
    dimension_influence = []
    for axis, bucket in by_axis.items():
        dimension_influence.append(
            {
                "axis": axis,
                "mean_abs_page_delta": round(sum(bucket["page_delta"]) / len(bucket["page_delta"]), 4)
                if bucket["page_delta"]
                else 0.0,
                "mean_tau_drop": round(sum(bucket["tau_drop"]) / len(bucket["tau_drop"]), 4)
                if bucket["tau_drop"]
                else 0.0,
            }
        )
    dimension_influence.sort(key=lambda row: (-row["mean_abs_page_delta"], row["axis"]))

    dirichlet_rows = [row for row in stability if row["kind"] == "dirichlet"]
    return {
        "status": "ok",
        "n_personas": len(panel),
        "n_scenarios": len(reliable),
        "n_dirichlet": n_dirichlet,
        "shift": shift,
        "concentration": concentration,
        "seed": seed,
        "unreliable_scenarios": dropped,
        "small_cells": _cell_flags(panel, base, min_cell=min_cell, target_cell=target_cell),
        "base_page_means": base_eval["page_means"],
        "base_product_order": base_eval["product_order"],
        "base_top3": base_eval["top3"],
        "base_bottom3": base_eval["bottom3"],
        "rank_stability": {
            "kendall_tau_mean": round(sum(taus) / len(taus), 4) if taus else None,
            "kendall_tau_min": round(min(taus), 4) if taus else None,
            "spearman_mean": round(sum(spears) / len(spears), 4) if spears else None,
            "spearman_min": round(min(spears), 4) if spears else None,
            "top3_same_rate": round(sum(1 for row in stability if row["top3_same"]) / len(stability), 4)
            if stability
            else None,
            "bottom3_same_rate": round(
                sum(1 for row in stability if row["bottom3_same"]) / len(stability), 4
            )
            if stability
            else None,
            "mean_top3_overlap": round(sum(row["top3_overlap"] for row in stability) / len(stability), 4)
            if stability
            else None,
            "mean_bottom3_overlap": round(
                sum(row["bottom3_overlap"] for row in stability) / len(stability), 4
            )
            if stability
            else None,
        },
        "gate_flip_rate": round(flipped_slots / flip_slots, 4) if flip_slots else 0.0,
        "dimension_influence": dimension_influence,
        "dirichlet_kendall_mean": round(
            sum(row["kendall_tau"] for row in dirichlet_rows) / len(dirichlet_rows), 4
        )
        if dirichlet_rows
        else None,
        "findings": findings,
        "page_level": page_detail,
        "page_weight_sensitive": page_sensitive,
        "recommendation": SEGMENT_RECOMMENDATION if page_sensitive else None,
        "segment_ranks_invariant": True,
    }


def missing_panel_report(scorecard: dict) -> dict:
    return {
        "status": "missing_panel_scores",
        "collection_id": scorecard.get("collection_id"),
        "seed": scorecard.get("seed", scorecard.get("method", {}).get("seed")),
        "n_personas": scorecard.get("method", {}).get("n_personas"),
        "embedder": scorecard.get("method", {}).get("embedder"),
        "model": scorecard.get("method", {}).get("model"),
        "message": MISSING_PANEL_NOTE,
        "original_system_prompt": ORIGINAL_SYSTEM_PROMPT,
        "required_cache_max_tokens": 320,
        "required_client_temperature_field": 0.5,
        "required_embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    }


def analyze_scorecard(
    scorecard: dict,
    spec: CollectionSpec | None = None,
    **kwargs,
) -> dict:
    panel = scorecard.get("panel_scores")
    if not panel:
        return missing_panel_report(scorecard)
    weights = scorecard.get("persona_weights")
    if not weights:
        raise ValueError("scorecard has panel_scores but no persona_weights")
    products = scorecard.get("products") or {}
    product_ids = list(scorecard.get("rankings", {}).get("overall") or products.keys())
    page_ids = sorted(
        {
            key
            for row in panel
            for key in row.get("scores", {})
            if str(key).startswith("page:")
        }
    )
    titles = {product_id: block.get("title", product_id) for product_id, block in products.items()}
    seed = kwargs.pop("seed", None)
    if seed is None:
        seed = scorecard.get("seed", scorecard.get("method", {}).get("seed", 7))
    result = analyze_panel(
        panel,
        weights,
        product_ids=product_ids,
        page_ids=page_ids,
        titles=titles,
        base_issues=scorecard.get("issues") or [],
        spec=spec,
        seed=seed,
        **kwargs,
    )
    result["collection_id"] = scorecard.get("collection_id")
    result["mock"] = scorecard.get("mock")
    return result


def _pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.0%}"


def _num(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value:.3f}"


def render_sensitivity_section(result: dict) -> str:
    lines = ["## Sensitivity", ""]
    if result.get("status") != "ok":
        lines.append(result.get("message", "Persona scores are missing, so the mix was not reweighted."))
        lines.append("")
        return "\n".join(lines)
    lines.append(
        f"Reweighted {result['n_personas']} already-scored personas across {result['n_scenarios']} "
        f"reliable mixes (one-at-a-time ±{result['shift']:.0%} on trip type, budget, source market, "
        f"and planning horizon, plus {result['n_dirichlet']} Dirichlet draws, concentration "
        f"{result['concentration']}, seed {result['seed']}). No new model calls."
    )
    lines.append("")
    lines.append(
        "Within a segment, purchase intent is the average of the personas in that cell. "
        "The cell does not care what share of the mix it was assigned. Those ranks are invariant. "
        "The blended page number and the overall product ranking do use the mix."
    )
    lines.append("")
    stability = result["rank_stability"]
    lines.append(
        f"Product-rank stability versus the base mix: mean Kendall tau {_num(stability['kendall_tau_mean'])}, "
        f"minimum {_num(stability['kendall_tau_min'])}; mean Spearman {_num(stability['spearman_mean'])}, "
        f"minimum {_num(stability['spearman_min'])}. Top-3 set unchanged in "
        f"{_pct(stability['top3_same_rate'])} of scenarios (mean overlap {stability['mean_top3_overlap']} of 3). "
        f"Bottom-3 unchanged in {_pct(stability['bottom3_same_rate'])}. "
        f"Weight-dependent gate severity flipped in {_pct(result['gate_flip_rate'])} of finding-scenario pairs."
    )
    lines.append("")
    if result["dimension_influence"]:
        lines.append("Dimensions, by how far a ±20 percentage-point shift moves the blended page score:")
        lines.append("")
        for row in result["dimension_influence"]:
            lines.append(
                f"- **{row['axis']}** — mean absolute page move {row['mean_abs_page_delta']:.3f}, "
                f"mean Kendall drop {row['mean_tau_drop']:.3f}"
            )
        lines.append("")
    if result.get("dirichlet_kendall_mean") is not None:
        lines.append(
            f"Dirichlet mixes around the base: mean Kendall tau {result['dirichlet_kendall_mean']}."
        )
        lines.append("")
    lines.append("| Finding | Base | Holds | Verdict |")
    lines.append("| --- | --- | ---: | --- |")
    for finding in result["findings"]:
        if finding["kind"] == "segment_rank":
            label = f"segment ranks ({finding['code']})"
            base = "invariant"
        elif finding["kind"] == "ranking":
            label = finding["code"]
            base = ", ".join(finding["key"])
        else:
            label = f"{finding['code']} {finding['key']}"
            base = finding["base_severity"]
        lines.append(
            f"| {label} | {base} | {finding['hold_rate']:.0%} | {finding['verdict']} |"
        )
    lines.append("")
    for page_id, detail in result["page_level"].items():
        lines.append(
            f"Page `{page_id}`: base mean {detail['base_mean']}, scenario range "
            f"{detail['scenario_min']}–{detail['scenario_max']}, "
            f"verdict **{detail['verdict']}**."
        )
    lines.append("")
    if result.get("recommendation"):
        lines.append(f"**{result['recommendation']}**")
        lines.append("")
    if result["small_cells"]:
        lines.append("Cells too small to reweight:")
        lines.append("")
        for flag in result["small_cells"]:
            lines.append(f"- {flag['message']}")
        lines.append("")
    if result["unreliable_scenarios"]:
        lines.append(
            f"{len(result['unreliable_scenarios'])} scenarios were dropped because the effective "
            "sample size fell below the cell minimum. They are not in the rates above."
        )
        lines.append("")
    return "\n".join(lines)


def write_sensitivity(result: dict, directory: str | Path, collection_id: str) -> tuple[Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{collection_id}.sensitivity.json"
    md_path = directory / f"{collection_id}.sensitivity.md"
    json_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    title = result.get("collection_id") or collection_id
    markdown = render_sensitivity_section(result).replace(
        "## Sensitivity", f"# Persona-mix sensitivity: {title}", 1
    )
    md_path.write_text(markdown + "\n", encoding="utf-8")
    return json_path, md_path
