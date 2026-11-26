"""Screening thresholds.

PI bands are uncalibrated assumptions for travel booking intent. The SSR paper's
human personal-care means sit near 4.0; that level is not a travel-CVR target.
Synthetic PI issues never block go-live. Price and content checks can.
"""

# Research-only purchase-intent bands (1–5 Likert mean).
PI_PASS = 3.6
PI_WARN = 3.0

# Same-currency from-price drift. Under PASS is treated as FX/timing noise.
PRICE_REL_PASS = 0.015
PRICE_REL_WARN = 0.05

# Assortment shape. These are review triggers, not Headout policy.
CHOICE_OVERLOAD_N = 15
CANNIBAL_JACCARD = 0.62
CANNIBAL_PRICE_RATIO = 1.12

# Duration card spans a short cruise and a long transfer in one from-price.
DURATION_SPAN_RATIO = 3.0
DURATION_SPAN_HOURS = 3.0

SEVERITY_RANK = {"pass": 0, "info": 1, "warn": 2, "fail": 3}
