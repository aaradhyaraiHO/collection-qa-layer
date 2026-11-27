"""Shape a scorecard into the seven-part page the local tool renders.

Charts are numbers. The page draws them as inline SVG. Nothing here calls a model.
When a live file has no per-persona scores, stability is the published segment
table reweighted. That is the mix moving the cells we already measured.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from collection_qa.personas import sample_personas
from collection_qa.report import CHANGE_BY_CODE, OWNER_BY_CODE, build_fixes, verdict_for
from collection_qa.sensitivity import kendall_tau, normalize_axis, rank_order, shift_axis

SMALL_CELL = 8
PAGE_BAND = 0.05


def build_view(source: dict, *, report: dict | None = None) -> dict:
    if isinstance(source.get("products"), dict):
        return _from_scorecard(source, report)
    return _from_check(source)


def load_pilot(collection_id: str, root: Path | None = None) -> dict:
    root = root or Path("reports/live")
    path = root / f"{collection_id}.json"
    scorecard = json.loads(path.read_text(encoding="utf-8"))
    panel_path = root / f"{collection_id}.panel.json"
    if panel_path.exists() and not scorecard.get("panel_scores"):
        extra = json.loads(panel_path.read_text(encoding="utf-8"))
        scorecard["panel_scores"] = extra.get("panel_scores") or []
        scorecard["panel_scores_provenance"] = extra.get("provenance")
    return build_view(scorecard)


def write_panel_file(scorecard_path: Path) -> Path:
    scorecard = json.loads(Path(scorecard_path).read_text(encoding="utf-8"))
    rows = panel_from_segment_means(scorecard)
    target = Path(scorecard_path).with_suffix(".panel.json")
    payload = {
        "collection_id": scorecard.get("collection_id"),
        "provenance": (
            "Each row is a seed-matched persona. The score is the published mean "
            "of that persona's trip type on that product or page. The committed "
            "live scorecard did not store the original per-persona SSR rows, and "
            "the sqlite cache is not in the repo, so these are not a second Claude run. "
            "The report heatmap uses the published segment table. This file is what "
            "a reader of panel_scores can reweight."
        ),
        "seed": scorecard.get("method", {}).get("seed"),
        "n_personas": scorecard.get("method", {}).get("n_personas"),
        "panel_scores": rows,
    }
    target.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return target


def panel_from_segment_means(scorecard: dict) -> list[dict]:
    method = scorecard.get("method") or {}
    panel = sample_personas(
        n=int(method.get("n_personas") or 30),
        profile=scorecard.get("persona_profile") or "fjord_cruise",
        seed=int(method.get("seed") or 7),
    )
    stimuli: dict[str, dict] = {}
    for product_id, block in (scorecard.get("products") or {}).items():
        stimuli[product_id] = block
    for role, block in (scorecard.get("pages") or {}).items():
        stimuli[f"page:{role}"] = block
    rows = []
    for persona in panel.personas:
        scores = {}
        for stimulus_id, block in stimuli.items():
            cell = ((block.get("by_segment") or {}).get("trip_type") or {}).get(persona.trip_type) or {}
            mean = cell.get("mean", (block.get("overall") or {}).get("mean"))
            if mean is None:
                continue
            scores[stimulus_id] = {"mean": round(float(mean), 6)}
        rows.append(
            {
                "persona_id": persona.id,
                "attributes": {
                    "source_market": persona.source_market,
                    "age_band": persona.age_band,
                    "trip_type": persona.trip_type,
                    "budget_tier": persona.budget_tier,
                    "planning_horizon": persona.planning_horizon,
                    "experience": persona.experience,
                    "accessibility": persona.accessibility,
                    "device_channel": persona.device_channel,
                },
                "scores": scores,
            }
        )
    return rows


def _from_scorecard(scorecard: dict, report: dict | None) -> dict:
    products = _product_table(scorecard)
    page = _primary_page(scorecard)
    issues = list(scorecard.get("issues") or [])
    quotes = list(scorecard.get("quotes") or [])
    status = (report or {}).get("status") or ("LIVE" if scorecard.get("provenance") == "live_headout" else "IN_PIPELINE")
    if report and report.get("verdict"):
        verdict, reason = report["verdict"], report["verdict_reason"]
    else:
        verdict, reason = verdict_for(status=status, issues=issues, has_products=bool(products))
    page_url = (page or {}).get("url") or ((report or {}).get("ce") or {}).get("collection_url")
    fixes = (report or {}).get("fixes") or build_fixes(issues, quotes, page_url)
    fails = sum(1 for issue in issues if issue.get("severity") == "fail")
    warns = sum(1 for issue in issues if issue.get("severity") == "warn")
    passes = sum(1 for issue in issues if issue.get("severity") == "pass")
    stability = _stability(scorecard)
    name = scorecard.get("collection_name") or ((report or {}).get("ce") or {}).get("name") or "Collection"
    likely = sorted(products, key=lambda row: (-(row["likely"]), row["title"]))
    ranked = sorted(products, key=lambda row: (-row["mean"], row["title"]))
    return {
        "title": name,
        "ce_id": scorecard.get("ce_id") or ((report or {}).get("ce") or {}).get("ce_id"),
        "collection_id": scorecard.get("collection_id"),
        "verdict": verdict,
        "verdict_reason": reason,
        "status": status,
        "mock": bool(scorecard.get("mock") or (report or {}).get("mock")),
        "kpis": [
            {"label": "Verdict", "value": verdict},
            {"label": "Page intent", "value": _fmt(page.get("mean") if page else None)},
            {"label": "Best product", "value": _fmt(ranked[0]["mean"]) if ranked else "—", "note": ranked[0]["title"] if ranked else ""},
            {"label": "Failed checks", "value": str(fails)},
            {"label": "Warnings", "value": str(warns)},
        ],
        "likely_to_book": likely,
        "quotes": [_quote_row(quote) for quote in quotes[:6]],
        "ranking": [{"title": row["title"], "mean": row["mean"], "id": row["id"]} for row in ranked],
        "fixes": [_fix_row(row) for row in fixes],
        "heatmap": _heatmap(scorecard),
        "dots": _dots(scorecard),
        "detail": {
            "products": ranked,
            "microbrand": _microbrand(scorecard, report),
            "prices": _prices(scorecard),
            "checks": {"pass": passes, "warn": warns, "fail": fails, "rows": [
                {"severity": issue.get("severity"), "code": issue.get("code"), "message": issue.get("message")}
                for issue in issues
            ]},
        },
        "trust": stability,
        "appendix": _appendix(scorecard, report),
    }


def _from_check(report: dict) -> dict:
    products = []
    for row in report.get("products") or []:
        mean = float(row.get("mean") or 0)
        products.append(
            {
                "id": row.get("id"),
                "title": row.get("title") or "",
                "mean": round(mean, 2),
                "pmf": [],
                "likely": None,
                "n": None,
                "z": None,
            }
        )
    issues = report.get("checks") or []
    fails = sum(1 for issue in issues if issue.get("severity") == "fail")
    warns = sum(1 for issue in issues if issue.get("severity") == "warn")
    passes = sum(1 for issue in issues if issue.get("severity") == "pass")
    ranked = sorted(products, key=lambda row: (-row["mean"], row["title"]))
    return {
        "title": (report.get("ce") or {}).get("name") or "Collection",
        "ce_id": (report.get("ce") or {}).get("ce_id"),
        "collection_id": None,
        "verdict": report.get("verdict") or "Hold",
        "verdict_reason": report.get("verdict_reason") or "",
        "status": report.get("status") or "",
        "mock": bool(report.get("mock")),
        "kpis": [
            {"label": "Verdict", "value": report.get("verdict") or "Hold"},
            {"label": "Best product", "value": _fmt(ranked[0]["mean"]) if ranked else "—", "note": ranked[0]["title"] if ranked else ""},
            {"label": "Failed checks", "value": str(fails)},
            {"label": "Warnings", "value": str(warns)},
        ],
        "likely_to_book": products,
        "quotes": [_quote_row(quote) for quote in (report.get("quotes") or [])[:6]],
        "ranking": [{"title": row["title"], "mean": row["mean"], "id": row["id"]} for row in ranked],
        "fixes": [_fix_row(row) for row in (report.get("fixes") or [])],
        "heatmap": {"columns": [], "rows": []},
        "dots": [],
        "detail": {
            "products": ranked,
            "microbrand": {"note": report.get("microbrand_vs_headout") or "No microbrand was resolved.", "bars": []},
            "prices": [],
            "checks": {"pass": passes, "warn": warns, "fail": fails, "rows": issues},
        },
        "trust": {
            "label": "Not reweighted",
            "note": " ".join(report.get("trust") or []),
            "page_base": None,
            "page_low": None,
            "page_high": None,
            "kendall_mean": None,
            "points": [],
            "bullets": list(report.get("trust") or []),
        },
        "appendix": {
            "inputs": report.get("inputs") or [],
            "pages": (report.get("appendix") or {}).get("pages") or [],
            "method": (report.get("appendix") or {}).get("method") or "",
        },
    }


def _product_table(scorecard: dict) -> list[dict]:
    products = scorecard.get("products") or {}
    order = (scorecard.get("rankings") or {}).get("overall") or list(products)
    means = [float(products[pid]["overall"]["mean"]) for pid in order if pid in products]
    center = sum(means) / len(means) if means else 0.0
    spread = (sum((value - center) ** 2 for value in means) / len(means)) ** 0.5 if means else 0.0
    rows = []
    for product_id in order:
        block = products.get(product_id)
        if not block:
            continue
        overall = block["overall"]
        pmf = [float(overall["pmf"].get(str(bucket), 0.0)) for bucket in range(1, 6)]
        mean = float(overall["mean"])
        z = block.get("z_vs_collection")
        if z is None and spread > 1e-9:
            z = (mean - center) / spread
        rows.append(
            {
                "id": product_id,
                "title": block.get("title") or product_id,
                "mean": round(mean, 2),
                "pmf": [round(value, 4) for value in pmf],
                "likely": round(pmf[3] + pmf[4], 4),
                "n": overall.get("n"),
                "z": None if z is None else round(float(z), 2),
                "price": block.get("price"),
                "currency": block.get("currency"),
            }
        )
    return rows


def _primary_page(scorecard: dict) -> dict | None:
    pages = scorecard.get("pages") or {}
    block = pages.get("primary") or (next(iter(pages.values())) if pages else None)
    if not block:
        return None
    return {
        "title": block.get("title"),
        "url": block.get("url"),
        "mean": round(float(block["overall"]["mean"]), 2),
        "pmf": [round(float(block["overall"]["pmf"].get(str(bucket), 0)), 4) for bucket in range(1, 6)],
        "n": block["overall"].get("n"),
    }


def _quote_row(quote: dict) -> dict:
    return {
        "text": quote.get("text") or "",
        "who": quote.get("persona_label") or quote.get("persona_id") or "",
        "on": quote.get("stimulus_title") or "",
        "mean": None if quote.get("mean_pi") is None else round(float(quote["mean_pi"]), 2),
    }


def _fix_row(row: dict) -> dict:
    code = row.get("code") or ""
    return {
        "priority": row.get("priority") or "",
        "issue": row.get("issue") or row.get("message") or "",
        "page_link": row.get("page_link") or "",
        "what_to_change": row.get("what_to_change") or CHANGE_BY_CODE.get(code, ""),
        "owner": row.get("owner") or OWNER_BY_CODE.get(code, "Growth"),
        "quote": row.get("quote") or "",
    }


def _heatmap(scorecard: dict) -> dict:
    products = scorecard.get("products") or {}
    order = (scorecard.get("rankings") or {}).get("overall") or list(products)
    columns = [{"id": pid, "title": products[pid].get("title") or pid} for pid in order if pid in products]
    rows = []
    levels = []
    for pid in order:
        block = products.get(pid) or {}
        for level in ((block.get("by_segment") or {}).get("trip_type") or {}):
            if level not in levels:
                levels.append(level)
    for level in levels:
        cells = []
        for pid in order:
            if pid not in products:
                continue
            cell = ((products[pid].get("by_segment") or {}).get("trip_type") or {}).get(level) or {}
            n = int(cell.get("n") or 0)
            mean = cell.get("mean")
            cells.append(
                {
                    "mean": None if mean is None else round(float(mean), 2),
                    "n": n,
                    "faded": n < SMALL_CELL,
                }
            )
        rows.append({"label": level.replace("_", " "), "cells": cells})
    return {"columns": [{"title": column["title"]} for column in columns], "rows": rows}


def _dots(scorecard: dict) -> list[dict]:
    pages = scorecard.get("pages") or {}
    block = pages.get("primary") or (next(iter(pages.values())) if pages else None)
    if not block:
        return []
    dots = []
    for axis in ("trip_type", "budget_tier"):
        for level, cell in ((block.get("by_segment") or {}).get(axis) or {}).items():
            n = int(cell.get("n") or 0)
            dots.append(
                {
                    "axis": axis.replace("_", " "),
                    "label": str(level).replace("_", " "),
                    "mean": round(float(cell["mean"]), 2),
                    "n": n,
                    "faded": n < SMALL_CELL,
                }
            )
    return dots


def _microbrand(scorecard: dict, report: dict | None) -> dict:
    pages = scorecard.get("pages") or {}
    bars = []
    if "primary" in pages:
        bars.append({"label": "Headout", "mean": round(float(pages["primary"]["overall"]["mean"]), 2)})
    if "microbrand" in pages:
        bars.append({"label": "Microbrand", "mean": round(float(pages["microbrand"]["overall"]["mean"]), 2)})
    note = (report or {}).get("microbrand_vs_headout")
    if not note:
        if not bars or len(bars) == 1 and bars[0]["label"] == "Headout":
            note = "No separate microbrand was scored. The collection page is the Headout surface."
        else:
            note = "Both surfaces were scored with the same panel. The gap is the difference in blended purchase intent."
    return {"note": note, "bars": bars}


def _prices(scorecard: dict) -> list[dict]:
    rows = []
    currency = None
    for product_id in (scorecard.get("rankings") or {}).get("overall") or []:
        block = (scorecard.get("products") or {}).get(product_id) or {}
        price = block.get("price")
        if price is None:
            continue
        currency = currency or block.get("currency")
        rows.append(
            {
                "name": block.get("title") or product_id,
                "price": float(price),
                "currency": block.get("currency") or currency,
                "kind": "Headout",
            }
        )
    for item in _spec_competitors(scorecard.get("collection_id")):
        price = item.get("price_from")
        if price is None:
            continue
        if currency and item.get("currency") and item.get("currency") != currency:
            continue
        rows.append(
            {
                "name": item.get("name") or "Competitor",
                "price": float(price),
                "currency": item.get("currency") or currency,
                "kind": "Competitor",
            }
        )
    return rows


def _spec_competitors(collection_id: str | None) -> list[dict]:
    if not collection_id:
        return []
    folder = Path("specs")
    if not folder.exists():
        return []
    for path in folder.glob("*.yaml"):
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if loaded.get("id") == collection_id:
            return list(loaded.get("competitors") or [])
    return []


def _stability(scorecard: dict) -> dict:
    sensitivity = scorecard.get("sensitivity") or {}
    if sensitivity.get("status") == "ok":
        return _stability_from_analysis(sensitivity, scorecard)
    return _stability_from_segments(scorecard)


def _stability_from_analysis(sensitivity: dict, scorecard: dict) -> dict:
    page = _primary_page(scorecard)
    base = page["mean"] if page else None
    points = []
    for row in sensitivity.get("dimension_influence") or []:
        points.append(
            {
                "label": str(row.get("axis") or "").replace("_", " "),
                "page": None if base is None else round(base, 2),
                "delta": row.get("mean_abs_page_delta"),
                "tau": None if row.get("mean_tau_drop") is None else round(1 - float(row["mean_tau_drop"]), 3),
            }
        )
    rank = sensitivity.get("rank_stability") or {}
    label = "WEIGHT-SENSITIVE" if sensitivity.get("page_weight_sensitive") else "ROBUST"
    return {
        "label": label,
        "note": sensitivity.get("recommendation")
        or "Reweighted from the stored per-persona scores. No new model calls.",
        "page_base": base,
        "page_low": base,
        "page_high": base,
        "kendall_mean": rank.get("kendall_tau_mean"),
        "points": points,
        "bullets": _trust_lines(scorecard, label, rank.get("kendall_tau_mean")),
    }


def _stability_from_segments(scorecard: dict) -> dict:
    pages = scorecard.get("pages") or {}
    block = pages.get("primary") or (next(iter(pages.values())) if pages else None)
    weights = {
        axis: normalize_axis(dict(levels))
        for axis, levels in (scorecard.get("persona_weights") or {}).items()
        if axis in {"trip_type", "budget_tier"} and isinstance(levels, dict)
    }
    points = []
    page_values = []
    taus = []
    base_page = None
    if block:
        base_page = round(float(block["overall"]["mean"]), 2)
        page_values.append(base_page)
    products = scorecard.get("products") or {}
    for axis, base_axis in weights.items():
        page_cells = ((block or {}).get("by_segment") or {}).get(axis) or {}
        if not page_cells:
            continue
        base_blend = _blend(base_axis, {level: float(cell["mean"]) for level, cell in page_cells.items()})
        base_product_means = _product_blend(products, axis, base_axis)
        base_order = rank_order(base_product_means)
        for level in list(base_axis):
            for delta, tag in ((0.20, "+20pp"), (-0.20, "-20pp")):
                moved = shift_axis(base_axis, level, delta)
                if moved is None or base_blend is None:
                    continue
                page_mean = _blend(moved, {name: float(cell["mean"]) for name, cell in page_cells.items()})
                product_means = _product_blend(products, axis, moved)
                order = rank_order(product_means)
                tau = kendall_tau(base_order, order) if base_order and order else None
                if page_mean is not None:
                    page_values.append(page_mean)
                if tau is not None:
                    taus.append(tau)
                points.append(
                    {
                        "label": f"{level.replace('_', ' ')} {tag}",
                        "page": None if page_mean is None else round(page_mean, 3),
                        "delta": None if page_mean is None or base_blend is None else round(page_mean - base_blend, 3),
                        "tau": None if tau is None else round(tau, 3),
                    }
                )
    kendall_mean = round(sum(taus) / len(taus), 3) if taus else None
    page_low = round(min(page_values), 3) if page_values else None
    page_high = round(max(page_values), 3) if page_values else None
    moved = any(abs(point["delta"] or 0) > PAGE_BAND for point in points)
    rank_soft = kendall_mean is not None and kendall_mean < 0.9
    label = "WEIGHT-SENSITIVE" if moved or rank_soft else "ROBUST"
    note = (
        "Built from the published segment means for trip type and budget. "
        "Individual reactions were not stored, so this chart moves those cells. "
        "It does not add within-cell noise, and it does not reweight source market."
    )
    return {
        "label": label,
        "note": note,
        "page_base": base_page,
        "page_low": page_low,
        "page_high": page_high,
        "kendall_mean": kendall_mean,
        "points": points,
        "bullets": _trust_lines(scorecard, label, kendall_mean) + [note],
    }


def _blend(weights: dict[str, float], means: dict[str, float]) -> float | None:
    num = den = 0.0
    for level, weight in weights.items():
        if level not in means:
            continue
        num += float(weight) * float(means[level])
        den += float(weight)
    if den <= 0:
        return None
    return num / den


def _product_blend(products: dict, axis: str, weights: dict[str, float]) -> dict[str, float]:
    found = {}
    for product_id, block in products.items():
        cells = (block.get("by_segment") or {}).get(axis) or {}
        means = {level: float(cell["mean"]) for level, cell in cells.items() if "mean" in cell}
        blended = _blend(weights, means)
        if blended is not None:
            found[product_id] = blended
    return found


def _trust_lines(scorecard: dict, label: str, kendall_mean) -> list[str]:
    lines = [
        "Personas are a prior, not Headout's booking mix.",
        "Absolute pass lines are not calibrated. A live Sonnet pilot compressed product means into about 3.17–3.46.",
        "Free text is mapped with Semantic Similarity Rating. Direct numeric ratings are not used.",
    ]
    if scorecard.get("mock"):
        lines.insert(0, "This run is MOCK. Do not use the verdict as a launch decision.")
    if kendall_mean is not None:
        lines.append(f"Product rank versus the base mix: mean Kendall tau {kendall_mean}. Verdict on this chart: {label}.")
    return lines


def _appendix(scorecard: dict, report: dict | None) -> dict:
    pages = []
    for source in scorecard.get("sources") or []:
        if isinstance(source, dict) and source.get("url"):
            pages.append(source["url"])
        elif isinstance(source, str):
            pages.append(source)
    if report:
        pages = list((report.get("appendix") or {}).get("pages") or pages)
    inputs = (report or {}).get("inputs") or []
    if not inputs:
        inputs = _synthetic_inputs(scorecard)
    method = ""
    if scorecard.get("method"):
        method = scorecard["method"]
        method = (
            f"SSR {method.get('paper')}, {method.get('n_personas')} personas, seed {method.get('seed')}, "
            f"embedder {method.get('embedder')}."
        )
    return {"inputs": inputs, "pages": pages, "method": method}


def _synthetic_inputs(scorecard: dict) -> list[dict]:
    has_page = bool(scorecard.get("pages"))
    has_products = bool(scorecard.get("products"))
    return [
        {"field": "collection page", "status": "used" if has_page else "not provided", "source": "headout", "detail": ""},
        {"field": "product cards", "status": "used" if has_products else "not provided", "source": "headout", "detail": ""},
        {"field": "eos_exports", "status": "not provided", "source": "", "detail": "The live pilot read the public site, not an EOS export."},
        {"field": "screenshots", "status": "not provided", "source": "", "detail": ""},
    ]


def _fmt(value) -> str:
    if value is None:
        return "—"
    return f"{float(value):.2f}"
