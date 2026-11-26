"""Command line for collection QA."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from collection_qa import __version__
from collection_qa.anchors import ANCHOR_SETS
from collection_qa.checks import run_checks
from collection_qa.models import load_spec
from collection_qa.personas import default_weights
from collection_qa.runner import run_collection


def _cmd_run(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    dry_run = args.dry_run or args.mock
    if not dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is not set. Re-run with --dry-run to use the mock generator.", file=sys.stderr)
        return 2
    out = Path(args.out) if args.out else Path("reports/mock" if dry_run else "reports/live")
    run_collection(
        spec,
        n_personas=args.personas,
        seed=args.seed,
        dry_run=dry_run,
        gate=args.gate,
        model=args.model,
        embedder_kind=args.embedder,
        embedding_model=args.embedding_model,
        workers=args.workers,
        completions=args.completions,
        epsilon=args.epsilon,
        ssr_temperature=args.temperature,
        llm_temperature=args.llm_temperature,
        max_products=args.max_products,
        ablate_personas=args.ablate_personas,
        cache_dir=Path(args.cache_dir),
        out_dir=out,
    )
    return 0


def _cmd_check(args: argparse.Namespace) -> int:
    spec = load_spec(args.spec)
    results = run_checks(spec)
    worst = "pass"
    rank = {"pass": 0, "info": 1, "warn": 2, "fail": 3}
    for item in results:
        print(f"[{item.severity}] {item.id}: {item.message}")
        if rank[item.severity] > rank[worst]:
            worst = item.severity
    print(f"Worst deterministic severity: {worst}")
    return 1 if worst == "fail" else 0


def _cmd_anchors(_args: argparse.Namespace) -> int:
    for set_id, statements in ANCHOR_SETS.items():
        print(set_id)
        for index, statement in enumerate(statements, start=1):
            print(f"  {index}. {statement}")
    return 0


def _cmd_personas(args: argparse.Namespace) -> int:
    weights, basis = default_weights(args.collection)
    print(basis)
    for name, table in weights.items():
        rendered = ", ".join(f"{label}={value:.2f}" for label, value in table.items())
        print(f"{name}: {rendered}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="collection-qa", description="Pre-launch collection QA with semantic similarity ratings.")
    parser.add_argument("--version", action="version", version=f"collection-qa {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Score a collection spec")
    run.add_argument("spec")
    run.add_argument("--personas", type=int, default=30)
    run.add_argument("--seed", type=int, default=20261126)
    run.add_argument("--dry-run", action="store_true", help="Use the rule-based mock instead of Claude")
    run.add_argument("--mock", action="store_true", help="Alias of --dry-run")
    run.add_argument("--gate", choices=["A", "B", "both"], default="both")
    run.add_argument("--out", default=None, help="Directory for the JSON and Markdown scorecards")
    run.add_argument("--model", default=os.environ.get("COLLECTION_QA_MODEL", "claude-sonnet-5-5"))
    run.add_argument(
        "--embedding-model",
        default=os.environ.get("COLLECTION_QA_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"),
    )
    run.add_argument("--embedder", choices=["sentence-transformers", "hash"], default="sentence-transformers")
    run.add_argument("--workers", type=int, default=8)
    run.add_argument("--completions", type=int, default=1, help="Completions per prompt. The paper used 2.")
    run.add_argument("--epsilon", type=float, default=0.0, help="SSR epsilon. The paper's main runs use 0.")
    run.add_argument("--temperature", type=float, default=1.0, help="SSR pmf temperature T. The paper's main runs use 1.")
    run.add_argument("--llm-temperature", type=float, default=0.5)
    run.add_argument("--max-products", type=int, default=0, help="If set, score only the first N products")
    run.add_argument("--ablate-personas", action="store_true", help="Drop demographic detail, as in the paper's ablation")
    run.add_argument("--cache-dir", default=".cache/collection-qa")
    run.set_defaults(func=_cmd_run)

    check = sub.add_parser("check", help="Run deterministic checks only")
    check.add_argument("spec")
    check.set_defaults(func=_cmd_check)

    anchors = sub.add_parser("anchors", help="Print the travel Likert anchor sets")
    anchors.set_defaults(func=_cmd_anchors)

    personas = sub.add_parser("personas", help="Print default persona weights for a collection id")
    personas.add_argument("collection")
    personas.set_defaults(func=_cmd_personas)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
