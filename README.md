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
collection-qa run specs/masai-mara.yaml specs/milford-sound.yaml --personas 30 --seed 7
```

Without a key, the live command exits. Mock mode still builds the scorecard, under `reports/mock/` unless you pass `--out`:

```bash
collection-qa run specs/masai-mara.yaml specs/milford-sound.yaml \
  --mock --personas 30 --seed 7
```

`--dry-run` is the same switch as `--mock`.

## Check a CE

```bash
pip install -e '.[embeddings,dev]'
# optional browser sign-in for drafts that are not on headout.com yet:
pip install 'collection-qa[eos]' && playwright install chromium
export ANTHROPIC_API_KEY=...    # omit it and the check falls back to mock reactions
export SLACK_TOKEN=...          # optional user token with search. Leave unset to skip Slack

collection-qa eos-login
collection-qa check "3945" --mock --personas 8 --no-prompt
collection-qa check "Milford Sound" --eos-export draft.json --mock --out reports/checks
```

`check` looks up the CE on the public collection API and product-card API. If those cards are bookable, status is **LIVE** and the existing panel runs on that page. Slack, when `SLACK_TOKEN` is set, searches for MMP threads (SRC, BOQA, BizQA, BOB, content lock, assortment, campaign ticket) and names the furthest stage it sees. No token is an empty stage, not an error.

If the page has no bookable cards, status is **IN_PIPELINE** when Slack or the collection record exists, otherwise **NOT_FOUND**. The command then asks for EOS links (`eos.headout.com`). Sign-in uses a headed Chromium profile at `~/.collection-qa/eos-profile` from `eos-login`. That folder is yours, it is gitignored, and the tool never asks for a shared password. `--eos-export` reads a saved HTML, JSON, or CSV instead of the browser.

Gate A runs when there is an assortment. Gate B is added when the page is live or the draft says content is locked. The report is `reports/checks/<id>.check.html` plus markdown and JSON: verdict (Go / Fix first / Hold), quotes, a product chart, a fix table (priority, issue, link, change, owner, quote), traveller-type breakdown, microbrand versus Headout, competitors, automated checks, whether the mix can be trusted, and an appendix.

EOS pages were read signed in, read-only. The map is `collection_qa.eos.EOS_STRUCTURE`. Sign-in is Google-only. Paste an `/mmp/draft/<uuid>/<page>` URL; the search box can create a draft, so the tool does not open it. Known MMP uuids: CE 3945 and CE 7324. Prices, cancellation, pickup, images, and an export button were not on those pages, so those stay in the screenshot, export, and manual placeholders. The public product-card API returned HTTP 403 when the pilot specs were seeded.

### If you are filling this in by hand

You do not need EOS, Slack, or a screenshot to get a first report.

```bash
collection-qa init "Milford Sound"
```

That creates `inputs/milford-sound/`. Open `inputs.yaml`. Each line says what to paste. Leave a line blank if you do not have it. The report's first box is **Inputs used / missing**, and a blank line shows as not provided.

- `eos_mmp_link`, `eos_assortment_link`, `eos_content_link` are the EOS pages from your browser bar.
- `eos_exports` is a file you saved (HTML, JSON, or CSV) under `exports/`.
- `screenshots` is a PNG or JPG of those pages under `screenshots/`. A reading from a picture is marked please verify.
- `assortment.csv` is the product list if you would rather type it: title, price, duration, what is included.
- `content.md` is the headline and the FAQs.

Then:

```bash
collection-qa check "Milford Sound" --mock --no-prompt
```

If the same fact is in more than one place, the tool keeps the signed-in EOS page, then a saved export, then a screenshot, then what you typed. A live headout.com card still wins, because that is the page a traveller books. The appendix names the source of each part.

`inputs/milford-sound/` is a filled example from the public collection on 2026-11-26. The EOS links in that file are blank.

`collection-qa ui` opens a local tool at http://127.0.0.1:8765. It is a four-step page. The results step is the report: likely-to-book bars, traveller quotes, a best-to-worst chart, the fix table, a traveller heatmap with thin cells faded, detail folds, a stability chart, and a collapsed appendix. Charts are inline SVG. Download HTML saves that page. Download PDF uses the browser print dialog. Pilot reports in the side list open the Masai Mara and Milford Sound live scorecards without a new run.

`reports/live-regen/` is the same live panel rebuilt from the cached Claude replies, with each persona's real scores. Product means match `reports/live/`. The 80-mix sensitivity and all 780 verbatim reactions are in that folder. The original `reports/live/` JSON files stay as first written. Pilot reports in the tool read the regenerated files.

Screenshot reading calls Claude only when you are not in `--mock` and `ANTHROPIC_API_KEY` is set. Tests use a stand-in and do not spend.

Useful flags:

| Flag | Default | Role |
| --- | --- | --- |
| `--model` | `claude-sonnet-5-5` (or `COLLECTION_QA_MODEL`) | Anthropic model id |
| `--embedder` | `sentence-transformers` live, `lexical` in mock | `sentence-transformers`, `lexical`, or `hash` |
| `--embedding-model` | `paraphrase-multilingual-MiniLM-L12-v2` | Local model. Multilingual, because a live run produced some German and French replies |
| `--personas` | 30 | Panel size |
| `--seed` | 7 | Persona sample. Written on the scorecard as `seed` and in the header |
| `--completions` | 1 | Paper averaged 2 draws per prompt. Raise this when you care more about stability than cost |
| `--concurrency` | 8 | Parallel LLM calls |
| `--timeout` | 90 | Seconds per Anthropic request. The SDK default is 10 minutes and hung a live run |
| `--max-retries` | 5 | SDK retries after a timeout or a 429/529 |
| `--max-tokens` | 640 | Reply cap. 320 truncated about 15% of the live pilot. The prompt also asks for at most 80 English words |
| `--cache` | `.collection_qa_cache/llm.sqlite` | Exact-prompt cache |
| `--epsilon` / `--temperature` | 0 / 1 | SSR map. `--temperature` is not sent to Claude. Sonnet 5.5 rejects that argument |
| `--gates` | `A,B` | Either gate on its own |
| `--out` | `reports/mock` or `reports/live` | Mock runs default to `reports/mock`. Live runs default to `reports/live` |

Claude Sonnet 5.5 does not accept a sampling temperature. The client does not send one. The paper's LLM temperature of 0.5 is recorded on the cache key only, so older cache rows stay distinct. SSR temperature (the pmf sharpening parameter) is still `--temperature` and still defaults to 1.

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

Each run writes `<out>/<collection-id>.json` and `.md`. The persona seed is a top-level field and a line in the header, so two scorecards can be matched to the same panel.

Product rows include a z-score against the mean of product means in that run. `relative_rank` warns at one standard deviation below the collection and fails at 1.5. `score_compression` warns when the product means span less than 0.40 points. Absolute pass lines (page 3.6, segment 3.4, product 3.3) stay in the file and are marked uncalibrated. The live pilot below is why: every product mean landed between 3.17 and 3.46, so those lines mostly warn and do not rank the page.

The files also contain:

- Purchase-intent distribution and mean, overall and by trip type and budget tier, for the page and for each product
- Top and bottom products in each segment
- Every check with pass, warn, or fail
- A few persona quotes
- Sources, unknowns, and the threshold values that were applied

## Live pilot versus mock

Both panels used 30 personas. The live run used seed **7**. The mock files under `reports/mock/` were regenerated with that same seed after the prompt and ranking changes, so the persona lists match. They are still templates plus a lexical embedder. The banner says MOCK. Do not read those means as demand.

`reports/live/` is the Claude run and is not regenerated here. It used `claude-sonnet-5-5`, English-only `all-MiniLM-L6-v2`, `max_tokens` 320, and seed 7. 780 calls cost about US$3.15 (Masai Mara about $1.88 including 230 cache hits from a resumed run, Milford Sound about $1.27). That tree did not send z-scores, and it still had the temperature argument removed only on the machine that ran it.

What agrees, because it does not depend on the model:

- Masai Mara: the microbrand's "Nakuru on every 4+ day safari" claim fails. The day trip is 17 hours on the card and 13–14 hours on the itinerary. Cancellation and pickup are missing on several cards. There is no numeric Headout price, so the ladder cannot be judged. The microbrand names Headout and does not say it is not the operator site. Fourteen products is a choice-overload warn. Conservancy night drives and a standalone balloon are gaps.
- Milford Sound: the optional-lunch cruise is NZ$143.20 on the card and NZ$155 on the product page. Te Anau is inside the pass band (NZ$207.20 vs NZ$205). No priced overnight card, despite the long-form and RealNZ's NZ$799 overnight. The lead cards do not name the operator. The FAQ covers cancellation, getting there, and access. The price ladder has a product in each band.

What the live model added, and what the mock does not:

- Means sit in a tight band, about 3.17 to 3.46 across both collections. Masai Mara's top product is the 4-day private fly-in (3.44) and the bottom is the private day trip (3.17). The 2-day and 3-day road safaris sit near that bottom. Milford's top is the boutique small boat (3.46) and the bottom is the Queenstown fly-cruise (3.21). Page means are 3.37 and 3.39 on Mara and 3.32 on Milford. Absolute pass lines of 3.6 and 3.4 mostly warn. The rank order is the usable part, and it is not the mock order: the template had ranked short Mara road safaris above fly-in luxury. On the live Milford panel, luxury travelers lift the ultra-premium cruise to a tie for first (3.43) and still rank the fly-cruise last (3.09).
- About 15% of replies (115 of 780) were cut off at 320 tokens. The default cap is now 640 and the prompt asks for at most 80 English words.
- 25 replies came back in German or French for non-English personas. One Mara quote in the live file is in French. The prompt now requires English, and the default embedder is multilingual MiniLM so a leftover reply can still be scored.
- Mock means spread more widely, because the template pastes an anchor sentence. That spread, and the mock rank order, are artifacts. Use the mock files for the scorecard shape and the deterministic rows. Use the live files for the Claude rank order. On the next run, read z-scores rather than the absolute cuts.

## Validation plan

Full text also lives in `collection_qa.anchors.CALIBRATION_PLAN`.

1. **Do not retune anchors on the collections you will gate.** Freeze the sentences, then score a holdout.
2. **Backtest on live collections** that already have conversion. Compare product rank by mean SSR intent with rank by CVR and with rank by revenue per session (Pearson on the means, Spearman on the ranks). The paper divides correlation by a human test-retest ceiling. Until a repeat survey exists, publish the raw correlations and do not claim a percent of human reliability.
3. **Distribution check only after human Likert data exists.** Kolmogorov-Smirnov similarity can look excellent while ranking is useless. Report both.
4. **Shadow mode on the next MMP.** Run Gate A after proposed assortment and Gate B after content lock. Do not block the EOS sprint. After launch, join the scorecard to CVR. Wait past the few days in which a new collection's ranking model is still settling.
5. **Do not gate on source-market or age slices** until they track the booking mix. The paper reproduced age and income better than gender or region. The weights in this package are priors.
6. **Re-embed the same frozen reactions** with a second local model before locking an embedder. Keep cosine and minimum-subtraction fixed so the only change is the model.

## Persona-mix sensitivity

The weights are priors. A segment mean does not use them. It is the average of the personas who landed in that cell, so changing the cell's share of the mix does not change the cell. The blended page number and the overall product ranking do use the mix. That is the part this test moves.

```bash
collection-qa sensitivity specs/masai-mara.yaml \
  --from-run reports/mock/masai-mara.json \
  --out reports/mock/sensitivity
```

The command does not call Claude. It reads `panel_scores` from a finished scorecard and reweights those purchase-intent means. One-at-a-time shifts move each trip type, budget tier, source market, and planning horizon by ±20 percentage points, rescaling the other levels on that axis. Then it draws Dirichlet mixes centered on the base prior (`--dirichlet`, `--concentration`, `--seed`). For each mix it recomputes blended page intent, the product ranking, and the weight-dependent gate severities.

The report gives Kendall tau and Spearman against the base ranking, top-3 and bottom-3 overlap, and the gate-flip rate. A finding is **ROBUST** when it holds in at least 90% of reliable scenarios, and **WEIGHT-SENSITIVE** otherwise. If the blended page number is weight-sensitive, the scorecard says to read the per-segment results instead. A cell with fewer than 8 scored personas is flagged, with how many more draws would bring its expected count to 15.

The mix becomes evidence in four steps, not from this test alone:

1. This sensitivity test shows which conclusions survive a different prior and which are an artifact of the assumed shares.
2. Replace the prior with the booking mix of a similar live collection (source market, party, budget) before treating a segment gap as a gate.
3. Check that prior against external demand signals: search and keyword clusters, competitor assortment, and the source-market mix already in the EOS deep-research doc.
4. After launch, correct the weights with the collection's own sessions. The shadow-mode plan in the calibration section is that correction. Until it exists, a WEIGHT-SENSITIVE blended number is not a go-live result. The segment table is.

`reports/live/` does not contain `panel_scores`, so the live sensitivity files record that gap instead of a fake reweight. Regenerating from the live cache is described there. A re-run with today's English prompt or the 640-token cap will miss the cache.

## Layout

```
src/collection_qa/    package and CLI
specs/                pilot collection specs
tests/                SSR, personas, checks, mock end-to-end
reports/mock/         template scorecards, seed 7, labeled MOCK
reports/live/         Claude Sonnet 5.5 scorecards from the pilot, seed 7
reports/live/sensitivity/  why the live files cannot be reweighted yet
```

## Limits

SSR does not fix a stale price or a wrong inclusion. The model only reacts to the spec you give it. Travel is also a thinner training domain than the oral-care concepts in the paper, so a high score on a new destination is a weaker signal than a high score on a park Headout already sells at volume. Synthetic travelers do not have a real budget, a real visa, or a real weather forecast. This layer is an early screen next to competitor research and content review, not a replacement for either.
