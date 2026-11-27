"""Run a persona panel, elicit reactions, and score them with SSR."""

from __future__ import annotations

from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone

import threading

import numpy as np

from collection_qa.anchors import ANCHOR_SETS, DEFAULT_EPSILON, DEFAULT_TEMPERATURE
from collection_qa.checks import (
    CANNIBAL_PI_DELTA,
    COMPRESSION_RANGE,
    PAGE_MEAN_PASS,
    PAGE_MEAN_WARN,
    PRODUCT_MEAN_PASS,
    PRODUCT_MEAN_WARN,
    RELATIVE_Z_FAIL,
    RELATIVE_Z_WARN,
    SEGMENT_MEAN_PASS,
    SEGMENT_MEAN_WARN,
    cannibalisation_from_intent,
    intent_issues,
    relative_ranking_issues,
    run_deterministic_checks,
    z_scores,
)
from collection_qa.cost import estimate_cost, planned_calls
from collection_qa.embeddings import DEFAULT_ST_MODEL, build_embedder
from collection_qa.llm import DEFAULT_MAX_RETRIES, DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT_SECONDS, LLMClient, LLMResult
from collection_qa.models import CollectionSpec, DistributionSummary, Quote
from collection_qa.personas import ASSUMPTION_NOTE, Persona, sample_personas
from collection_qa.sensitivity import analyze_panel
from collection_qa.ssr import mean_rating, pmf_as_dict, ssr_pmf

SEGMENT_AXES = ("trip_type", "budget_tier")


@dataclass
class RunConfig:
    mock: bool = False
    model: str = "claude-sonnet-5-5"
    embedder: str = "lexical"
    embedding_model: str = DEFAULT_ST_MODEL
    n_personas: int = 30
    seed: int = 7
    concurrency: int = 8
    cache_path: str | None = None
    completions: int = 1
    epsilon: float = DEFAULT_EPSILON
    temperature: float = DEFAULT_TEMPERATURE
    gates: set[str] = field(default_factory=lambda: {"A", "B"})
    max_tokens: int = DEFAULT_MAX_TOKENS
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    progress: object | None = None


@dataclass
class _Job:
    persona: Persona
    stimulus_id: str
    stimulus_title: str
    product_id: str | None
    surface_role: str | None
    completion_index: int


def _summary(pmfs: list[np.ndarray]) -> DistributionSummary:
    stacked = np.vstack(pmfs)
    avg = stacked.mean(axis=0)
    return DistributionSummary(n=len(pmfs), pmf=pmf_as_dict(avg), mean=mean_rating(avg))


def _group_summaries(
    records: list[tuple[Persona, np.ndarray]],
) -> dict[str, dict[str, DistributionSummary]]:
    grouped: dict[str, dict[str, list[np.ndarray]]] = {axis: defaultdict(list) for axis in SEGMENT_AXES}
    for persona, pmf in records:
        for axis in SEGMENT_AXES:
            grouped[axis][getattr(persona, axis)].append(pmf)
    return {
        axis: {key: _summary(pmfs) for key, pmfs in buckets.items()}
        for axis, buckets in grouped.items()
    }


def _progress(config: RunConfig, stage: str, detail: str, current: int | None = None, total: int | None = None) -> None:
    callback = config.progress
    if callback is None:
        return
    callback(stage, detail, current, total)


def run_collection(spec: CollectionSpec, config: RunConfig) -> dict:
    panel = sample_personas(
        n=config.n_personas,
        profile=spec.audience_profile,
        seed=config.seed,
        override=spec.persona_weights,
    )
    surfaces = spec.surfaces() if "B" in config.gates else []
    products = spec.products if "A" in config.gates else []
    jobs: list[_Job] = []
    for persona in panel.personas:
        for product in products:
            for completion_index in range(config.completions):
                jobs.append(
                    _Job(
                        persona=persona,
                        stimulus_id=product.id,
                        stimulus_title=product.title,
                        product_id=product.id,
                        surface_role=None,
                        completion_index=completion_index,
                    )
                )
        for role, surface in surfaces:
            for completion_index in range(config.completions):
                jobs.append(
                    _Job(
                        persona=persona,
                        stimulus_id=f"page:{role}",
                        stimulus_title=surface.hero_title,
                        product_id=None,
                        surface_role=role,
                        completion_index=completion_index,
                    )
                )

    client = LLMClient(
        model=config.model,
        mock=config.mock,
        max_tokens=config.max_tokens,
        timeout=config.timeout,
        max_retries=config.max_retries,
        cache_path=config.cache_path,
    )
    surface_by_role = dict(surfaces)
    product_by_id = {product.id: product for product in spec.products}

    done_jobs = 0
    job_lock = threading.Lock()

    def _run(job: _Job) -> tuple[_Job, LLMResult]:
        nonlocal done_jobs
        product = product_by_id.get(job.product_id) if job.product_id else None
        surface = surface_by_role.get(job.surface_role) if job.surface_role else None
        result = client.complete(
            persona=job.persona,
            spec=spec,
            product=product,
            surface=surface,
            surface_role=job.surface_role,
            completion_index=job.completion_index,
        )
        with job_lock:
            done_jobs += 1
            _progress(config, "simulating", f"Traveller reactions {done_jobs}/{len(jobs)}", done_jobs, len(jobs))
        return job, result

    workers = max(1, config.concurrency)
    _progress(config, "simulating", f"Traveller reactions 0/{len(jobs)}", 0, len(jobs))
    if jobs:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            completed = list(pool.map(_run, jobs))
    else:
        completed = []

    _progress(config, "scoring", "Mapping reactions onto the booking-intent scale")

    vocab = [statement for group in ANCHOR_SETS for statement in group]
    embedder = build_embedder(
        config.embedder,
        model_name=config.embedding_model,
        vocabulary_texts=vocab,
    )
    anchor_vectors = [embedder.embed(group) for group in ANCHOR_SETS]
    texts = [result.text for _, result in completed]
    response_vectors = embedder.embed(texts) if texts else np.zeros((0, 1))

    # Average pmfs across completions for the same persona and stimulus.
    bucket: dict[tuple[str, str], list[np.ndarray]] = defaultdict(list)
    text_by_key: dict[tuple[str, str], str] = {}
    generator = "mock-template" if config.mock else "anthropic"
    for (job, result), vector in zip(completed, response_vectors):
        pmf = ssr_pmf(
            vector,
            anchor_vectors,
            epsilon=config.epsilon,
            temperature=config.temperature,
        )
        key = (job.persona.id, job.stimulus_id)
        bucket[key].append(pmf)
        # Keep the first completion as the quote. Completions are exchangeable.
        text_by_key.setdefault(key, result.text)
        generator = result.generator

    averaged: dict[tuple[str, str], np.ndarray] = {
        key: np.mean(np.vstack(pmfs), axis=0) for key, pmfs in bucket.items()
    }
    persona_by_id = {persona.id: persona for persona in panel.personas}

    def records_for(stimulus_id: str) -> list[tuple[Persona, np.ndarray]]:
        rows = []
        for (persona_id, stim_id), pmf in averaged.items():
            if stim_id == stimulus_id:
                rows.append((persona_by_id[persona_id], pmf))
        return rows

    product_block: dict[str, dict] = {}
    product_means: dict[str, float] = {}
    if "A" in config.gates:
        for product in spec.products:
            rows = records_for(product.id)
            if not rows:
                continue
            overall = _summary([pmf for _, pmf in rows])
            product_means[product.id] = overall.mean
            product_block[product.id] = {
                "title": product.title,
                "type": product.type,
                "positioning": product.positioning,
                "price": product.price,
                "currency": product.currency,
                "overall": overall.model_dump(),
                "by_segment": {
                    axis: {key: value.model_dump() for key, value in groups.items()}
                    for axis, groups in _group_summaries(rows).items()
                },
            }

    page_block: dict[str, dict] = {}
    if "B" in config.gates:
        for role, surface in surfaces:
            rows = records_for(f"page:{role}")
            if not rows:
                continue
            overall = _summary([pmf for _, pmf in rows])
            page_block[role] = {
                "title": surface.hero_title,
                "page_type": surface.page_type,
                "url": surface.url,
                "overall": overall.model_dump(),
                "by_segment": {
                    axis: {key: value.model_dump() for key, value in groups.items()}
                    for axis, groups in _group_summaries(rows).items()
                },
            }

    rankings = _rankings(product_block)
    product_z = z_scores(product_means)
    for product_id, score in product_z.items():
        product_block[product_id]["z_vs_collection"] = round(score, 4)
    _progress(config, "checks", "Running price, duration, and content checks")
    issues = [issue.model_dump() for issue in run_deterministic_checks(spec)]
    if "A" in config.gates and product_means:
        titles = {product_id: block["title"] for product_id, block in product_block.items()}
        issues.extend(
            issue.model_dump() for issue in relative_ranking_issues(product_means, titles)
        )
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
            issue.model_dump() for issue in cannibalisation_from_intent(spec, product_means)
        )
        issues.extend(issue.model_dump() for issue in _segment_product_flags(product_block))
    if "B" in config.gates:
        page_means = {role: block["overall"]["mean"] for role, block in page_block.items()}
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
        for role, block in page_block.items():
            for axis, groups in block["by_segment"].items():
                means = {key: value["mean"] for key, value in groups.items()}
                issues.extend(
                    issue.model_dump()
                    for issue in intent_issues(
                        scope=f"page:{role} by {axis}",
                        gate="B",
                        means=means,
                        pass_at=SEGMENT_MEAN_PASS,
                        warn_at=SEGMENT_MEAN_WARN,
                        code="segment_page_intent",
                    )
                )

    quotes = _quotes(
        spec=spec,
        averaged=averaged,
        text_by_key=text_by_key,
        persona_by_id=persona_by_id,
        product_means=product_means,
        generator=generator,
    )
    calls = planned_calls(
        n_personas=config.n_personas,
        n_products=len(spec.products),
        n_surfaces=len(spec.surfaces()),
        gates=config.gates,
        completions=config.completions,
    )
    cost = estimate_cost(
        model=config.model,
        calls=calls,
        input_tokens=client.input_tokens,
        output_tokens=client.output_tokens,
        actual_usage=not config.mock and client.calls + client.cache_hits > 0,
    )
    if config.mock:
        # Token counts in mock mode are character estimates, not API usage.
        cost_payload = cost.__dict__.copy()
        cost_payload["actual_usage"] = False
        cost_payload["note"] = (
            "MOCK run. Token counts are length estimates of template prompts. "
            "USD applies the published rate to those estimates so you can see "
            "what a live run of this size would cost. No API call was made."
        )
    else:
        cost_payload = cost.__dict__.copy()
        cost_payload["note"] = "Live Anthropic usage." if client.calls else "Served entirely from cache."

    banner = None
    if config.mock:
        banner = (
            "MOCK OUTPUT. Reactions are deterministic templates, not Claude. "
            f"Embeddings are {embedder.name}, not a judgment of real travelers. "
            "Do not use these scores as market research or as a go-live decision."
        )

    panel_scores = _panel_scores(persona_by_id, averaged)
    page_ids = [f"page:{role}" for role, _surface in surfaces]
    product_ids = list(product_means)
    titles = {product_id: block["title"] for product_id, block in product_block.items()}
    sensitivity = None
    if panel_scores and (product_ids or page_ids):
        _progress(config, "sensitivity", "Reweighting the persona mix")
        sensitivity = analyze_panel(
            panel_scores,
            panel.weights,
            product_ids=product_ids,
            page_ids=page_ids,
            titles=titles,
            base_issues=issues,
            spec=spec,
            seed=config.seed,
        )
        sensitivity["collection_id"] = spec.id
        sensitivity["mock"] = config.mock

    return {
        "banner": banner,
        "mock": config.mock,
        "collection_id": spec.id,
        "collection_name": spec.name,
        "destination": spec.destination,
        "ce_id": spec.ce_id,
        "provenance": spec.provenance,
        "provenance_note": spec.provenance_note,
        "fetched_on": spec.fetched_on,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "seed": config.seed,
        "method": {
            "paper": "arXiv 2510.08338",
            "epsilon": config.epsilon,
            "temperature": config.temperature,
            "anchor_sets": len(ANCHOR_SETS),
            "embedder": embedder.name,
            "model": config.model,
            "completions": config.completions,
            "n_personas": config.n_personas,
            "seed": config.seed,
            "max_tokens": config.max_tokens,
            "request_timeout_s": config.timeout,
            "max_retries": config.max_retries,
            "concurrency": config.concurrency,
            "gates": sorted(config.gates),
            "llm_calls_made": client.calls,
            "cache_hits": client.cache_hits,
        },
        "persona_assumption": ASSUMPTION_NOTE,
        "persona_profile": panel.profile,
        "persona_weights": panel.weights,
        "cost": cost_payload,
        "issues": issues,
        "products": product_block,
        "pages": page_block,
        "rankings": rankings,
        "quotes": [quote.model_dump() for quote in quotes],
        "panel_scores": panel_scores,
        "sensitivity": sensitivity,
        "unknowns": spec.unknowns,
        "sources": [source.model_dump() for source in spec.sources],
        "thresholds": {
            "page_mean_pass": PAGE_MEAN_PASS,
            "page_mean_warn": PAGE_MEAN_WARN,
            "segment_mean_pass": SEGMENT_MEAN_PASS,
            "segment_mean_warn": SEGMENT_MEAN_WARN,
            "product_mean_pass": PRODUCT_MEAN_PASS,
            "product_mean_warn": PRODUCT_MEAN_WARN,
            "cannibal_pi_delta": CANNIBAL_PI_DELTA,
            "relative_z_warn": RELATIVE_Z_WARN,
            "relative_z_fail": RELATIVE_Z_FAIL,
            "compression_range": COMPRESSION_RANGE,
            "absolute_thresholds_calibrated": False,
            "note": (
                "Absolute cuts are not calibrated to Headout CVR. A live Sonnet 5.5 "
                "pilot (seed 7, 30 personas) compressed product means into about "
                "3.17–3.46, so these pass lines mostly warn. Use z_vs_collection "
                "and relative_rank until a backtest replaces the cuts. "
                "See anchors.CALIBRATION_PLAN."
            ),
        },
    }


def _panel_scores(persona_by_id: dict[str, Persona], averaged: dict[tuple[str, str], np.ndarray]) -> list[dict]:
    by_persona: dict[str, dict] = defaultdict(dict)
    for (persona_id, stimulus_id), pmf in averaged.items():
        by_persona[persona_id][stimulus_id] = {
            "mean": round(mean_rating(pmf), 6),
            "pmf": pmf_as_dict(pmf),
        }
    rows = []
    for persona_id in sorted(persona_by_id):
        persona = persona_by_id[persona_id]
        rows.append(
            {
                "persona_id": persona_id,
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
                "scores": by_persona.get(persona_id, {}),
            }
        )
    return rows


def _rankings(product_block: dict[str, dict]) -> dict:
    def order(items: list[tuple[str, float]]) -> list[str]:
        return [product_id for product_id, _ in sorted(items, key=lambda pair: (-pair[1], pair[0]))]

    overall = order((product_id, block["overall"]["mean"]) for product_id, block in product_block.items())
    by_axis: dict[str, dict[str, list[str]]] = {}
    for axis in SEGMENT_AXES:
        segments: dict[str, list[tuple[str, float]]] = defaultdict(list)
        for product_id, block in product_block.items():
            for segment, summary in block["by_segment"].get(axis, {}).items():
                segments[segment].append((product_id, summary["mean"]))
        by_axis[axis] = {segment: order(pairs) for segment, pairs in segments.items()}
    return {"overall": overall, "by_segment": by_axis}


def _segment_product_flags(product_block: dict[str, dict]) -> list:
    """Flag a segment only when its favorite product still scores poorly."""
    from collection_qa.checks import intent_issues as _intent

    flagged = []
    for axis in SEGMENT_AXES:
        best: dict[str, float] = {}
        for block in product_block.values():
            for segment, summary in block["by_segment"].get(axis, {}).items():
                best[segment] = max(best.get(segment, 0.0), summary["mean"])
        flagged.extend(
            _intent(
                scope=f"best product by {axis}",
                gate="A",
                means=best,
                pass_at=SEGMENT_MEAN_PASS,
                warn_at=SEGMENT_MEAN_WARN,
                code="segment_best_product",
            )
        )
    return flagged


def _quotes(
    *,
    spec: CollectionSpec,
    averaged: dict[tuple[str, str], np.ndarray],
    text_by_key: dict[tuple[str, str], str],
    persona_by_id: dict[str, Persona],
    product_means: dict[str, float],
    generator: str,
) -> list[Quote]:
    quotes: list[Quote] = []
    seen: set[tuple[str, str]] = set()

    def add(persona_id: str, stimulus_id: str, title: str) -> None:
        if (persona_id, stimulus_id) in seen:
            return
        pmf = averaged.get((persona_id, stimulus_id))
        text = text_by_key.get((persona_id, stimulus_id))
        if pmf is None or text is None:
            return
        seen.add((persona_id, stimulus_id))
        persona = persona_by_id[persona_id]
        quotes.append(
            Quote(
                persona_id=persona_id,
                persona_label=persona.label(),
                stimulus_id=stimulus_id,
                stimulus_title=title,
                text=text,
                mean_pi=mean_rating(pmf),
                generator=generator,
            )
        )

    page_scores = [
        (persona_id, stimulus_id, mean_rating(pmf))
        for (persona_id, stimulus_id), pmf in averaged.items()
        if stimulus_id.startswith("page:")
    ]
    page_scores.sort(key=lambda row: row[2])
    for persona_id, stimulus_id, _ in page_scores[:2] + page_scores[-2:]:
        role = stimulus_id.split(":", 1)[1]
        surface = dict(spec.surfaces()).get(role)
        add(persona_id, stimulus_id, surface.hero_title if surface else stimulus_id)

    if product_means:
        ordered = sorted(product_means, key=lambda product_id: (product_means[product_id], product_id))
        for product_id in (ordered[0], ordered[-1]):
            cells = [
                (persona_id, mean_rating(pmf))
                for (persona_id, stimulus_id), pmf in averaged.items()
                if stimulus_id == product_id
            ]
            if not cells:
                continue
            cells.sort(key=lambda row: row[1])
            # Bottom product: a low quote. Top product: a high quote.
            chosen = cells[0][0] if product_id == ordered[0] else cells[-1][0]
            product = spec.product_by_id(product_id)
            add(chosen, product_id, product.title if product else product_id)
    return quotes
