"""Run a collection through personas, free-text intent, SSR, and the two gates."""

from __future__ import annotations

import os
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from collection_qa.anchors import ANCHOR_SETS, iter_anchors
from collection_qa.checks import run_checks
from collection_qa.cost import actual_cost, estimate_cost
from collection_qa.embeddings import Embedder, build_embedder
from collection_qa.checks import CheckResult
from collection_qa.gates import (
    cannibalisation_pairs,
    choice_overload,
    price_ladder_fit,
    research_status,
    rollup,
    segment_means,
    synthetic_page_issue,
    synthetic_product_issues,
    top_and_bottom,
)
from collection_qa.thresholds import CANNIBAL_JACCARD, CANNIBAL_PRICE_RATIO
from collection_qa.llm import AnthropicCompleter, LLMCache
from collection_qa.mock_llm import react_page, react_product
from collection_qa.models import CollectionSpec
from collection_qa.personas import Persona, sample_personas
from collection_qa.prompts import SYSTEM_PROMPT, page_user, product_user
from collection_qa.scorecard import write_json, write_markdown
from collection_qa.ssr import average_pmfs, mean_rating, rate_embedding


def _pmf_dict(pmf: np.ndarray) -> dict[str, float]:
    return {str(i + 1): round(float(pmf[i]), 4) for i in range(5)}


def _anchor_matrix(embedder: Embedder) -> dict[str, np.ndarray]:
    rows = iter_anchors()
    vectors = embedder.encode([text for _, _, text in rows])
    grouped: dict[str, list[np.ndarray]] = defaultdict(list)
    for (set_id, _rating, _text), vector in zip(rows, vectors):
        grouped[set_id].append(vector)
    return {set_id: np.stack(vectors, axis=0) for set_id, vectors in grouped.items()}


def _embed_map(embedder: Embedder, texts: list[str]) -> dict[str, np.ndarray]:
    unique = list(dict.fromkeys(texts))
    if not unique:
        return {}
    vectors = embedder.encode(unique)
    return {text: vectors[index] for index, text in enumerate(unique)}


def _complete_live(completer: AnthropicCompleter, prompts: list[str], workers: int) -> list[str]:
    outputs: list[str | None] = [None] * len(prompts)

    def one(index: int) -> None:
        outputs[index] = completer.complete(prompts[index], system=SYSTEM_PROMPT).text

    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        list(pool.map(one, range(len(prompts))))
    return [text or "" for text in outputs]


def _banner(mode: str, embedder_name: str, catalog_status: str) -> str:
    catalog = "Proposed assortment from competitor listings." if catalog_status == "proposed_from_competitors" else "Catalog seeded from live Headout pages and APIs."
    if mode == "MOCK":
        return (
            "MOCK OUTPUT. Free-text reactions come from a rule-based stand-in, not Claude. "
            f"Embeddings: {embedder_name}. "
            "Read purchase-intent numbers as a worked example of the scorecard. "
            "Read deterministic checks as findings about the fetched pages. "
            + catalog
        )
    return (
        "LIVE OUTPUT. Free-text reactions come from Claude and were mapped with SSR. "
        f"Embeddings: {embedder_name}. "
        "Synthetic purchase intent is an uncalibrated screening signal. "
        + catalog
    )


def _quotes(spec, personas, product_texts, product_cell_means, page_texts, page_means) -> list[dict]:
    by_id = {persona.id: persona for persona in personas}
    quotes: list[dict] = []
    if page_means:
        ordered = sorted(page_means.items(), key=lambda item: item[1])
        for persona_id, mean in (ordered[0], ordered[-1]):
            persona = by_id[persona_id]
            quotes.append(
                {
                    "scope": "page",
                    "persona_id": persona_id,
                    "label": persona.summary(),
                    "mean_pi": round(mean, 3),
                    "text": page_texts[(persona_id, 0)],
                }
            )
    products = {product.id: product for product in spec.products}
    for trip_type in ("solo", "couple", "family_with_kids", "friends"):
        members = [persona for persona in personas if persona.trip_type == trip_type and not persona.ablated]
        if not members:
            continue
        per_product: dict[str, float] = {}
        for product in spec.products:
            values = [product_cell_means[(product.id, persona.id)] for persona in members if (product.id, persona.id) in product_cell_means]
            if values:
                per_product[product.id] = float(np.mean(values))
        if not per_product:
            continue
        ordered = sorted(per_product.items(), key=lambda item: item[1])
        for product_id, mean in (ordered[0], ordered[-1]):
            persona = members[0]
            quotes.append(
                {
                    "scope": f"product:{products[product_id].title}",
                    "persona_id": persona.id,
                    "label": f"{trip_type} · mean PI {mean:.2f} · {persona.summary()}",
                    "mean_pi": round(product_cell_means.get((product_id, persona.id), mean), 3),
                    "text": product_texts[(persona.id, product_id, 0)],
                }
            )
    return quotes


def run_collection(
    spec: CollectionSpec,
    *,
    n_personas: int = 30,
    seed: int = 20261126,
    dry_run: bool = False,
    gate: str = "both",
    model: str = "claude-sonnet-5-5",
    embedder_kind: str = "sentence-transformers",
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
    workers: int = 8,
    completions: int = 1,
    epsilon: float = 0.0,
    ssr_temperature: float = 1.0,
    llm_temperature: float = 0.5,
    max_products: int = 0,
    ablate_personas: bool = False,
    cache_dir: Path | None = None,
    out_dir: Path | None = None,
) -> dict:
    if gate not in ("A", "B", "both"):
        raise ValueError("gate must be A, B, or both")
    if completions < 1:
        raise ValueError("completions must be at least 1")
    if not dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is not set. Re-run with --dry-run to use the mock generator.")

    if max_products and max_products < len(spec.products):
        spec.products = spec.products[:max_products]

    panel = sample_personas(
        spec.id,
        n_personas,
        seed=seed,
        override=spec.persona_weights,
        ablate=ablate_personas,
    )
    run_products = gate in ("A", "both")
    run_page = gate in ("B", "both")

    product_prompts: list[str] = []
    product_jobs: list[tuple[str, str, int]] = []
    if run_products:
        for persona in panel.personas:
            for product in spec.products:
                for sample_index in range(completions):
                    product_jobs.append((persona.id, product.id, sample_index))
                    product_prompts.append(product_user(persona, product, spec.destination) + SYSTEM_PROMPT)
    page_jobs: list[tuple[str, int]] = []
    page_prompts: list[str] = []
    if run_page:
        for persona in panel.personas:
            for sample_index in range(completions):
                page_jobs.append((persona.id, sample_index))
                page_prompts.append(page_user(persona, spec) + SYSTEM_PROMPT)

    estimate = estimate_cost(model, product_prompts + page_prompts, completions=1)
    print(
        f"Cost estimate ({model}): {estimate.calls} calls, "
        f"~{estimate.input_tokens} input tokens, ~{estimate.output_tokens} output tokens, "
        f"~${estimate.usd:.2f}. {estimate.note}"
    )
    if dry_run:
        print("Mode: MOCK. No Anthropic call. The estimate is what a live run of this prompt set would cost.")

    by_persona = {persona.id: persona for persona in panel.personas}
    by_product = {product.id: product for product in spec.products}
    product_texts: dict[tuple[str, str, int], str] = {}
    page_texts: dict[tuple[str, int], str] = {}

    if dry_run:
        for persona_id, product_id, sample_index in product_jobs:
            product_texts[(persona_id, product_id, sample_index)] = react_product(
                by_persona[persona_id], by_product[product_id]
            )
        for persona_id, sample_index in page_jobs:
            page_texts[(persona_id, sample_index)] = react_page(by_persona[persona_id], spec)
        actual_input = 0
        actual_output = 0
        llm_name = "mock-rule-based"
    else:
        cache = LLMCache((cache_dir or Path(".cache/collection-qa")) / "llm.sqlite")
        completer = AnthropicCompleter(model, temperature=llm_temperature, cache=cache)
        if product_prompts:
            filled = _complete_live(completer, [product_user(by_persona[p], by_product[prod], spec.destination) for p, prod, _ in product_jobs], workers)
            for job, text in zip(product_jobs, filled):
                product_texts[job] = text
        if page_prompts:
            filled = _complete_live(completer, [page_user(by_persona[p], spec) for p, _ in page_jobs], workers)
            for job, text in zip(page_jobs, filled):
                page_texts[job] = text
        actual_input = completer.input_tokens
        actual_output = completer.output_tokens
        llm_name = model
        spent = actual_cost(model, actual_input, actual_output)
        print(
            f"Actual tokens: input {actual_input}, output {actual_output}, "
            f"API calls {completer.api_calls}, cache hits {completer.cache_hits}, "
            f"approx ${0 if spent is None else spent:.4f}."
        )

    embedder = build_embedder(embedder_kind, embedding_model)
    print(f"Embedding with {embedder.name} …")
    anchors = _anchor_matrix(embedder)
    text_vectors = _embed_map(embedder, list(product_texts.values()) + list(page_texts.values()))

    def score(text: str) -> np.ndarray:
        return rate_embedding(
            text_vectors[text],
            anchors,
            epsilon=epsilon,
            temperature=ssr_temperature,
        ).pmf

    product_cell_pmf: dict[tuple[str, str], np.ndarray] = {}
    product_cell_means: dict[tuple[str, str], float] = {}
    for persona in panel.personas:
        for product in spec.products:
            samples = [product_texts[(persona.id, product.id, i)] for i in range(completions) if (persona.id, product.id, i) in product_texts]
            if not samples:
                continue
            pmf = average_pmfs([score(text) for text in samples])
            product_cell_pmf[(product.id, persona.id)] = pmf
            product_cell_means[(product.id, persona.id)] = mean_rating(pmf)

    page_pmf_by_persona: dict[str, np.ndarray] = {}
    page_means: dict[str, float] = {}
    for persona in panel.personas:
        samples = [page_texts[(persona.id, i)] for i in range(completions) if (persona.id, i) in page_texts]
        if not samples:
            continue
        pmf = average_pmfs([score(text) for text in samples])
        page_pmf_by_persona[persona.id] = pmf
        page_means[persona.id] = mean_rating(pmf)

    product_rows = []
    product_means: dict[str, float] = {}
    for product in spec.products:
        pmfs = [product_cell_pmf[(product.id, persona.id)] for persona in panel.personas if (product.id, persona.id) in product_cell_pmf]
        if not pmfs:
            continue
        pmf = average_pmfs(pmfs)
        mean = mean_rating(pmf)
        product_means[product.id] = mean
        product_rows.append(
            {
                "product_id": product.id,
                "title": product.title,
                "price": product.price,
                "currency": product.currency,
                "price_unit": product.price_unit,
                "duration": product.duration,
                "rating": product.rating,
                "review_count": product.review_count,
                "mean_pi": round(mean, 3),
                "distribution": _pmf_dict(pmf),
                "tags": product.tags,
            }
        )

    page_distribution = None
    page_mean = None
    if page_pmf_by_persona:
        page_pmf = average_pmfs(list(page_pmf_by_persona.values()))
        page_mean = mean_rating(page_pmf)
        page_distribution = _pmf_dict(page_pmf)

    deterministic = run_checks(spec)
    structural = []
    pairs = cannibalisation_pairs(spec) if run_products or gate == "both" else []
    if pairs:
        structural.append(
            {
                "id": "cannibalisation",
                "severity": "warn",
                "gate": "A",
                "blocks_go_live": False,
                "message": (
                    f"{len(pairs)} product pair(s) share a duration, a from-price within "
                    f"{int(round((CANNIBAL_PRICE_RATIO - 1) * 100))}%, and a title overlap of at least "
                    f"{CANNIBAL_JACCARD:.0%}. Review whether both need to sit on the collection. "
                    "First pairs: "
                    + "; ".join(f"{item['a']} vs {item['b']} (J={item['jaccard']})" for item in pairs[:6])
                ),
                "product_ids": sorted({pid for item in pairs for pid in (item["a"], item["b"])}),
                "evidence": {"pairs": pairs[:12]},
            }
        )
    else:
        structural.append(
            {
                "id": "cannibalisation",
                "severity": "pass",
                "gate": "A",
                "blocks_go_live": False,
                "message": (
                    "No pair shares a duration, a close from-price, and a high title overlap. "
                    f"Thresholds: Jaccard ≥ {CANNIBAL_JACCARD:.0%}, price ratio ≤ {CANNIBAL_PRICE_RATIO}."
                ),
                "product_ids": [],
                "evidence": {},
            }
        )
    overload = choice_overload(spec, product_means or None)
    if overload is not None:
        structural.append(overload.as_dict())
    if run_products:
        for issue in price_ladder_fit(spec, panel.personas, product_cell_means):
            structural.append(issue.as_dict())

    research = []
    if run_products:
        product_issues = synthetic_product_issues(product_means, by_product)
        if product_issues:
            research.extend(issue.as_dict() for issue in product_issues)
        elif product_means:
            research.append(
                {
                    "id": "synthetic_product_pi",
                    "severity": "pass",
                    "gate": "A",
                    "blocks_go_live": False,
                    "message": "Every scored product is at or above the uncalibrated pass band. This does not block go-live.",
                    "product_ids": [],
                    "evidence": {},
                }
            )
    page_issue = synthetic_page_issue(page_mean)
    if page_issue is not None:
        research.append(page_issue.as_dict())

    gate_a_inputs = list(deterministic) + [
        CheckResult(
            id=item["id"],
            severity=item["severity"],
            gate=item["gate"],
            blocks_go_live=item["blocks_go_live"],
            message=item["message"],
            product_ids=item.get("product_ids") or [],
            evidence=item.get("evidence") or {},
        )
        for item in structural
    ]
    segments: dict[str, dict] = {}
    for attribute in ("budget_tier", "trip_type", "experience"):
        grouped = segment_means(panel.personas, [p.id for p in spec.products], product_cell_means, attribute)
        segments[attribute] = {}
        for label, means in grouped.items():
            members = [persona for persona in panel.personas if getattr(persona, attribute) == label and not persona.ablated]
            segments[attribute][label] = {
                "n": len(members),
                "thin": len(members) < 5,
                **top_and_bottom(means, by_product),
            }

    checks_out = [item.as_dict() for item in deterministic] + structural + research
    mode = "MOCK" if dry_run else "LIVE"
    spent = 0.0 if dry_run else (actual_cost(model, actual_input, actual_output) or 0.0)
    scorecard = {
        "banner": _banner(mode, embedder.name, spec.catalog_status),
        "meta": {
            "mode": mode,
            "name": spec.name,
            "collection_spec_id": spec.id,
            "collection_id": spec.collection_id,
            "ce_id": spec.ce_id,
            "page_type": spec.page_type,
            "catalog_status": spec.catalog_status,
            "destination": spec.destination,
            "fetched_at": spec.fetched_at,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "n_personas": n_personas,
            "seed": seed,
            "ablate_personas": ablate_personas,
            "llm": llm_name,
            "llm_temperature": llm_temperature,
            "completions": completions,
            "embedding_model": embedder.name,
            "epsilon": epsilon,
            "ssr_temperature": ssr_temperature,
            "anchor_sets": list(ANCHOR_SETS),
            "persona_assumption": panel.assumption_basis,
            "persona_counts": {
                "budget_tier": panel.counts("budget_tier"),
                "trip_type": panel.counts("trip_type"),
                "experience": panel.counts("experience"),
                "base": panel.counts("base"),
            },
            "unknowns": spec.unknowns,
            "sources": spec.sources,
            "cost": {
                **estimate.as_dict(),
                "actual_input_tokens": actual_input,
                "actual_output_tokens": actual_output,
                "actual_usd": round(spent, 4),
            },
        },
        "checks": checks_out,
        "gate_a": {
            "status": rollup(gate_a_inputs, "A"),
            "research_status": research_status(
                [
                    CheckResult(
                        id=item["id"],
                        severity=item["severity"],
                        gate=item["gate"],
                        blocks_go_live=False,
                        message=item["message"],
                    )
                    for item in research
                ],
                "A",
            ),
            "products": product_rows,
            "segments": segments,
            "cannibalisation_pairs": pairs[:12],
        },
        "gate_b": {
            "status": rollup(gate_a_inputs, "B"),
            "research_status": research_status(
                [
                    CheckResult(
                        id=item["id"],
                        severity=item["severity"],
                        gate=item["gate"],
                        blocks_go_live=False,
                        message=item["message"],
                    )
                    for item in research
                ],
                "B",
            ),
            "page": {"mean_pi": None if page_mean is None else round(page_mean, 3), "distribution": page_distribution},
        },
        "quotes": _quotes(spec, panel.personas, product_texts, product_cell_means, page_texts, page_means),
    }
    if out_dir is not None:
        out = Path(out_dir)
        write_json(scorecard, out / f"{spec.id}.scorecard.json")
        write_markdown(scorecard, out / f"{spec.id}.scorecard.md")
        print(f"Wrote {out / (spec.id + '.scorecard.json')}")
    print(
        f"Gate A {scorecard['gate_a']['status']} (research {scorecard['gate_a']['research_status']}); "
        f"Gate B {scorecard['gate_b']['status']} (research {scorecard['gate_b']['research_status']})."
    )
    return scorecard
