"""Write a scorecard as JSON and Markdown."""

from __future__ import annotations

import json
from pathlib import Path

from collection_qa.cost import CostEstimate


def write_scorecard(payload: dict, directory: str | Path) -> tuple[Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stem = payload["collection_id"]
    json_path = directory / f"{stem}.json"
    md_path = directory / f"{stem}.md"
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(payload), encoding="utf-8")
    return json_path, md_path


def render_markdown(payload: dict) -> str:
    lines: list[str] = []
    title = payload["collection_name"]
    lines.append(f"# Collection QA scorecard: {title}")
    lines.append("")
    if payload.get("banner"):
        lines.append(f"> **{payload['banner']}**")
        lines.append("")
    lines.append(f"- Collection id: `{payload['collection_id']}`")
    if payload.get("ce_id"):
        lines.append(f"- CE / collection id on Headout: `{payload['ce_id']}`")
    lines.append(f"- Destination: {payload['destination']}")
    lines.append(f"- Provenance: **{payload['provenance']}**. {payload['provenance_note']}")
    lines.append(f"- Source pages fetched: {payload['fetched_on']}")
    lines.append(f"- Scorecard generated: {payload['generated_at']}")
    seed = payload.get("seed", payload.get("method", {}).get("seed"))
    if seed is not None:
        lines.append(f"- Persona seed: **{seed}**")
    lines.append("")
    method = payload["method"]
    lines.append("## Method")
    lines.append("")
    lines.append(
        f"Semantic Similarity Rating (arXiv 2510.08338): free-text booking intent, "
        f"embedded with `{method['embedder']}`, cosine similarity to {method['anchor_sets']} "
        f"sets of travel Likert anchors, minimum-similarity subtraction "
        f"(epsilon={method['epsilon']}, temperature={method['temperature']}), "
        f"then the per-set distributions are averaged."
    )
    lines.append("")
    lines.append(
        f"Panel: {method['n_personas']} personas, seed {method['seed']}, "
        f"profile weights are assumptions. Model `{method['model']}`, "
        f"{method['completions']} completion(s) per prompt. "
        f"LLM calls made: {method['llm_calls_made']}. Cache hits: {method['cache_hits']}."
    )
    lines.append("")
    lines.append(payload["persona_assumption"])
    lines.append("")
    lines.append("## Cost")
    lines.append("")
    cost = payload["cost"]
    estimate = CostEstimate(
        model=cost["model"],
        calls=cost["calls"],
        input_tokens=cost["input_tokens"],
        output_tokens=cost["output_tokens"],
        input_usd_per_mtok=cost["input_usd_per_mtok"],
        output_usd_per_mtok=cost["output_usd_per_mtok"],
        usd=cost["usd"],
        price_known=cost["price_known"],
        actual_usage=cost["actual_usage"],
    )
    for line in estimate.lines():
        lines.append(line)
    if cost.get("note"):
        lines.append(cost["note"])
    lines.append("")
    lines.append("## Gate results")
    lines.append("")
    lines.append(_issue_table(payload["issues"]))
    lines.append("")
    if payload.get("pages"):
        lines.append("## Page purchase intent (Gate B)")
        lines.append("")
        for role, block in payload["pages"].items():
            lines.append(f"### {role}: {block['title']}")
            lines.append("")
            lines.append(f"Page type: {block['page_type']}. URL: {block.get('url') or 'unknown'}.")
            lines.append("")
            lines.append(_dist_line("All personas", block["overall"]))
            lines.append("")
            lines.extend(_segment_lines(block["by_segment"]))
            lines.append("")
    if payload.get("products"):
        lines.append("## Product purchase intent (Gate A)")
        lines.append("")
        ranked = payload["rankings"]["overall"]
        has_z = any("z_vs_collection" in payload["products"][product_id] for product_id in ranked)
        if has_z:
            lines.append("| Product | Mean PI | z vs collection | n | pmf 1–5 |")
            lines.append("| --- | ---: | ---: | ---: | --- |")
        else:
            lines.append("| Product | Mean PI | n | pmf 1–5 |")
            lines.append("| --- | ---: | ---: | --- |")
        for product_id in ranked:
            block = payload["products"][product_id]
            overall = block["overall"]
            pmf = " ".join(f"{point}:{overall['pmf'][point]:.2f}" for point in ("1", "2", "3", "4", "5"))
            if has_z:
                lines.append(
                    f"| {block['title']} | {overall['mean']:.2f} | {block['z_vs_collection']:+.2f} | "
                    f"{overall['n']} | {pmf} |"
                )
            else:
                lines.append(
                    f"| {block['title']} | {overall['mean']:.2f} | {overall['n']} | {pmf} |"
                )
        lines.append("")
        if has_z:
            lines.append(
                "z is this product's mean minus the mean of product means in this run, "
                "divided by their standard deviation. Absolute pass lines are not calibrated "
                "to conversion. A negative z is a product this panel liked less than the rest "
                "of the collection, even when every mean sits in a narrow band."
            )
            lines.append("")
        lines.append("## Top and bottom products by segment")
        lines.append("")
        for axis, segments in payload["rankings"]["by_segment"].items():
            lines.append(f"### {axis}")
            lines.append("")
            for segment, order in segments.items():
                if not order:
                    continue
                top = _names(payload, order[:3], axis, segment)
                bottom = _names(payload, list(reversed(order[-3:])), axis, segment)
                lines.append(f"- **{segment}** — top: {top}. Bottom, lowest first: {bottom}.")
            lines.append("")
    if payload.get("quotes"):
        lines.append("## Sample persona quotes")
        lines.append("")
        if payload.get("mock"):
            lines.append("These quotes were written by the mock template, not by Claude.")
            lines.append("")
        for quote in payload["quotes"]:
            lines.append(
                f"- **{quote['persona_id']}** on {quote['stimulus_title']} "
                f"(mean PI {quote['mean_pi']:.2f}, {quote['generator']}): "
                f"{quote['persona_label']}"
            )
            lines.append(f"  > {quote['text']}")
            lines.append("")
    if payload.get("sensitivity"):
        from collection_qa.sensitivity import render_sensitivity_section

        lines.append(render_sensitivity_section(payload["sensitivity"]))
    lines.append("## Unknowns in the source capture")
    lines.append("")
    for item in payload.get("unknowns", []):
        lines.append(f"- {item}")
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    for source in payload.get("sources", []):
        lines.append(f"- {source['fetched_on']}: {source['what']} — {source['url']}")
    lines.append("")
    thresholds = payload.get("thresholds", {})
    if thresholds:
        lines.append("## Thresholds")
        lines.append("")
        lines.append(thresholds.get("note", ""))
        lines.append("")
        for key, value in thresholds.items():
            if key == "note":
                continue
            lines.append(f"- {key}: {value}")
        lines.append("")
    lines.append(
        "Calibration against live CVR is not done in this scorecard. "
        "Shadow the next MMP and compare product rank to realized conversion "
        "before these pass/warn/fail cuts become a gate."
    )
    lines.append("")
    return "\n".join(lines)


def _names(payload: dict, ids: list[str], axis: str, segment: str) -> str:
    parts = []
    for product_id in ids:
        block = payload["products"][product_id]
        summary = block["by_segment"][axis][segment]
        parts.append(f"{block['title']} ({summary['mean']:.2f})")
    return "; ".join(parts)


def _dist_line(label: str, summary: dict) -> str:
    pmf = ", ".join(f"{point}={summary['pmf'][point]:.2f}" for point in ("1", "2", "3", "4", "5"))
    return f"- {label}: mean **{summary['mean']:.2f}** (n={summary['n']}; {pmf})"


def _segment_lines(by_segment: dict) -> list[str]:
    lines = []
    for axis, groups in by_segment.items():
        lines.append(f"By {axis}:")
        lines.append("")
        for key, summary in groups.items():
            lines.append(_dist_line(key, summary))
        lines.append("")
    return lines


def _issue_table(issues: list[dict]) -> str:
    if not issues:
        return "No checks ran."
    lines = ["| Gate | Severity | Code | Finding |", "| --- | --- | --- | --- |"]
    order = {"fail": 0, "warn": 1, "pass": 2}
    ranked = sorted(issues, key=lambda issue: (order.get(issue["severity"], 9), issue["gate"], issue["code"]))
    for issue in ranked:
        message = issue["message"].replace("|", "\\|")
        lines.append(f"| {issue['gate']} | {issue['severity']} | `{issue['code']}` | {message} |")
    return "\n".join(lines)
