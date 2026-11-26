# Collection QA layer

Pre-launch market research for a Headout collection. A collection is the landing page for a Combined Entity (CE). In ExperienceOS (EOS) that launch is an MMP (Managed Marketplace): research, assortment, content lock, then BizOps.

This package runs **before** the page is treated as ready. It builds a synthetic panel of travelers, asks each one for a free-text booking reaction, and turns that text into a 1–5 purchase-intent distribution with **Semantic Similarity Rating** (SSR), the method in [arXiv 2510.08338](https://arxiv.org/pdf/2510.08338).

Direct numeric ratings are not used. The paper shows that asking a model for a Likert number piles responses on 3 and almost never uses 1 or 5. SSR keeps the prose, embeds it, and compares it with several sets of anchor sentences.

Personas are not optional. The same paper's no-demographics ablation still produced a human-looking distribution (KS similarity 0.91, mean about 4.0) while ranking correlation fell to about 50%. Without a traveler, the model likes everything and the assortment order is noise.

## What it scores

Two gates, placed on the EOS path described in the internal go-live notes:

| Gate | When in the MMP | What it asks |
| --- | --- | --- |
| **A. Post-assortment** | After proposed assortment, before content lock and before Assortment Review is sent to BOB | Per-product intent by segment, price-ladder coverage, gaps versus competitors, cannibalisation, choice overload |
| **B. Post-content-lock** | After content is locked on EOS, before execution, so QA does not become a new MMP | Page-level intent, trust and official-versus-reseller confusion on microbrands, FAQ and clarity gaps |

Deterministic checks run with both gates. They do not call a model:

- The same product's "from" price disagrees across page sections
- Duration disagrees across sections (card versus itinerary)
- Pickup, duration, or cancellation is missing
- Mixed currencies
- A microbrand never says it is not the operator's site

Pass, warn, and fail cuts live in `collection_qa.checks`. They are **assumptions**. They are not fitted to Headout conversion. Do not block an MMP on them until the calibration plan below has been run.

## Method

1. Load a collection spec (YAML or JSON via the same loader: YAML is what the CLI opens).
2. Sample personas from a named prior (`safari` or `fjord_cruise`) or from weights on the spec. Every default weight is labeled an assumption. Axes are independent, which real booking data is not.
3. For Gate A, each persona writes a short reaction to each product. For Gate B, each persona writes a reaction to each surface (headout.com and, when present, the microbrand).
4. Embed the reaction and six sets of five travel-specific anchor sentences. Default embedder for a live run is a local `sentence-transformers` model. No second API key.
5. Cosine similarity, subtract the minimum similarity in the set, optional epsilon on the least-similar anchor, optional temperature. Average the six distributions. This is equations 8–9 in the paper, with epsilon 0 and temperature 1, which is what the paper's main experiments used.
6. Report the mean of that distribution as purchase intent. Also keep the full 1–5 distribution. Means alone hide a pile-up on a single score.

The anchor sentences are in `collection_qa.anchors`. They were written for booking a trip. They are **not** the personal-care anchors from the paper. Those were tuned on 57 surveys and do not transfer.

Persona fields: source market, age band, trip type (solo, couple, family with kids, friends), budget tier, planning horizon, first-timer versus repeat, accessibility, interests, device or channel.

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[embeddings,dev]'
cp .env.example .env
# put ANTHROPIC_API_KEY in .env, then:
set -a && source .env && set +a

collection-qa estimate specs/masai-mara.yaml specs/milford-sound.yaml --personas 30
collection-qa run specs/masai-mara.yaml specs/milford-sound.yaml \
  --personas 30 --out reports
```

Without a key, the live command exits. Mock mode still builds the scorecard:

```bash
collection-qa run specs/masai-mara.yaml specs/milford-sound.yaml \
  --mock --personas 30 --out reports
```

`--dry-run` is the same switch as `--mock`.

Useful flags:

| Flag | Default | Role |
| --- | --- | --- |
| `--model` | `claude-sonnet-5-5` (or `COLLECTION_QA_MODEL`) | Anthropic model id |
| `--embedder` | `sentence-transformers` live, `lexical` in mock | `sentence-transformers`, `lexical`, or `hash` |
| `--embedding-model` | `sentence-transformers/all-MiniLM-L6-v2` | Local model name |
| `--personas` | 30 | Panel size |
| `--completions` | 1 | Paper averaged 2 draws per prompt. Raise this when you care more about stability than cost |
| `--concurrency` | 8 | Parallel LLM calls |
| `--cache` | `.collection_qa_cache/llm.sqlite` | Exact-prompt cache |
| `--epsilon` / `--temperature` | 0 / 1 | SSR map, not the LLM temperature |
| `--gates` | `A,B` | Either gate on its own |
| `--seed` | 7 | Persona sample |

The LLM temperature is 0.5, matching the paper's main setting. It is not a CLI flag.

A run prints a cost estimate before any calls, then the token totals after. Prices are the public Claude rates recorded on 2026-11-26 (Sonnet 5.5 is $2 / million input tokens and $10 / million output tokens). Unknown model ids are billed at the Sonnet 5.5 rate and the printout says so.

`collection-qa calibration` prints the validation plan.

### Tests

```bash
pip install -e '.[dev]'
pytest
```

SSR math, persona sampling, deterministic checks, and an end-to-end mock run do not need a key and do not download an embedding model. The mock embedder is a bag-of-words over the anchor vocabulary. It is good enough to prove the pipeline. It is not a semantic model. Live scorecards should use `--embedder sentence-transformers`.

## Specs

`specs/masai-mara.yaml` and `specs/milford-sound.yaml` are seeded only from public pages fetched on **2026-11-26**. Each fact has a source URL. Unknowns are listed on the spec and copied onto the scorecard. The product-card API (`api-ho.headout.com`) returned HTTP 403 from the machine that built these files, so prices that were not visible in the HTML capture are null. They were not filled in from competitors.

Both collections exist on headout.com. Masai Mara also has a Headout microbrand at `masai-mara-safaris.com`. No Milford Sound microbrand was found. Vatican and Colosseum notes elsewhere in the research folder are only a structural reference. They are not pilot inputs.

A third file, `tests/fixtures/tiny.yaml`, is synthetic and is not a collection.

## Output

Each run writes `reports/<collection-id>.json` and `.md`:

- Purchase-intent distribution and mean, overall and by trip type and budget tier, for the page and for each product
- Top and bottom products in each segment
- Every check with pass, warn, or fail
- A few persona quotes
- Sources, unknowns, and the threshold values that were applied

The committed files under `reports/` are **MOCK**. `ANTHROPIC_API_KEY` was not available. Reactions are templates. Embeddings are lexical. The banner in each file says that. Use them to see the shape of a scorecard, and use the deterministic rows as findings about the captured pages. Do not treat the mock purchase-intent numbers as demand.

## Validation plan

Full text also lives in `collection_qa.anchors.CALIBRATION_PLAN`.

1. **Do not retune anchors on the collections you will gate.** Freeze the sentences, then score a holdout.
2. **Backtest on live collections** that already have conversion. Compare product rank by mean SSR intent with rank by CVR and with rank by revenue per session (Pearson on the means, Spearman on the ranks). The paper divides correlation by a human test-retest ceiling. Until a repeat survey exists, publish the raw correlations and do not claim a percent of human reliability.
3. **Distribution check only after human Likert data exists.** Kolmogorov-Smirnov similarity can look excellent while ranking is useless. Report both.
4. **Shadow mode on the next MMP.** Run Gate A after proposed assortment and Gate B after content lock. Do not block the EOS sprint. After launch, join the scorecard to CVR. Wait past the few days in which a new collection's ranking model is still settling.
5. **Do not gate on source-market or age slices** until they track the booking mix. The paper reproduced age and income better than gender or region. The weights in this package are priors.
6. **Re-embed the same frozen reactions** with a second local model before locking an embedder. Keep cosine and minimum-subtraction fixed so the only change is the model.

## Layout

```
src/collection_qa/    package and CLI
specs/                pilot collection specs
tests/                SSR, personas, checks, mock end-to-end
reports/              generated scorecards
```

## Limits

SSR does not fix a stale price or a wrong inclusion. The model only reacts to the spec you give it. Travel is also a thinner training domain than the oral-care concepts in the paper, so a high score on a new destination is a weaker signal than a high score on a park Headout already sells at volume. Synthetic travelers do not have a real budget, a real visa, or a real weather forecast. This layer is an early screen next to competitor research and content review, not a replacement for either.
