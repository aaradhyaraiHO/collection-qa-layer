"""JSON and Markdown scorecards."""

from __future__ import annotations

import json
from pathlib import Path


def write_json(scorecard: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scorecard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _fmt_dist(dist: dict | None) -> str:
    if not dist:
        return ""
    return " ".join(f"{k}:{dist[k]:.2f}" for k in ("1", "2", "3", "4", "5") if k in dist)


def render_markdown(scorecard: dict) -> str:
    meta = scorecard["meta"]
    mode = meta["mode"]
    lines: list[str] = [
        f"# {mode} scorecard — {meta['name']}",
        "",
        scorecard["banner"],
        "",
        f"- Collection `{meta['collection_spec_id']}` · public id {meta.get('collection_id') or 'unknown'} · {meta['page_type']} · {meta['catalog_status']}",
        f"- Fetched {meta['fetched_at']} · personas {meta['n_personas']} · seed {meta['seed']}",
        f"- LLM: {meta['llm']} · embeddings: {meta['embedding_model']}",
        f"- SSR: ε={meta['epsilon']}, T={meta['ssr_temperature']}, anchor sets={meta['anchor_sets']}",
        f"- Estimated live cost: ${meta['cost']['estimated_usd']:.2f} ({meta['cost']['note']})",
        f"- Actual API spend recorded this run: ${meta['cost'].get('actual_usd') or 0:.4f}",
        "",
        "## How to read this",
        "",
        "Purchase-intent distributions are 5-point booking-intent pmfs from semantic similarity rating. "
        "The mean is the expected rating. Pass ≥ 3.6, warn ≥ 3.0, and below 3.0 is a research fail. "
        "Those bands are uncalibrated assumptions and do not block go-live. "
        "A gate fails only when a deterministic check fails.",
        "",
        f"**Gate A (post-assortment):** {scorecard['gate_a']['status']} · research signal {scorecard['gate_a']['research_status']}",
        "",
        f"**Gate B (post-content-lock):** {scorecard['gate_b']['status']} · research signal {scorecard['gate_b']['research_status']}",
        "",
    ]
    if meta.get("unknowns"):
        lines.append("## Unknowns in the spec")
        lines.append("")
        for item in meta["unknowns"]:
            lines.append(f"- {item}")
        lines.append("")

    def table(title: str, rows: list[dict]) -> None:
        lines.append(title)
        lines.append("")
        lines.append("| Severity | Id | Gate | Blocks | What it found |")
        lines.append("| --- | --- | --- | --- | --- |")
        for check in rows:
            if check["severity"] == "pass":
                continue
            blocks = "yes" if check["blocks_go_live"] else "no"
            message = check["message"].replace("|", "/")
            lines.append(f"| {check['severity']} | {check['id']} | {check['gate']} | {blocks} | {message} |")
        lines.append("")

    research_ids = {"synthetic_product_pi", "synthetic_page_pi"}
    structural = [check for check in scorecard["checks"] if check["id"] not in research_ids]
    research = [check for check in scorecard["checks"] if check["id"] in research_ids]
    table("## Deterministic and assortment checks", structural)
    passed = []
    for check in structural:
        if check["severity"] == "pass" and check["id"] not in passed:
            passed.append(check["id"])
    lines.append("Passed: " + (", ".join(passed) if passed else "none") + ".")
    lines.append("")
    table("## Research signals (synthetic purchase intent, not a go-live block)", research)

    lines.append("## Gate A — products")
    lines.append("")
    lines.append("| Product | Price | Mean PI | Distribution | Reviews |")
    lines.append("| --- | --- | --- | --- | --- |")
    for row in scorecard["gate_a"]["products"]:
        price = "n/a" if row["price"] is None else f"{row['price']:g} {row['currency']} {row['price_unit']}"
        lines.append(
            f"| {row['title']} | {price} | {row['mean_pi']:.2f} | {_fmt_dist(row['distribution'])} | {row['review_count']} |"
        )
    lines.append("")
    lines.append("### Top and bottom by segment")
    lines.append("")
    for attribute, segments in scorecard["gate_a"]["segments"].items():
        lines.append(f"**{attribute}**")
        lines.append("")
        for label, block in segments.items():
            top = ", ".join(f"{item['title']} ({item['mean_pi']:.2f})" for item in block["top"][:2])
            bottom = ", ".join(f"{item['title']} ({item['mean_pi']:.2f})" for item in block["bottom"][:2])
            lines.append(f"- {label} (n={block['n']}): high {top}; low {bottom}")
        lines.append("")

    page = scorecard["gate_b"]["page"]
    lines.append("## Gate B — page")
    lines.append("")
    if page.get("mean_pi") is None:
        lines.append("Page-level reactions were not run.")
    else:
        lines.append(f"Mean PI **{page['mean_pi']:.2f}**. Distribution {_fmt_dist(page.get('distribution'))}.")
    lines.append("")
    lines.append("## Sample persona quotes")
    lines.append("")
    for quote in scorecard["quotes"]:
        lines.append(f"- **{quote['scope']}** · {quote['persona_id']} · {quote.get('label', '')}")
        lines.append(f"  > {quote['text']}")
        lines.append("")
    lines.append("## Sources")
    lines.append("")
    for source in meta.get("sources") or []:
        lines.append(f"- {source.get('url')} — {source.get('role', '')}")
    lines.append("")
    return "\n".join(lines)


def write_markdown(scorecard: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_markdown(scorecard), encoding="utf-8")
