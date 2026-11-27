"""Shape a scorecard into the seven-part page the local tool renders.

Charts are numbers. The page draws them as inline SVG. Nothing here calls a model.
Pilot pages read reports/live-regen, which stores the cached Claude panel and the
80-mix sensitivity. They do not invent persona scores.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from collection_qa.report import CHANGE_BY_CODE, OWNER_BY_CODE, build_fixes, verdict_for

SMALL_CELL = 8


def build_view(source: dict, *, report: dict | None = None) -> dict:
    if isinstance(source.get("products"), dict):
        return _from_scorecard(source, report)
    return _from_check(source)


def load_pilot(collection_id: str, root: Path | None = None) -> dict:
    root = root or Path("reports/live-regen")
    path = root / f"{collection_id}.json"
    scorecard = json.loads(path.read_text(encoding="utf-8"))
    sensitivity_path = root / f"{collection_id}.sensitivity.json"
    if sensitivity_path.exists():
        scorecard["sensitivity"] = json.loads(sensitivity_path.read_text(encoding="utf-8"))
    return build_view(scorecard)


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


def _panel_groups(scorecard: dict, axis: str) -> dict[str, list[dict]] | None:
    panel = scorecard.get("panel_scores") or []
    if not panel:
        return None
    groups: dict[str, list[dict]] = {}
    for level in (scorecard.get("persona_weights") or {}).get(axis) or []:
        groups[level] = []
    for row in panel:
        level = (row.get("attributes") or {}).get(axis)
        if not level:
            continue
        groups.setdefault(level, []).append(row)
    return groups


def _heatmap(scorecard: dict) -> dict:
    products = scorecard.get("products") or {}
    order = [pid for pid in ((scorecard.get("rankings") or {}).get("overall") or list(products)) if pid in products]
    columns = [{"title": products[pid].get("title") or pid} for pid in order]
    groups = _panel_groups(scorecard, "trip_type")
    if groups is not None:
        rows = []
        for level, members in groups.items():
            if not members and level not in (scorecard.get("persona_weights") or {}).get("trip_type", {}):
                continue
            cells = []
            for pid in order:
                values = [
                    float(row["scores"][pid]["mean"])
                    for row in members
                    if pid in (row.get("scores") or {})
                ]
                n = len(values)
                cells.append(
                    {
                        "mean": None if not values else round(sum(values) / n, 2),
                        "n": n,
                        "faded": n < SMALL_CELL,
                    }
                )
            if any(cell["n"] for cell in cells):
                rows.append({"label": level.replace("_", " "), "cells": cells})
        return {"columns": columns, "rows": rows}
    rows = []
    levels: list[str] = []
    for pid in order:
        for level in ((products[pid].get("by_segment") or {}).get("trip_type") or {}):
            if level not in levels:
                levels.append(level)
    for level in levels:
        cells = []
        for pid in order:
            cell = ((products[pid].get("by_segment") or {}).get("trip_type") or {}).get(level) or {}
            n = int(cell.get("n") or 0)
            mean = cell.get("mean")
            cells.append({"mean": None if mean is None else round(float(mean), 2), "n": n, "faded": n < SMALL_CELL})
        rows.append({"label": level.replace("_", " "), "cells": cells})
    return {"columns": columns, "rows": rows}


def _dots(scorecard: dict) -> list[dict]:
    groups_ready = _panel_groups(scorecard, "trip_type")
    if groups_ready is not None and any("page:primary" in (row.get("scores") or {}) for row in scorecard.get("panel_scores") or []):
        dots = []
        for axis in ("trip_type", "budget_tier"):
            for level, members in (_panel_groups(scorecard, axis) or {}).items():
                values = [
                    float(row["scores"]["page:primary"]["mean"])
                    for row in members
                    if "page:primary" in (row.get("scores") or {})
                ]
                if not values:
                    continue
                n = len(values)
                dots.append(
                    {
                        "axis": axis.replace("_", " "),
                        "label": str(level).replace("_", " "),
                        "mean": round(sum(values) / n, 2),
                        "n": n,
                        "faded": n < SMALL_CELL,
                    }
                )
        return dots
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
    return {
        "label": "Not run",
        "note": "This scorecard has no per-persona reweight.",
        "page_base": None,
        "page_low": None,
        "page_high": None,
        "kendall_mean": None,
        "highlights": [],
        "dimensions": [],
        "points": [],
        "bullets": _trust_lines(scorecard, "Not run", None),
    }


def _stability_from_analysis(sensitivity: dict, scorecard: dict) -> dict:
    page_level = sensitivity.get("page_level") or {}
    primary = page_level.get("page:primary") or next(iter(page_level.values()), {})
    base = primary.get("base_mean")
    low = primary.get("scenario_min")
    high = primary.get("scenario_max")
    titles = {
        product_id: block.get("title") or product_id
        for product_id, block in (scorecard.get("products") or {}).items()
    }
    dimensions = []
    for row in sensitivity.get("dimension_influence") or []:
        dimensions.append(
            {
                "label": str(row.get("axis") or "").replace("_", " "),
                "delta": row.get("mean_abs_page_delta"),
                "tau": None if row.get("mean_tau_drop") is None else round(1 - float(row["mean_tau_drop"]), 3),
            }
        )
    rank = sensitivity.get("rank_stability") or {}
    label = "WEIGHT-SENSITIVE" if sensitivity.get("page_weight_sensitive") else (primary.get("verdict") or "ROBUST")
    n_scenarios = sensitivity.get("n_scenarios")
    note = (
        f"Reweighted the cached panel across {n_scenarios} mixes "
        "(trip type, budget, source market, and planning horizon). No new model calls."
        if n_scenarios
        else "Reweighted the stored per-persona scores. No new model calls."
    )
    if sensitivity.get("recommendation"):
        note = sensitivity["recommendation"]
    return {
        "label": label,
        "note": note,
        "page_base": None if base is None else round(float(base), 2),
        "page_low": None if low is None else round(float(low), 2),
        "page_high": None if high is None else round(float(high), 2),
        "kendall_mean": rank.get("kendall_tau_mean"),
        "highlights": _highlights(sensitivity, titles),
        "dimensions": dimensions,
        "points": dimensions,
        "bullets": _trust_lines(scorecard, label, rank.get("kendall_tau_mean")),
    }


def _highlights(sensitivity: dict, titles: dict[str, str]) -> list[dict]:
    found = []
    page = (sensitivity.get("page_level") or {}).get("page:primary") or {}
    if page:
        found.append(
            {
                "label": "Page intent across mixes",
                "detail": f"{float(page['scenario_min']):.2f}–{float(page['scenario_max']):.2f}",
                "verdict": page.get("verdict") or "",
            }
        )
    rank = sensitivity.get("rank_stability") or {}
    if rank.get("top3_same_rate") is not None:
        found.append({"label": "Top 3 held", "detail": f"{float(rank['top3_same_rate']):.0%}", "verdict": ""})
    if rank.get("bottom3_same_rate") is not None:
        found.append({"label": "Bottom 3 held", "detail": f"{float(rank['bottom3_same_rate']):.0%}", "verdict": ""})
    for finding in sensitivity.get("findings") or []:
        if finding.get("code") != "relative_rank":
            continue
        key = finding.get("key")
        title = titles.get(key, str(key or "Product"))
        short = "Flyover" if "fly" in title.lower() else title
        found.append(
            {
                "label": f"{short} stays weak",
                "detail": f"{float(finding['hold_rate']):.0%}",
                "verdict": finding.get("verdict") or "",
            }
        )
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
