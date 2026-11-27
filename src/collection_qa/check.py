"""CE lookup to a pre-launch QA report.

Live pages are scored when Headout returns product cards. Otherwise the draft
comes from an EOS export or from the user's own signed-in browser. Gate A is
the assortment. Gate B is added when content is locked or the page is live.
"""

from __future__ import annotations

from pathlib import Path

from collection_qa.eos import (
    UNCONFIRMED_SELECTORS,
    EosDocument,
    EosParser,
    HeuristicEosAdapter,
    fetch_eos_page,
    read_eos_export,
)
from collection_qa.inputs import (
    SOURCE_RANK,
    ClaudeVision,
    InputManifest,
    SidecarVision,
    VisionExtractor,
    collect_layers,
    find_manifest,
    ledger_rows,
    load_manifest,
    merge_layers,
)
from collection_qa.headout_lookup import HeadoutLookup, ResolvedCE, ResolvedProduct
from collection_qa.models import FAQ, CollectionSpec, Product, Source, Surface
from collection_qa.personas import ASSUMPTION_NOTE
from collection_qa.pipeline import RunConfig, run_collection
from collection_qa.report import build_fixes, trust_bullets, verdict_for
from collection_qa.slack_status import SlackClient, combine_status, summarize_slack

METHOD = (
    "Travellers are sampled from a named prior and write a free-text booking reaction. "
    "Semantic Similarity Rating maps that text onto six sets of 1–5 anchors "
    "(arXiv 2510.08338). The model is not asked for a number. "
    "Deterministic checks cover price, duration, pickup, and cancellation. "
    + ASSUMPTION_NOTE
)


def guess_profile(name: str) -> str:
    text = name.lower()
    if any(word in text for word in ("safari", "mara", "serengeti", "nakuru")):
        return "safari"
    if any(word in text for word in ("cruise", "milford", "fjord", "sound")):
        return "fjord_cruise"
    return "generic"


def gates_for(*, status: str, content_locked: bool, has_content: bool) -> set[str]:
    if status == "LIVE" or content_locked or has_content:
        return {"A", "B"}
    return {"A"}


def spec_from_resolved(resolved: ResolvedCE, *, fetched_on: str) -> CollectionSpec:
    products = [_product_from_public(item, resolved.collection_url) for item in resolved.products]
    return _spec(
        ce_id=resolved.ce_id,
        name=resolved.name,
        destination=resolved.destination or resolved.name,
        url=resolved.collection_url,
        hero_title=resolved.hero_title or resolved.name,
        hero_copy=resolved.hero_copy or "",
        products=products,
        microbrand_url=resolved.microbrand_url,
        fetched_on=fetched_on,
        provenance_note="Built from the public Headout collection response.",
        unknowns=list(resolved.notes),
        sources=[
            Source(
                url=resolved.collection_url or "https://www.headout.com/",
                fetched_on=fetched_on,
                what="Public collection lookup",
            )
        ],
    )


def spec_from_eos(resolved: ResolvedCE, document: EosDocument, *, fetched_on: str) -> CollectionSpec:
    products = []
    for item in document.products:
        products.append(
            Product(
                id=item.id,
                title=item.title,
                type="experience",
                price=item.price,
                currency=item.currency,
                duration=item.duration,
                features=item.highlights,
                inclusions=item.inclusions,
                pickup=item.pickup,
                pickup_status="included" if item.pickup else "unknown",
                cancellation=item.cancellation,
                url=item.url or document.source,
                source_urls=[document.source],
                notes=["Parsed from an EOS export. Selectors are unconfirmed."],
            )
        )
    faqs = [FAQ(question=question, answer=answer) for question, answer in document.faqs]
    hero = document.hero_title or resolved.name
    copy = document.hero_copy or ""
    return _spec(
        ce_id=resolved.ce_id,
        name=resolved.name,
        destination=resolved.destination or resolved.name,
        url=resolved.collection_url,
        hero_title=hero,
        hero_copy=copy,
        products=products,
        microbrand_url=resolved.microbrand_url,
        fetched_on=fetched_on,
        provenance_note="Built from an EOS assortment or content export, not from a live collection page.",
        unknowns=list(resolved.notes) + list(document.notes),
        sources=[Source(url=document.source, fetched_on=fetched_on, what="EOS export or saved page")],
        faqs=faqs,
        faq_capture="present" if faqs else "unknown",
    )


def _spec(**kwargs) -> CollectionSpec:
    faqs = kwargs.pop("faqs", [])
    faq_capture = kwargs.pop("faq_capture", "unknown")
    microbrand_url = kwargs.pop("microbrand_url")
    micro = None
    if microbrand_url:
        micro = Surface(
            page_type="microbrand",
            url=microbrand_url,
            hero_title=kwargs["hero_title"],
            hero_copy=kwargs["hero_copy"],
            faq_capture="unknown",
            discloses_headout=None,
            not_official_venue_disclaimer=None,
            notes=["Microbrand URL came from the lookup. Page copy was not fetched."],
        )
    return CollectionSpec(
        id=_slug(kwargs["name"], kwargs["ce_id"]),
        name=kwargs["name"],
        destination=kwargs["destination"],
        ce_id=kwargs["ce_id"],
        provenance="live_headout",
        provenance_note=kwargs["provenance_note"],
        fetched_on=kwargs["fetched_on"],
        audience_profile=guess_profile(kwargs["name"]),
        primary_surface=Surface(
            page_type="headout.com",
            url=kwargs["url"],
            hero_title=kwargs["hero_title"],
            hero_copy=kwargs["hero_copy"],
            faqs=faqs,
            faq_capture=faq_capture,
            discloses_headout=True,
        ),
        microbrand=micro,
        products=kwargs["products"],
        sources=kwargs["sources"],
        unknowns=kwargs["unknowns"],
    )


def _product_from_public(item: ResolvedProduct, page_url: str | None) -> Product:
    return Product(
        id=item.id,
        title=item.title,
        type="experience",
        price=item.price,
        currency=item.currency,
        duration=item.duration,
        rating=item.rating,
        review_count=item.review_count,
        inclusions=item.inclusions,
        cancellation=item.cancellation,
        pickup=item.pickup,
        pickup_status="included" if item.pickup else "unknown",
        url=item.url or page_url,
        source_urls=[url for url in (item.url, page_url) if url],
    )


def _slug(name: str, ce_id: str | None) -> str:
    base = "".join(char.lower() if char.isalnum() else "-" for char in name).strip("-")
    while "--" in base:
        base = base.replace("--", "-")
    return f"{base}-{ce_id}" if ce_id else (base or "ce")


def run_check(
    query: str,
    *,
    fetch,
    slack: SlackClient,
    out: str | Path,
    mock: bool = True,
    personas: int = 30,
    seed: int = 7,
    eos_export: str | None = None,
    eos_urls: list[str] | None = None,
    eos_parser: EosParser | None = None,
    eos_fetcher=None,
    eos_profile: str | None = None,
    prompt_fn=None,
    fetched_on: str = "2026-11-26",
    inputs_path: str | None = None,
    vision: VisionExtractor | None = None,
    progress=None,
) -> dict:
    def _note(stage: str, detail: str, current: int | None = None, total: int | None = None) -> None:
        if progress:
            progress(stage, detail, current, total)

    _note("resolving", f"Looking up {query}")
    lookup = HeadoutLookup(fetch)
    resolved = lookup.resolve(query)
    slack_summary = summarize_slack(slack, ce_id=resolved.ce_id, name=resolved.name)
    status, stage = combine_status(
        page_live=resolved.page_live,
        collection_found=bool(resolved.ce_id),
        slack=slack_summary,
    )
    parser = eos_parser or HeuristicEosAdapter()
    eos_doc = _load_eos(
        status=status,
        eos_export=eos_export,
        eos_urls=eos_urls or [],
        parser=parser,
        eos_fetcher=eos_fetcher,
        eos_profile=eos_profile,
        prompt_fn=prompt_fn,
    )
    _note("reading", "Reading the input folder, exports, and screenshots")
    manifest_path = find_manifest(query, inputs_path)
    manifest = load_manifest(manifest_path) if manifest_path and manifest_path.exists() else None
    if manifest and manifest.microbrand_url and not resolved.microbrand_url:
        resolved.microbrand_url = manifest.microbrand_url
    layers = collect_layers(manifest, parser=parser, vision=vision or (SidecarVision() if mock else ClaudeVision()), eos_live=None) if manifest else []
    if eos_export:
        layers.append(("eos_export", read_eos_export(eos_export, parser)))
    elif eos_doc is not None:
        layers.append(("eos_live", eos_doc))
    layers = sorted(layers, key=lambda item: SOURCE_RANK[item[0]])
    merged, field_sources, verify = merge_layers(layers)
    if resolved.page_live:
        field_sources["products"] = "headout"
        if resolved.hero_title:
            field_sources["hero_title"] = "headout"
        if resolved.hero_copy:
            field_sources["hero_copy"] = "headout"
    content_locked = bool(
        (eos_doc and (eos_doc.content_locked or _stage_is_locked(eos_doc.stage)))
        or (merged and (merged.content_locked or _stage_is_locked(merged.stage)))
    )
    has_content = bool(
        (merged and (merged.hero_copy or merged.faqs))
        or (eos_doc and (eos_doc.hero_copy or eos_doc.faqs))
        or content_locked
        or resolved.hero_copy
    )
    draft = merged if merged and merged.products else eos_doc
    if status == "LIVE":
        spec = spec_from_resolved(resolved, fetched_on=fetched_on)
        if manifest and manifest.microbrand_url:
            spec.microbrand = spec.microbrand or _micro_surface(manifest.microbrand_url, spec.primary_surface.hero_title, spec.primary_surface.hero_copy)
    elif draft and draft.products:
        spec = spec_from_eos(resolved, draft, fetched_on=fetched_on)
        if not resolved.page_live:
            status = "IN_PIPELINE"
            stage = stage or (draft.stage if draft else None) or "manual_inputs"
        for product in spec.products:
            if any(product.title.lower() in item.lower() for item in verify):
                product.notes.append("please verify — this row was read from a screenshot")
    else:
        spec = None
    input_rows = ledger_rows(manifest, field_sources if layers or resolved.page_live else {})
    gates = gates_for(status=status, content_locked=content_locked, has_content=has_content) if spec else set()
    scorecard = None
    if spec and spec.products and gates:
        scorecard = run_collection(
            spec,
            RunConfig(
                mock=mock,
                n_personas=personas,
                seed=seed,
                embedder="lexical" if mock else "sentence-transformers",
                gates=gates,
                progress=progress,
            ),
        )
    issues = (scorecard or {}).get("issues") or []
    quotes = (scorecard or {}).get("quotes") or []
    products = _product_rows(scorecard)
    verdict, reason = verdict_for(status=status, issues=issues, has_products=bool(products))
    page_url = resolved.collection_url
    micro_note = _micro_note(resolved, scorecard)
    report = {
        "verdict": verdict,
        "verdict_reason": reason,
        "mock": mock,
        "status": status,
        "stage": stage,
        "gates": sorted(gates),
        "ce": {
            "ce_id": resolved.ce_id,
            "name": resolved.name,
            "collection_url": resolved.collection_url,
            "microbrand_url": resolved.microbrand_url,
            "destination": resolved.destination,
        },
        "quotes": quotes,
        "products": products,
        "fixes": build_fixes(issues, quotes, page_url),
        "by_traveller": _by_traveller(scorecard),
        "microbrand_vs_headout": micro_note,
        "checks": [
            {"severity": issue["severity"], "code": issue["code"], "message": issue["message"]}
            for issue in issues
        ],
        "trust": trust_bullets(scorecard, mock=mock),
        "inputs": input_rows,
        "competitors": list(manifest.competitor_urls) if manifest else [],
        "appendix": {
            "pages": [url for url in (resolved.collection_url, resolved.microbrand_url) if url]
            + ([eos_doc.source] if eos_doc else []),
            "method": METHOD,
            "slack": slack_summary.summary,
            "eos_notes": (list(merged.notes) if merged else []) + (list(eos_doc.notes) if eos_doc else (
                ["No EOS page was parsed."] if status != "LIVE" else []
            )),
            "field_sources": field_sources,
            "unconfirmed_selectors": UNCONFIRMED_SELECTORS if eos_doc else "",
        },
    }
    from collection_qa.executive import build_view

    report["view"] = build_view(scorecard, report=report) if scorecard else build_view(report)
    return report


def _stage_is_locked(stage: str | None) -> bool:
    if not stage:
        return False
    text = stage.lower().replace("_", " ")
    return "content" in text and "lock" in text


def _load_eos(
    *,
    status: str,
    eos_export: str | None,
    eos_urls: list[str],
    parser: EosParser,
    eos_fetcher,
    eos_profile: str | None,
    prompt_fn,
) -> EosDocument | None:
    if status == "LIVE" and not eos_export and not eos_urls:
        return None
    if eos_export:
        return read_eos_export(eos_export, parser)
    urls = list(eos_urls)
    if not urls and prompt_fn and status != "LIVE":
        print("This CE is not a live collection page. Paste EOS links, then a blank line.")
        while True:
            line = prompt_fn("EOS link: ").strip()
            if not line:
                break
            urls.append(line)
    if not urls:
        return None
    fetcher = eos_fetcher or fetch_eos_page
    chunks = []
    for url in urls:
        chunks.append(fetcher(url, Path(eos_profile) if eos_profile else None))
    return parser.parse("\n".join(chunks), source=urls[0])


def _product_rows(scorecard: dict | None) -> list[dict]:
    if not scorecard:
        return []
    rows = []
    for product_id in scorecard.get("rankings", {}).get("overall") or []:
        block = scorecard["products"][product_id]
        rows.append({"id": product_id, "title": block["title"], "mean": block["overall"]["mean"]})
    return rows


def _by_traveller(scorecard: dict | None) -> dict:
    if not scorecard:
        return {}
    pages = scorecard.get("pages") or {}
    products = scorecard.get("products") or {}
    rankings = (scorecard.get("rankings") or {}).get("by_segment", {}).get("trip_type", {})
    found = {}
    page = next(iter(pages.values()), None)
    segments = (page or {}).get("by_segment", {}).get("trip_type", {})
    names = set(segments) | set(rankings)
    for name in sorted(names):
        top_id = (rankings.get(name) or [None])[0]
        top = products.get(top_id, {}).get("title") if top_id else None
        page_mean = segments.get(name, {}).get("mean")
        found[name] = {"page_mean": page_mean, "top_product": top}
    return found


def _micro_surface(url: str, title: str, copy: str) -> Surface:
    return Surface(
        page_type="microbrand",
        url=url,
        hero_title=title,
        hero_copy=copy,
        faq_capture="unknown",
        notes=["Microbrand URL came from inputs.yaml. The page itself was not fetched."],
    )


def _micro_note(resolved: ResolvedCE, scorecard: dict | None) -> str:
    if not resolved.microbrand_url:
        return "No microbrand URL was on the public collection payload."
    pages = (scorecard or {}).get("pages") or {}
    bits = [f"Microbrand URL: {resolved.microbrand_url}."]
    if "primary" in pages:
        bits.append(f"Headout page mean {pages['primary']['overall']['mean']:.2f}.")
    if "microbrand" in pages:
        bits.append(f"Microbrand page mean {pages['microbrand']['overall']['mean']:.2f}.")
    else:
        bits.append("The microbrand page itself was not fetched, so it was not scored as its own surface.")
    return " ".join(bits)

