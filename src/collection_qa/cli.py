"""Command line for the collection QA layer."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from collection_qa.anchors import CALIBRATION_PLAN
from collection_qa.cost import DEFAULT_MODEL, estimate_cost, planned_calls
from collection_qa.embeddings import DEFAULT_ST_MODEL
from collection_qa.llm import DEFAULT_MAX_RETRIES, DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT_SECONDS
from collection_qa.models import load_spec
from collection_qa.pipeline import RunConfig, run_collection
from collection_qa.scorecard import write_scorecard


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="collection-qa",
        description="Pre-launch collection QA using Semantic Similarity Rating.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Score one or more collection specs")
    _add_common(run_parser)
    run_parser.add_argument("specs", nargs="+", help="Collection spec YAML files")
    run_parser.add_argument(
        "--out",
        default=None,
        help="Scorecard directory. Default is reports/mock with --mock and reports/live otherwise",
    )
    run_parser.add_argument("--mock", "--dry-run", action="store_true", dest="mock", help="Template reactions, no API key")
    run_parser.add_argument("--model", default=os.environ.get("COLLECTION_QA_MODEL", DEFAULT_MODEL))
    run_parser.add_argument(
        "--embedder",
        choices=("lexical", "hash", "sentence-transformers"),
        default=None,
        help="Default is lexical in mock mode and sentence-transformers otherwise",
    )
    run_parser.add_argument(
        "--embedding-model",
        default=os.environ.get("COLLECTION_QA_EMBEDDING_MODEL", DEFAULT_ST_MODEL),
    )
    run_parser.add_argument("--cache", default=".collection_qa_cache/llm.sqlite")
    run_parser.add_argument("--concurrency", type=int, default=8, help="Parallel LLM calls")
    run_parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Per-request timeout in seconds for the Anthropic client",
    )
    run_parser.add_argument(
        "--max-retries",
        type=int,
        default=DEFAULT_MAX_RETRIES,
        help="SDK retries for a failed Anthropic request",
    )
    run_parser.add_argument("--completions", type=int, default=1, help="Paper used 2; default 1 to limit cost")
    run_parser.add_argument("--epsilon", type=float, default=0.0)
    run_parser.add_argument("--temperature", type=float, default=1.0, help="SSR pmf temperature. Not sent to Claude")
    run_parser.add_argument(
        "--max-tokens",
        type=int,
        default=DEFAULT_MAX_TOKENS,
        help="Reply cap. 320 truncated about 15 percent of the live pilot",
    )
    run_parser.add_argument("--gates", default="A,B", help="Comma-separated: A, B")

    sensitivity_parser = sub.add_parser(
        "sensitivity",
        help="Reweight a finished scorecard. Does not call the LLM",
    )
    sensitivity_parser.add_argument("spec", help="Collection spec YAML, used to name products")
    sensitivity_parser.add_argument("--from-run", required=True, help="Scorecard JSON with panel_scores, or a cache is not enough")
    sensitivity_parser.add_argument("--out", required=True, help="Directory for the sensitivity JSON and Markdown")
    sensitivity_parser.add_argument("--shift", type=float, default=0.20, help="One-at-a-time probability shift, e.g. 0.20")
    sensitivity_parser.add_argument("--dirichlet", type=int, default=40, help="Random mixes drawn around the base")
    sensitivity_parser.add_argument("--concentration", type=float, default=50.0, help="Dirichlet concentration. Higher stays closer to the base mix")
    sensitivity_parser.add_argument("--seed", type=int, default=None, help="Defaults to the scorecard seed")
    sensitivity_parser.add_argument("--min-cell", type=int, default=8, help="Flag a mix level with fewer scored personas than this")
    sensitivity_parser.add_argument("--target-cell", type=int, default=15, help="Cell size the extra-sample suggestion aims for")

    estimate_parser = sub.add_parser("estimate", help="Print a cost estimate and exit")
    _add_common(estimate_parser)
    estimate_parser.add_argument("specs", nargs="+")
    estimate_parser.add_argument("--model", default=os.environ.get("COLLECTION_QA_MODEL", DEFAULT_MODEL))
    estimate_parser.add_argument("--completions", type=int, default=1)
    estimate_parser.add_argument("--gates", default="A,B")

    sub.add_parser("calibration", help="Print the CVR calibration plan")

    args = parser.parse_args(argv)
    if args.command == "calibration":
        print(CALIBRATION_PLAN)
        return 0
    if args.command == "estimate":
        return _estimate(args)
    if args.command == "sensitivity":
        return _sensitivity(args)
    return _run(args)


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--personas", type=int, default=30)
    parser.add_argument("--seed", type=int, default=7)


def _gates(raw: str) -> set[str]:
    gates = {part.strip().upper() for part in raw.split(",") if part.strip()}
    unknown = gates - {"A", "B"}
    if unknown or not gates:
        raise SystemExit(f"gates must be A, B, or A,B (got {raw!r})")
    return gates


def _sensitivity(args: argparse.Namespace) -> int:
    import json

    from collection_qa.sensitivity import analyze_scorecard, write_sensitivity

    scorecard = json.loads(Path(args.from_run).read_text(encoding="utf-8"))
    spec = load_spec(args.spec)
    if scorecard.get("collection_id") and scorecard["collection_id"] != spec.id:
        print(
            f"Scorecard collection {scorecard['collection_id']} does not match spec {spec.id}.",
            file=sys.stderr,
        )
        return 2
    result = analyze_scorecard(
        scorecard,
        spec,
        shift=args.shift,
        n_dirichlet=args.dirichlet,
        concentration=args.concentration,
        seed=args.seed,
        min_cell=args.min_cell,
        target_cell=args.target_cell,
    )
    json_path, md_path = write_sensitivity(result, args.out, spec.id)
    print(f"wrote {json_path}")
    print(f"wrote {md_path}")
    if result.get("status") != "ok":
        print(result.get("message", "panel_scores are missing"), file=sys.stderr)
        return 3
    print(
        f"  scenarios={result['n_scenarios']} gate_flip_rate={result['gate_flip_rate']} "
        f"page_weight_sensitive={result['page_weight_sensitive']}"
    )
    return 0


def _estimate(args: argparse.Namespace) -> int:
    gates = _gates(args.gates)
    total_calls = 0
    for path in args.specs:
        spec = load_spec(path)
        calls = planned_calls(
            n_personas=args.personas,
            n_products=len(spec.products),
            n_surfaces=len(spec.surfaces()),
            gates=gates,
            completions=args.completions,
        )
        total_calls += calls
        cost = estimate_cost(model=args.model, calls=calls)
        print(f"{spec.id}: {calls} calls")
        for line in cost.lines():
            print(f"  {line}")
    if len(args.specs) > 1:
        rolled = estimate_cost(model=args.model, calls=total_calls)
        print(f"Total calls: {total_calls}")
        print(f"Total estimated USD: ${rolled.usd:.4f}")
    return 0


def _run(args: argparse.Namespace) -> int:
    mock = bool(args.mock)
    if not mock and not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "ANTHROPIC_API_KEY is not set. Refusing to call Anthropic. "
            "Re-run with --mock (or --dry-run) to score the spec with template reactions.",
            file=sys.stderr,
        )
        return 2
    embedder = args.embedder
    if embedder is None:
        embedder = "lexical" if mock else "sentence-transformers"
    gates = _gates(args.gates)
    cache = args.cache
    Path(cache).parent.mkdir(parents=True, exist_ok=True)
    config = RunConfig(
        mock=mock,
        model=args.model,
        embedder=embedder,
        embedding_model=args.embedding_model,
        n_personas=args.personas,
        seed=args.seed,
        concurrency=args.concurrency,
        cache_path=cache,
        completions=args.completions,
        epsilon=args.epsilon,
        temperature=args.temperature,
        gates=gates,
        max_tokens=args.max_tokens,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )
    out = args.out or ("reports/mock" if mock else "reports/live")
    for path in args.specs:
        spec = load_spec(path)
        print(f"Scoring {spec.id} ({spec.name})")
        print(
            f"  personas={config.n_personas} seed={config.seed} gates={','.join(sorted(gates))} "
            f"mock={config.mock} embedder={config.embedder} model={config.model} "
            f"concurrency={config.concurrency} timeout={config.timeout}s retries={config.max_retries}"
        )
        planned = planned_calls(
            n_personas=config.n_personas,
            n_products=len(spec.products),
            n_surfaces=len(spec.surfaces()),
            gates=gates,
            completions=config.completions,
        )
        preview = estimate_cost(model=config.model, calls=planned)
        print("  Pre-run cost estimate:")
        for line in preview.lines():
            print(f"    {line}")
        payload = run_collection(spec, config)
        json_path, md_path = write_scorecard(payload, out)
        print("  After run:")
        for line in _cost_lines(payload):
            print(f"    {line}")
        fails = sum(1 for issue in payload["issues"] if issue["severity"] == "fail")
        warns = sum(1 for issue in payload["issues"] if issue["severity"] == "warn")
        print(f"  issues: {fails} fail, {warns} warn")
        print(f"  wrote {json_path}")
        print(f"  wrote {md_path}")
        if payload.get("banner"):
            print(f"  {payload['banner']}")
    return 0


def _cost_lines(payload: dict) -> list[str]:
    cost = payload["cost"]
    return [
        f"calls: {cost['calls']}",
        f"input tokens: {cost['input_tokens']}",
        f"output tokens: {cost['output_tokens']}",
        f"USD: ${cost['usd']:.4f}",
        cost.get("note") or "",
    ]


if __name__ == "__main__":
    raise SystemExit(main())
