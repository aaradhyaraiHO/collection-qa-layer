# Collection QA layer

Pre-launch QA for a Headout collection: a landing page of experiences, internally a Combined Entity (CE) launched through a Managed Marketplace project (MMP) in ExperienceOS (EOS).

The layer samples traveler personas, asks each one for a free-text booking reaction, and turns that text into a 5-point purchase-intent distribution with Semantic Similarity Rating (SSR). It also runs deterministic checks on the spec itself (prices, pickup, duration, cancellation, inclusion claims, microbrand disclosure).

This is an early screen. It is not a go-live approval, and it does not replace supply readiness, BizOps QA, or business QA.

## Method

The method follows [arXiv 2510.08338](https://arxiv.org/pdf/2510.08338), *LLMs Reproduce Human Purchase Intent via Semantic Similarity Elicitation of Likert Ratings* (Maier et al., PyMC Labs / Colgate-Palmolive).

Asking a model for a number from 1 to 5 produces a pile of 3s. SSR keeps the words:

1. A persona writes a short free-text reaction to one stimulus. The prompt forbids a numeric score.
2. The reaction and several anchor statements are embedded.
3. Cosine similarity to each anchor in a set of five statements becomes a distribution over ratings 1–5.
4. The minimum similarity in that set is subtracted first. Without that step the distribution is almost flat, because even opposite sentences sit near each other in embedding space. With ε = 0, the least-similar anchor gets zero mass. A temperature T can sharpen the distribution. The paper's main runs use **ε = 0** and **T = 1**, and this tool does too unless you change the flags.
5. The per-set distributions are averaged. This repo ships **six** travel booking-intent sets (`collection-qa anchors`).

The paper embedded with OpenAI `text-embedding-3-small`. This tool embeds locally with `sentence-transformers` (default `sentence-transformers/all-MiniLM-L6-v2`) so there is no second API key. Anchor quality has to be re-checked on that model; the paper's anchors were tuned on 57 personal-care surveys and are not reused here.

**Personas are the point.** In the paper, dropping demographics made the distributions look human (KS similarity 0.91, mean intent 4.0) and cut ranking correlation roughly in half. `--ablate-personas` repeats that ablation. A realistic-looking distribution with a flat ranking is not a pass.

Direct Likert ratings are not implemented.

## Where it sits in EOS

EOS is the workflow that takes a CE from research to a live collection. Public Slack uses MMP for the unit of work inside EOS. The only expansion found there is "Managed Marketplace" (a 2025 #ask-delphi reply). Official training docs often leave the acronym unexpanded.

There is no documented Headout step that simulates user groups before go-live. This layer is a proposed insert at two existing pauses:

| Gate | When in the MMP | What it answers | What it must not do |
| --- | --- | --- | --- |
| **A. Post-assortment** | After Proposed Assortment exists, before product content is locked and before SOS is raised | Per-product booking intent by segment, whether the price ladder fits those segments, near-duplicate products, choice overload, gaps versus competitor listings and versus Headout products left off the collection | It does not choose vendors, raise SOS, or set a Scorpio rank |
| **B. Post-content-lock** | After content is locked on EOS, before Assortment Review creates a BOB sprint | Page-level booking intent, whether a microbrand is clearly a Headout reseller rather than the venue, FAQ and claim gaps, duration and price copy that disagrees with the cards | It does not replace Content review, BizQA, BOQA, or SRC |

Deterministic checks run at both gates. A **fail** on one of those checks is the only result that blocks. Synthetic purchase-intent bands are research signals until they are calibrated (see below). France's late-2026 MMP thread is the failure mode Gate B is meant to avoid: new merchandising requirements showing up after content is closed.

## Layout

```
src/collection_qa/     package and CLI
specs/                 pilot collection specs (YAML) and the API extracts they were built from
scripts/build_pilot_specs.py
tests/
reports/mock/          scorecards from a mock run
```

A spec is YAML or JSON: id, name, destination, page type (`headout_collection`, `microbrand`, or `proposed_assortment`), products (title, type, price, currency, unit, duration, features, rating, inclusions, pickup, cancellation), and page content (hero, USPs, FAQs, trust signals). `proposed_assortment` is for a CE Headout does not yet list. Both pilots below are live Headout collections, not proposals.

## Persona weights

Defaults live in `collection_qa/personas.py` and are labeled **assumptions**. They are not a booking extract.

- **Masai Mara** (`masai-mara`): international couples and families, mid and premium budgets, mostly planning months ahead, starting in Nairobi. Multi-day safari, not a same-day ticket.
- **Milford Sound** (`milford-sound`): more Australia / New Zealand / short-haul mix, more budget and mid, more last-minute and weeks-ahead planning, Queenstown weighted above Te Anau. Day trip and a short cruise, not a week in the bush.
- Any other collection id uses a generic mix, and the scorecard says so.

A spec may set `persona_weights` to override any attribute. Weights for an attribute must sum to 1.

```bash
collection-qa personas masai-mara
collection-qa personas milford-sound
```

Each sampled persona has: source market, age band, trip type (solo / couple / family with kids / friends), budget tier, planning horizon, first-timer or repeat, accessibility, interests, device, and channel, plus a starting point (`base`).

## How to run

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # put ANTHROPIC_API_KEY in .env; never commit it

# Deterministic checks only. No model, no API key.
collection-qa check specs/masai-mara.yaml
collection-qa check specs/milford-sound.yaml

# Full scorecard with the rule-based stand-in (no API spend).
collection-qa run specs/masai-mara.yaml --dry-run --personas 30 --out reports/mock
collection-qa run specs/milford-sound.yaml --dry-run --personas 30 --out reports/mock

# Live Claude. Key is read from the environment by the official SDK.
export ANTHROPIC_API_KEY=...
collection-qa run specs/masai-mara.yaml --personas 30 --out reports/live
```

Useful flags:

| Flag | Default | Role |
| --- | --- | --- |
| `--model` | `claude-sonnet-5-5` (or `COLLECTION_QA_MODEL`) | Anthropic model id |
| `--embedding-model` | `sentence-transformers/all-MiniLM-L6-v2` | Local embedding checkpoint |
| `--embedder hash` | `sentence-transformers` | Offline lexicon embedder for tests. Not the paper's method |
| `--completions` | 1 | Paper used 2 samples per prompt and averaged them |
| `--epsilon` / `--temperature` | 0 / 1 | SSR pmf parameters from the paper's main setting |
| `--llm-temperature` | 0.5 | Paper's main decoding temperature. Dropped and retried if the model rejects it |
| `--workers` | 8 | Concurrent Messages API calls |
| `--gate A` or `--gate B` | `both` | Skip the other stimulus |
| `--max-products N` | all | Shorter run |
| `--ablate-personas` | off | Paper's no-demographics ablation |
| `--cache-dir` | `.cache/collection-qa` | Sqlite cache of LLM responses, keyed by model, temperature, and prompt |

Every run prints a **cost estimate** before the calls: rough input tokens at 4 characters per token, 180 output tokens per call, and the public base price for the model (Sonnet 5.5 at $2 / $10 per million tokens as of the models page fetched 2026-11-26). Thinking tokens are not in that estimate. A mock run prints the same estimate and then records $0 actual spend. A live run adds actual token counts from the API.

Rebuild the pilot YAML after editing `scripts/build_pilot_specs.py`:

```bash
PYTHONPATH=src python scripts/build_pilot_specs.py
```

### Tests

```bash
pytest
```

Tests cover SSR math (minimum subtraction, epsilon, temperature, averaging), persona sampling and the Mara vs Milford weight split, deterministic checks including the seeded pilot specs, and an end-to-end mock run. They use the hash embedder and do not need an API key or a model download.

## Scorecard

`reports/mock/<id>.scorecard.json` and `.md` contain:

- Purchase-intent distributions and means by product, and by budget tier, trip type, and first-timer vs repeat
- Top and bottom products in each segment
- Deterministic and structural issues with severity `pass`, `info`, `warn`, or `fail`
- Whether a fail blocks go-live
- Sample persona quotes
- The cost estimate

Gate status is the worst **blocking** deterministic result. Synthetic means use bands of pass ≥ 3.6, warn ≥ 3.0, and fail below that. Those bands are assumptions. A synthetic fail is reported as a research status and does not block.

Structural assortment checks, also assumptions rather than Headout policy:

- Choice overload: 15 or more products on the collection
- Cannibalisation: same duration, from-prices within 12%, title token overlap at least 0.62
- Price ladder: within one price unit, budget intent should not rise toward the expensive third, and luxury intent should not fall toward it
- Same-currency price drift under 1.5% passes (FX and timing noise). Above 5% fails. Figures in another currency are stored and not converted

## Pilot collections

Fetched **2026-11-26**. Both already exist on Headout. Neither spec is a competitor-built proposal. Vatican and Colosseum notes were used only as a pattern for how a collection and a microbrand differ.

### Masai Mara — collection 7324, microbrand

- Marketplace: https://www.headout.com/masai-mara-c-7324/ (POI, primary city NAIROBI). H1 "Experience the best of the Masai Mara from Nairobi". SSR long-form payload was empty. The HTML embedded the first nine cards.
- Microbrand under test: https://www.masai-mara-safaris.com/ (legal entity Headout Inc). This is the spec's page, because the CMS content is actually in the payload: hero, comparison copy, schema.org FAQs.
- Catalog: 17 products from `https://api-ho.headout.com/api/v2/collections/7324/product-cards/?currency=USD&language=EN&sort-type=POPULARITY`. Prices in the spec are that USD response.
- A 3-day budget camping safari (product 56686) is live on Headout and is **not** in this collection. Its price was not on the fetched page.
- Viator and GetYourGuide list 3-day budget joining safaris from about $196 and $345. Park-fee treatment on those pages is not comparable to Headout cards that say entry fees are included, so the spec does not call that a like-for-like gap.

### Milford Sound cruises — collection 3945, headout.com

- https://www.headout.com/milford-sound-cruise-tickets-c-3945/ (DAY_TRIP, secondary cities QUEENSTOWN and TE_ANAU). H1 "Experience the best cruises in Milford Sound". Meta description promises a 2-hour cruise. SSR long-form body was empty.
- Catalog: 24 products from the same product-card API with `currency=NZD`. The HTML fetched from this environment embedded USD from-prices instead. Those are not compared to the NZD catalog.
- No Headout microbrand turned up in this pass.
- Product 26901 is a Doubtful Sound cruise from Manapouri sitting in the Milford collection.
- RealNZ's own product page says the cruise is not fully wheelchair accessible. The confirmed collection copy does not say so.

Unknowns are listed in each spec and repeated on the scorecard. EOS CE ids are not on the public pages. From-prices on multi-variant cards are not labeled with the option they refer to (budget vs luxury, cruise-only vs fly-cruise-fly).

Regenerate the YAML rather than hand-editing prices. The trimmed API JSON is in `specs/source/`.

## What the mock pilot can and cannot say

`reports/mock/` is a **MOCK** run: 30 personas per collection. The words are a rule-based stand-in that mentions price, duration, and party. Embeddings are local MiniLM, so the SSR math is the real mapping, and the sentences are not Claude's. Means on this run sit in a narrow band around 3 (standard deviation about 0.07 on the Mara and 0.12 on Milford). That is what short templated text does in this embedding space. Segment order still puts the dearest fly-ins below shorter trips for budget personas. Treat those ranks as a worked example, not a conversion forecast.

The deterministic section of the same files is about the fetched pages. Read that section for the pilot findings. The run summary in the pull request states which embedder was used.

## Validation plan

Do this before anyone treats a mean intent score as a launch gate.

1. **Shadow mode.** On every new or revamped CE, run Gate A when Proposed Assortment is saved and Gate B when content is locked. Store the scorecard on the MMP. Do not block the sprint. After launch, join product-level mean intent to realized CVR and to booking share at 14 and 28 days.
2. **Backtest on live collections.** Vatican (collection 189) and Colosseum (220) have enough traffic to estimate a human ceiling: split days or languages, correlate mean CVR across products, and use that correlation as the test-retest ceiling the way the paper uses split-half reliability. Then score the same frozen pages with SSR and report correlation attainment (SSR correlation / ceiling) and KS similarity between the synthetic distribution and the distribution of observed outcomes, binned to five levels. Mara (7324) and Milford (3945) are the right next backtests once they have volume; they are a weaker first ceiling because they are newer.
3. **Anchor and embedder check.** Re-fit or replace the six anchor sets on real Headout booking-intent verbatims. Repeat with the production embedding model. The paper found that anchor choice moves the mapping, which is why the sets are averaged and why they must be retuned off personal care.
4. **Persona ablation as a regression test.** A change that keeps a pretty distribution and loses rank correlation against the backtest, or that makes `--ablate-personas` rank products the same way as the full panel, is a failed change. The paper's no-demographics condition is the template.
5. **Segment humility.** Age and income tracked in the paper. Gender, region, and ethnicity did not. Source-market and accessibility slices in this tool stay exploratory until the backtest says otherwise. Cells with fewer than five personas are marked thin.
6. **Only then** promote a blocking threshold, and only for a check that has beaten a simple baseline (price tier and review count) on held-out CEs.

Until that backtest exists, a BGM can use the deterministic fails as a content and assortment punch list, and can read the quotes for objections (pickup, "is this official?", a 13-hour day with kids). The numeric means are a screening aid.

## Limits

- Synthetic travelers do not have a real budget, a real visa, or a real weather window. The paper is explicit that this augments research and does not replace it.
- Training-data coverage is thinner for a new lodge or a small operator than for Milford Sound or the Mara. SSR will not invent demand that the web has not discussed.
- Empty long-form in a headout.com SSR payload also shows up on older collections. It means this pass did not confirm a FAQ, not that production has no guide.
- Prices move. The spec records the API currency that was requested and the fetch date. A visitor in another country sees another currency.
