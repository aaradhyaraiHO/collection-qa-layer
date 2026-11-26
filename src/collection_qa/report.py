"""Go / Fix first / Hold report as JSON, Markdown, and one HTML file.

Charts are inline SVG so the HTML file does not depend on a network.
"""

from __future__ import annotations

import html
import json
from pathlib import Path

OWNER_BY_CODE = {
    "price_consistency": "BizOps",
    "duration_consistency": "Content",
    "currency_consistency": "BizOps",
    "missing_cancellation": "Growth",
    "missing_pickup": "Growth",
    "missing_duration": "Content",
    "choice_overload": "Growth",
    "price_ladder": "Growth",
    "cannibalisation": "Growth",
    "cannibalisation_intent": "Growth",
    "gap:overnight-cruise": "Growth",
    "microbrand_disclaimer": "Content",
    "microbrand_headout_disclosure": "Content",
    "faq_missing": "Content",
    "faq_topics": "Content",
    "faq_capture_unknown": "Content",
    "page_intent": "Content",
    "product_intent": "Growth",
    "relative_rank": "Growth",
    "score_compression": "Growth",
    "segment_page_intent": "Content",
    "segment_best_product": "Growth",
}

CHANGE_BY_CODE = {
    "price_consistency": "Use the same from-price on the card and the product page.",
    "duration_consistency": "Use one duration in the card and the itinerary.",
    "missing_cancellation": "State the cancellation cutoff on the card.",
    "missing_pickup": "Say whether pickup is included, optional, or not offered.",
    "missing_duration": "Add a duration.",
    "choice_overload": "Group the list into a short ladder so the first screen is a choice, not a catalogue.",
    "price_ladder": "Add a product in the empty price band, or stop implying that band exists.",
    "microbrand_disclaimer": "Add a line that this site is not the operator or the venue.",
    "microbrand_headout_disclosure": "Say that Headout operates the site.",
    "faq_missing": "Add FAQs for cancellation, getting there, and access.",
    "faq_topics": "Cover the missing FAQ topic in the traveller's words.",
    "page_intent": "Rewrite the hero and the trust block. The blended page score is weak.",
    "product_intent": "Rework or demote this product. The panel's booking intent is low.",
    "relative_rank": "This product lags the rest of the collection. Differentiate it or take it off the page.",
    "score_compression": "Do not use the absolute pass line. Rank products inside this collection.",
    "segment_page_intent": "The page loses this traveller type. Say how the trip fits them.",
}


def verdict_for(*, status: str, issues: list[dict], has_products: bool) -> tuple[str, str]:
    if status == "NOT_FOUND" or not has_products:
        return (
            "Hold",
            "There is no bookable assortment to score yet. Find the CE or paste the EOS page before a go-live call.",
        )
    fails = [issue for issue in issues if issue.get("severity") == "fail"]
    if fails:
        return (
            "Fix first",
            f"{len(fails)} check(s) failed. Do not send this to BizOps until those rows are cleared.",
        )
    if status == "IN_PIPELINE":
        return (
            "Go",
            "No failed checks on the draft that was parsed. Warnings are still open. This is not a launch approval.",
        )
    return (
        "Go",
        "No failed checks on the live page. Warnings stay on the fix table. Absolute scores are not calibrated to conversion.",
    )


def build_fixes(issues: list[dict], quotes: list[dict], page_url: str | None) -> list[dict]:
    rows = []
    for issue in issues:
        if issue.get("severity") not in {"fail", "warn"}:
            continue
        code = issue.get("code", "")
        evidence = issue.get("evidence") or {}
        link = evidence.get("url") or evidence.get("source_url") or page_url or ""
        product_key = evidence.get("key") or evidence.get("product_id")
        quote = _quote_for(quotes, product_key)
        rows.append(
            {
                "priority": "P0" if issue["severity"] == "fail" else "P1",
                "issue": issue.get("message", code),
                "code": code,
                "page_link": link,
                "what_to_change": CHANGE_BY_CODE.get(code, "Resolve this check before content lock or go-live."),
                "owner": OWNER_BY_CODE.get(code, "Growth"),
                "quote": quote,
                "severity": issue["severity"],
            }
        )
    rows.sort(key=lambda row: (row["priority"], row["code"]))
    return rows


def _quote_for(quotes: list[dict], product_key) -> str:
    if not quotes:
        return ""
    if isinstance(product_key, str):
        for quote in quotes:
            if quote.get("stimulus_id") == product_key:
                return quote.get("text") or ""
    return quotes[0].get("text") or ""


def trust_bullets(scorecard: dict | None, *, mock: bool) -> list[str]:
    bullets = [
        "Personas are a prior, not Headout's booking mix. A segment mean is the people in that cell. It does not depend on the cell's share of the mix.",
        "Absolute pass lines (page 3.6, segment 3.4, product 3.3) are not calibrated. A live Sonnet pilot compressed means into about 3.17–3.46.",
        "Direct numeric ratings are not used. Free text is mapped with Semantic Similarity Rating (arXiv 2510.08338).",
    ]
    if mock:
        bullets.insert(
            0,
            "This run is MOCK. Reactions are templates, not Claude. Do not use the verdict as a launch decision.",
        )
    sensitivity = (scorecard or {}).get("sensitivity") or {}
    if sensitivity.get("status") == "ok":
        if sensitivity.get("page_weight_sensitive"):
            bullets.append(sensitivity.get("recommendation") or "The blended page number is weight-sensitive. Read the segments.")
        else:
            bullets.append("The blended page number stayed within 0.05 of the base mix in at least 90% of reweight scenarios.")
        stability = sensitivity.get("rank_stability") or {}
        if stability.get("kendall_tau_mean") is not None:
            bullets.append(
                f"Product rank versus the base mix: mean Kendall tau {stability['kendall_tau_mean']}."
            )
        small = sensitivity.get("small_cells") or []
        if small:
            bullets.append(
                f"{len(small)} mix cell(s) have fewer than 8 personas. Those shifts are thin. "
                + small[0]["message"]
            )
    elif sensitivity.get("status") == "missing_panel_scores":
        bullets.append("Sensitivity was not run. The scorecard has no per-persona scores.")
    return bullets


def render_markdown(report: dict) -> str:
    lines = [
        f"# {report['ce']['name']}",
        "",
        f"**{report['verdict']}.** {report['verdict_reason']}",
        "",
        f"Status: {report['status']}" + (f" ({report['stage']})" if report.get("stage") else ""),
        f"Gates: {', '.join(report['gates']) or 'none'}",
        "",
        "## Traveller quotes",
        "",
    ]
    if report.get("mock"):
        lines.append("These quotes are mock templates, not Claude.")
        lines.append("")
    for quote in report.get("quotes") or []:
        lines.append(f"> {quote.get('text', '')}")
        lines.append("")
        lines.append(f"— {quote.get('persona_label', quote.get('persona_id', ''))} on {quote.get('stimulus_title', '')}")
        lines.append("")
    lines.append("## Product chart")
    lines.append("")
    lines.append("| Product | Mean PI |")
    lines.append("| --- | ---: |")
    for product in report.get("products") or []:
        lines.append(f"| {product['title']} | {product['mean']:.2f} |")
    lines.append("")
    lines.append("## Fix table")
    lines.append("")
    lines.append("| Priority | Issue | Page | What to change | Owner | Quote |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for row in report.get("fixes") or []:
        lines.append(
            f"| {row['priority']} | {row['issue']} | {row['page_link']} | {row['what_to_change']} | {row['owner']} | {row['quote']} |"
        )
    lines.append("")
    lines.append("## By traveller type")
    lines.append("")
    for segment, summary in (report.get("by_traveller") or {}).items():
        lines.append(f"- **{segment}**: page mean {summary.get('page_mean')}, top product {summary.get('top_product')}")
    lines.append("")
    lines.append("## Detail")
    lines.append("")
    lines.append("### Microbrand vs Headout")
    lines.append("")
    lines.append(report.get("microbrand_vs_headout") or "No microbrand was resolved.")
    lines.append("")
    lines.append("### Competitors")
    lines.append("")
    if report.get("competitors"):
        for item in report["competitors"]:
            lines.append(f"- {item}")
    else:
        lines.append("No competitor rows were attached to this check.")
    lines.append("")
    lines.append("### Automated checks")
    lines.append("")
    for issue in report.get("checks") or []:
        lines.append(f"- {issue['severity']} `{issue['code']}` {issue['message']}")
    lines.append("")
    lines.append("## Can we trust it")
    lines.append("")
    for bullet in report.get("trust") or []:
        lines.append(f"- {bullet}")
    lines.append("")
    lines.append("## Appendix")
    lines.append("")
    appendix = report.get("appendix") or {}
    lines.append(f"Pages checked: {', '.join(appendix.get('pages') or []) or 'none'}")
    lines.append("")
    lines.append(appendix.get("method") or "")
    lines.append("")
    if appendix.get("slack"):
        lines.append(f"Slack: {appendix['slack']}")
        lines.append("")
    if appendix.get("eos_notes"):
        lines.append("EOS parse notes:")
        lines.append("")
        for note in appendix["eos_notes"]:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)


def render_html(report: dict) -> str:
    products = report.get("products") or []
    chart = _bar_chart([row["title"] for row in products], [row["mean"] for row in products])
    quotes = "\n".join(
        f"<blockquote><p>{html.escape(quote.get('text') or '')}</p>"
        f"<footer>{html.escape(quote.get('persona_label') or '')} on {html.escape(quote.get('stimulus_title') or '')}</footer></blockquote>"
        for quote in report.get("quotes") or []
    ) or "<p>No quotes.</p>"
    fixes = "".join(
        "<tr>"
        + "".join(
            f"<td>{html.escape(str(row[key]))}</td>"
            for key in ("priority", "issue", "page_link", "what_to_change", "owner", "quote")
        )
        + "</tr>"
        for row in report.get("fixes") or []
    )
    travellers = "".join(
        f"<li><strong>{html.escape(name)}</strong>: page mean {html.escape(str(summary.get('page_mean')))}, "
        f"top product {html.escape(str(summary.get('top_product')))}</li>"
        for name, summary in (report.get("by_traveller") or {}).items()
    )
    checks = "".join(
        f"<li><span class='{html.escape(issue['severity'])}'>{html.escape(issue['severity'])}</span> "
        f"<code>{html.escape(issue['code'])}</code> {html.escape(issue['message'])}</li>"
        for issue in report.get("checks") or []
    )
    trust = "".join(f"<li>{html.escape(item)}</li>" for item in report.get("trust") or [])
    competitors = report.get("competitors") or ["No competitor rows were attached to this check."]
    comp_html = "".join(f"<li>{html.escape(str(item))}</li>" for item in competitors)
    pages = ", ".join(html.escape(page) for page in (report.get("appendix") or {}).get("pages") or [])
    verdict = html.escape(report["verdict"])
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{html.escape(report['ce']['name'])} — {verdict}</title>
<style>
body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 960px; color: #1c1c1c; line-height: 1.45; }}
h1 {{ font-size: 1.8rem; }}
.verdict {{ padding: 1rem 1.2rem; border-radius: 8px; background: #f4f1ea; }}
.verdict strong {{ font-size: 1.4rem; }}
table {{ border-collapse: collapse; width: 100%; font-size: 0.92rem; }}
th, td {{ border-bottom: 1px solid #ddd; text-align: left; vertical-align: top; padding: 0.4rem; }}
.fail {{ color: #8d1d1d; }} .warn {{ color: #8a5a00; }} .pass {{ color: #1d6b3a; }}
blockquote {{ margin: 0 0 1rem; padding-left: 1rem; border-left: 3px solid #c4b8a5; }}
footer {{ color: #555; font-size: 0.85rem; }}
</style>
</head>
<body>
<h1>{html.escape(report['ce']['name'])}</h1>
<p>Status {html.escape(report['status'])} {html.escape(report.get('stage') or '')}. Gates {html.escape(', '.join(report.get('gates') or []))}. CE {html.escape(str(report['ce'].get('ce_id') or ''))}.</p>
<section class="verdict"><strong>{verdict}</strong><p>{html.escape(report['verdict_reason'])}</p></section>
<h2>Traveller quotes</h2>
{quotes}
<h2>Product chart</h2>
{chart}
<h2>Fix table</h2>
<table><thead><tr><th>Priority</th><th>Issue</th><th>Page</th><th>What to change</th><th>Owner</th><th>Quote</th></tr></thead><tbody>{fixes}</tbody></table>
<h2>By traveller type</h2>
<ul>{travellers}</ul>
<h2>Detail</h2>
<h3>Product scores</h3>
{chart}
<h3>Microbrand vs Headout</h3>
<p>{html.escape(report.get('microbrand_vs_headout') or 'No microbrand was resolved.')}</p>
<h3>Competitors</h3>
<ul>{comp_html}</ul>
<h3>Automated checks</h3>
<ul>{checks}</ul>
<h2>Can we trust it</h2>
<ul>{trust}</ul>
<h2>Appendix</h2>
<p>Pages checked: {pages or 'none'}</p>
<p>{html.escape((report.get('appendix') or {}).get('method') or '')}</p>
<p>{html.escape((report.get('appendix') or {}).get('slack') or '')}</p>
</body>
</html>
"""


def _bar_chart(labels: list[str], values: list[float]) -> str:
    if not values:
        return "<p>No product scores.</p>"
    width = 640
    row_h = 28
    height = row_h * len(values) + 10
    max_value = 5
    parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img">']
    for index, (label, value) in enumerate(zip(labels, values)):
        y = index * row_h + 4
        bar = (max(value, 0) / max_value) * (width - 220)
        parts.append(
            f'<text x="0" y="{y + 16}" font-size="12">{html.escape(label[:32])}</text>'
            f'<rect x="210" y="{y}" width="{bar:.1f}" height="18" fill="#3d5a40"></rect>'
            f'<text x="{214 + bar:.1f}" y="{y + 14}" font-size="12">{value:.2f}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


def write_report(report: dict, directory: str | Path, stem: str) -> tuple[Path, Path, Path]:
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    json_path = directory / f"{stem}.check.json"
    md_path = directory / f"{stem}.check.md"
    html_path = directory / f"{stem}.check.html"
    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    html_path.write_text(render_html(report), encoding="utf-8")
    return json_path, md_path, html_path
