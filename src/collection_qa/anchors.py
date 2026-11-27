"""Travel booking-intent Likert anchors for Semantic Similarity Rating.

The reference sets in arXiv 2510.08338 were manually optimized on 57 personal-care
surveys. They are not reused here. These six sets are travel-specific, generic
across products, and meant to be averaged. They are a starting point, not a
calibrated instrument. See CALIBRATION_PLAN.
"""

from __future__ import annotations

# Each set is a 5-tuple of statements for Likert points 1..5.
# 1 = booking unlikely, 3 = indifference or uncertainty, 5 = intent to book.
ANCHOR_SETS: list[list[str]] = [
    [
        "I would not book this.",
        "I probably would not book this.",
        "I am unsure whether I would book this.",
        "I would likely book this.",
        "I would book this.",
    ],
    [
        "This does not fit my trip at all.",
        "This is a poor fit for my trip.",
        "I am undecided about whether this fits my trip.",
        "This fits my trip well.",
        "This is exactly what I would book for my trip.",
    ],
    [
        "This is not worth booking at this price.",
        "I doubt this is good value for me.",
        "I am unsure whether the price is worth it.",
        "This looks like fair value and I would consider booking.",
        "This is clearly worth booking at this price.",
    ],
    [
        "I do not trust this listing enough to book it.",
        "I feel uneasy about booking this as it is presented.",
        "I am uncertain whether I can trust this listing.",
        "I trust this listing enough that I would book it.",
        "I fully trust this listing and would book it with confidence.",
    ],
    [
        "I would never book this for my trip.",
        "I would put this off and probably not book it.",
        "I might book this later, but I am not sure.",
        "I would book this for my upcoming trip.",
        "I would book this immediately.",
    ],
    [
        "I would choose a different experience instead of this.",
        "I would probably look for an alternative.",
        "I might book this or an alternative; I cannot tell yet.",
        "I would choose this over the alternatives I have seen.",
        "This is the experience I would book over the other options.",
    ],
]

LIKERT_POINTS = (1, 2, 3, 4, 5)

# Paper main experiments: epsilon = 0, temperature = 1.
DEFAULT_EPSILON = 0.0
DEFAULT_TEMPERATURE = 1.0

CALIBRATION_PLAN = """
Calibration plan (do this before any go-live threshold is treated as policy)

The anchor sets above were written for travel booking intent. They were not
optimized on Headout surveys. arXiv 2510.08338 shows that anchor wording moves
the map from text to Likert, and that averaging several sets only reduces that
dependence. It does not remove it.

1. Hold out anchors. Do not retune these sentences on the same collections that
   will be gated. If a new set is drafted, freeze it, then score a holdout.

2. Backtest on live collections. Pick collections with stable traffic and a
   known conversion rate (CVR) from collection page view to booking, at product
   (TGID) level. Run this package in shadow on the live page text. Compare:
   - product rank by mean SSR purchase intent vs rank by realized CVR
   - product rank vs rank by revenue per session
   Report Pearson correlation of the means, and Spearman rank correlation.
   The paper divides correlation by a human test-retest ceiling. Until Headout
   has a repeat survey, report the raw correlations and do not claim a
   "percent of human reliability."

3. Distribution check, only once human Likert exists. A small in-market panel
   (or a post-booking "how likely were you to book this before you saw reviews")
   gives a real 1-5 distribution. Compare it to the SSR pmf with
   Kolmogorov-Smirnov similarity, the paper's K^{xy} = 1 - KS distance.
   A realistic-looking pmf is not success by itself: the paper's no-persona
   ablation reached K^{xy} = 0.91 while ranking correlation fell to about 50%.

4. Shadow mode on the next MMP. After proposed assortment (Gate A) and again
   after content lock (Gate B), run SSR but do not block the EOS sprint. Store
   the scorecard. After launch, join it to CVR once the new CE has enough
   sessions (the ranking model itself is described internally as converging in
   a few days; wait longer than that before judging SSR). Thresholds in
   collection_qa.checks are labeled assumptions until this shadow set exists.

   A live Sonnet 5.5 pilot on Masai Mara and Milford Sound (30 personas, seed 7,
   780 calls, about US$3.15, 2026-11-26) put product means in a band of about
   3.17–3.46. The uncalibrated pass lines (page 3.6, segment 3.4, product 3.3)
   therefore mostly warn and do not rank the assortment. Until step 2 exists,
   read relative_rank and z_vs_collection, not the absolute cut.

5. Segment trust. Do not treat source-market or age slices as a go-live gate
   until they track Headout booking mix. The paper replicated age and income
   better than gender or region. Persona weights in this package are priors,
   not measured demand.

6. Embedding sensitivity. Re-run the same frozen reactions through a second
   local model. The live pilot used English-only all-MiniLM-L6-v2 and lost
   25 replies that came back in German or French. The default is now
   paraphrase-multilingual-MiniLM-L12-v2, and the prompt requires English.
   Confirm a second model before locking one. Cosine similarity and
   minimum-subtraction stay fixed so the only change is the embedder.
""".strip()
