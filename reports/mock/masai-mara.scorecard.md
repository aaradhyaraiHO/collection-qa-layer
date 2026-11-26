# MOCK scorecard — Masai Mara

MOCK OUTPUT. Free-text reactions come from a rule-based stand-in, not Claude. Embeddings: sentence-transformers/all-MiniLM-L6-v2. Read purchase-intent numbers as a worked example of the scorecard. Read deterministic checks as findings about the fetched pages. Catalog seeded from live Headout pages and APIs.

- Collection `masai-mara` · public id 7324 · microbrand · live_headout
- Fetched 2026-11-26 · personas 30 · seed 20261126
- LLM: mock-rule-based · embeddings: sentence-transformers/all-MiniLM-L6-v2
- SSR: ε=0.0, T=1.0, anchor sets=['booking_plain', 'booking_now', 'fit_for_me', 'value', 'choose_over_others', 'commitment']
- Estimated live cost: $1.43 (Rough estimate at 4 characters per token and 180 output tokens per call. Excludes Claude thinking tokens.)
- Actual API spend recorded this run: $0.0000

## How to read this

Purchase-intent distributions are 5-point booking-intent pmfs from semantic similarity rating. The mean is the expected rating. Pass ≥ 3.6, warn ≥ 3.0, and below 3.0 is a research fail. Those bands are uncalibrated assumptions and do not block go-live. A gate fails only when a deterministic check fails.

**Gate A (post-assortment):** warn · research signal fail

**Gate B (post-content-lock):** warn · research signal warn

## Unknowns in the spec

- The public collection id is 7324. The EOS Combined Entity id is not on the public page. Vatican and Colosseum used the same number for both; that pattern was not verified here.
- multiVariant and otherPricesExist are true on several cards. The from-price is not labeled with a stay tier (budget, comfort, luxury) or shared versus private.
- Price of Headout product 56686, the 3-day budget camping safari, was not in the fetched product page.
- A rendered fetch of the homepage did not include the sentence 'Crafted by Headout'. That sentence was on the about and fly-in URLs in search snippets. The homepage payload does contain 'Headout Inc'.
- Competitor park-fee treatment is not fully comparable. The Viator extract lists a $20 destination payment and an ambiguous park-fee line. The GetYourGuide extract tells the traveler to pay park fees of $200 or $400.

## Deterministic and assortment checks

| Severity | Id | Gate | Blocks | What it found |
| --- | --- | --- | --- | --- |
| warn | mixed_price_units | A | no | From-prices on this collection use more than one unit (per_group, per_person). A single list will not read as a price ladder unless every card shows the unit. Per-group ids are listed. |
| warn | pickup_stated | both | no | Pickup or transfers are marked as depending on the option selected. The collection card does not name the meeting point. |
| warn | zero_reviews | A | no | 7 of 17 products have 0 reviews on the collection card. |
| warn | inclusion_claim | B | no | The page says “Lake Nakuru National Park (included with 4+ days safaris)”. 6 product(s) meet the duration condition and do not carry the tag 'lake_nakuru'. The same page also says: Masai Mara, or Masai Mara with Lake Naivasha or Lake Nakuru. |
| warn | inclusion_claim | B | no | The page says “Lake Naivasha & Hell's Gate (included with 4+ days safaris)”. 7 product(s) meet the duration condition and do not carry the tag 'lake_naivasha'. The same page also says: Masai Mara, or Masai Mara with Lake Naivasha or Lake Nakuru. |
| warn | inclusion_claim | B | no | The page says “Amboseli National Park (included with 5–7-day safaris)”. 3 product(s) meet the duration condition and do not carry the tag 'amboseli'. The same page also says: The comparison table describes 5-day routes as Masai Mara, Lake Nakuru and Lake Naivasha, or Masai Mara and Amboseli. |
| warn | reseller_disclosure | B | no | The microbrand text names Headout, and the fetched copy does not contain a sentence that this is not the venue's website. Travelers can still read the domain as the operator. |
| warn | faq_coverage | B | no | Confirmed FAQs are missing these topics: cancellation. |
| warn | outside_collection | A | no | Headout publishes related products that are not in this collection. Titles: From Nairobi: 3-Day Masai Mara Budget Camping Safari. |
| info | competitor_gap | A | no | Viator lists “3 days 2 nights budget group safari to Maasai Mara National Reserve” from 195.56 USD. Comparability is 'fees_unclear'. From $195.56 per person plus $20 paid in destination. Park-fee inclusion was ambiguous in the fetched extract, so this is not a like-for-like gap. |
| info | competitor_gap | A | no | GetYourGuide lists “From Nairobi: Maasai Mara 3-Day Budget Safari Holiday by Jeep” from 345 USD. Comparability is 'fees_unclear'. The fetched page showed $345 per person and told travelers to pay park entrance fees of $200 (Jan–Jun) or $400 (Jul–Dec). Currency was the symbol shown, not a confirmed ISO label. Not like-for-like with Headout cards that say entry fees are included. |
| warn | cannibalisation | A | no | 5 product pair(s) share a duration, a from-price within 12%, and a title overlap of at least 62%. Review whether both need to sit on the collection. First pairs: 57722 vs 57638 (J=0.917); 61529 vs 61528 (J=0.857); 57712 vs 57728 (J=0.833); 57698 vs 57697 (J=0.8); 57690 vs 57697 (J=0.8) |
| warn | choice_overload | A | no | 17 products on one collection. The review trigger is 15, which is an assumption for this QA layer, not a Headout policy. Synthetic mean PI standard deviation across products is 0.07. |

Passed: price_consistency, duration_present, cancellation_present, duration_span, assortment_scope, price_ladder_fit.

## Research signals (synthetic purchase intent, not a go-live block)

| Severity | Id | Gate | Blocks | What it found |
| --- | --- | --- | --- | --- |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees is 2.88. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees is 3.03. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 4-Day Masai Mara Safari with Stays, and Entry Fees is 2.96. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays, and Entry Fees is 3.00. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays, and Entry Fees is 2.94. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees is 3.03. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees is 2.93. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha & Amboseli with Stays and Entry Fees is 2.84. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees is 2.83. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees is 2.99. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees is 2.95. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees is 2.96. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees is 3.01. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: 3-Day Masai Mara Safari With Stays, and Entry Fees is 3.00. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: Fly-In and Drive 4-Day Masai Mara and Lake Nakuru Safari with Luxury Stays and Entry Fees is 2.94. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: Fly-In and Drive 4-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees is 2.82. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Nairobi: Fly-In and Drive 5-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees is 2.86. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_page_pi | B | no | Synthetic mean booking intent for the page is 3.31. Pass ≥ 3.6, warn ≥ 3.0. Uncalibrated; does not block go-live. |

## Gate A — products

| Product | Price | Mean PI | Distribution | Reviews |
| --- | --- | --- | --- | --- |
| From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays, and Entry Fees | 638.15 USD per_person | 3.00 | 1:0.19 2:0.17 3:0.24 4:0.24 5:0.16 | 0 |
| From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha & Amboseli with Stays and Entry Fees | 1080.37 USD per_person | 2.84 | 1:0.20 2:0.22 3:0.23 4:0.22 5:0.12 | 0 |
| From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees | 2903.97 USD per_group | 2.83 | 1:0.21 2:0.20 3:0.25 4:0.22 5:0.12 | 449 |
| From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees | 923.84 USD per_person | 2.93 | 1:0.19 2:0.20 3:0.23 4:0.23 5:0.15 | 100 |
| From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees | 430.15 USD per_person | 3.01 | 1:0.18 2:0.18 3:0.24 4:0.24 5:0.15 | 178 |
| From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees | 561.53 USD per_person | 3.03 | 1:0.18 2:0.18 3:0.23 4:0.25 5:0.16 | 180 |
| From Nairobi: 4-Day Masai Mara Safari with Stays, and Entry Fees | 618.45 USD per_person | 2.96 | 1:0.19 2:0.18 3:0.24 4:0.24 5:0.15 | 460 |
| From Nairobi: 3-Day Masai Mara Safari With Stays, and Entry Fees | 414.85 USD per_person | 3.00 | 1:0.18 2:0.18 3:0.24 4:0.24 5:0.15 | 150 |
| From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees | 320.72 USD per_group | 3.03 | 1:0.19 2:0.14 3:0.27 4:0.25 5:0.15 | 0 |
| From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 1593.74 USD per_group | 2.99 | 1:0.18 2:0.19 3:0.25 4:0.23 5:0.15 | 83 |
| From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 2064.41 USD per_group | 2.95 | 1:0.19 2:0.19 3:0.24 4:0.23 5:0.15 | 70 |
| From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 2631.41 USD per_group | 2.88 | 1:0.21 2:0.20 3:0.23 4:0.22 5:0.14 | 0 |
| From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays, and Entry Fees | 785.92 USD per_person | 2.94 | 1:0.18 2:0.18 3:0.29 4:0.23 5:0.12 | 356 |
| From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees | 869.11 USD per_person | 2.96 | 1:0.18 2:0.19 3:0.26 4:0.23 5:0.14 | 170 |
| From Nairobi: Fly-In and Drive 4-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees | 3669.42 USD per_group | 2.82 | 1:0.24 2:0.20 3:0.22 4:0.20 5:0.15 | 0 |
| From Nairobi: Fly-In and Drive 4-Day Masai Mara and Lake Nakuru Safari with Luxury Stays and Entry Fees | 3568.74 USD per_group | 2.94 | 1:0.20 2:0.19 3:0.24 4:0.22 5:0.15 | 0 |
| From Nairobi: Fly-In and Drive 5-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees | 4219.68 USD per_group | 2.86 | 1:0.22 2:0.20 3:0.23 4:0.21 5:0.14 | 0 |

### Top and bottom by segment

**budget_tier**

- mid (n=14): high From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays, and Entry Fees (3.08), From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees (3.05); low From Nairobi: Fly-In and Drive 4-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees (2.70), From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.73)
- premium (n=11): high From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (3.11), From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.10); low From Nairobi: 3-Day Masai Mara Safari With Stays, and Entry Fees (3.01), From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.01)
- budget (n=5): high From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.05), From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees (2.94); low From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays, and Entry Fees (2.55), From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha & Amboseli with Stays and Entry Fees (2.57)

**trip_type**

- solo (n=4): high From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays, and Entry Fees (3.07), From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees (3.04); low From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.67), From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (2.71)
- couple (n=14): high From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.06), From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees (3.04); low From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.81), From Nairobi: Fly-In and Drive 4-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees (2.84)
- family_with_kids (n=5): high From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.03), From Nairobi: Fly-In and Drive 4-Day Masai Mara and Lake Nakuru Safari with Luxury Stays and Entry Fees (3.00); low From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha & Amboseli with Stays and Entry Fees (2.70), From Nairobi: Fly-In and Drive 4-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees (2.71)
- friends (n=7): high From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.04), From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees (3.02); low From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays, and Entry Fees (2.90), From Nairobi: Fly-In and Drive 4-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees (2.91)

**experience**

- first_timer (n=19): high From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays, and Entry Fees (3.06), From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees (3.05); low From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.83), From Nairobi: Fly-In and Drive 4-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees (2.85)
- repeat (n=11): high From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.03), From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays, and Entry Fees (3.00); low From Nairobi: Fly-In and Drive 4-Day Masai Mara, Nakuru, and Naivasha Safari with Luxury Stays and Entry Fees (2.77), From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha & Amboseli with Stays and Entry Fees (2.79)

## Gate B — page

Mean PI **3.31**. Distribution 1:0.10 2:0.20 3:0.19 4:0.29 5:0.22.

## Sample persona quotes

- **page** · masai-mara-030 · 25-34 traveler from US, traveling as family_with_kids, budget budget, planning horizon weeks, repeat, accessibility none, interest comfort, starting point nairobi, on desktop via organic.
  > I probably would not book from this Masai Mara page. A few titles are close for our family with kids on a budget budget, but I am unlikely to book until the prices and the plan are easier to compare.

- **page** · masai-mara-027 · 35-44 traveler from DE, traveling as couple, mid budget, planning horizon weeks, first timer, accessibility other, interest photography, starting point nairobi, on mobile via direct.
  > I would probably book from this page. There is an option that fits this trip for the two of us on a mid budget, and the microbrand gives me enough to choose.

- **product:From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees** · masai-mara-001 · solo · mean PI 2.67 · 45-54 traveler from US, traveling as solo, mid budget, planning horizon months, first timer, accessibility none, interest migration, starting point already_in_kenya, on mobile via organic.
  > I would not book this. 2903.97 USD per group for 5 days is the wrong trip for me traveling alone on a mid budget, and From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees does not solve the way we actually travel.

- **product:From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays, and Entry Fees** · masai-mara-001 · solo · mean PI 3.07 · 45-54 traveler from US, traveling as solo, mid budget, planning horizon months, first timer, accessibility none, interest migration, starting point already_in_kenya, on mobile via organic.
  > I would probably book this. From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays, and Entry Fees at 638.15 USD per person for 4 days fits this trip for me traveling alone on a mid budget, as long as the inclusions on the card are the ones in the booking.

- **product:From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees** · masai-mara-002 · couple · mean PI 2.81 · 55-64 traveler from other, traveling as couple, mid budget, planning horizon weeks, first timer, accessibility none, interest migration, starting point already_in_kenya, on desktop via paid.
  > I would not book this. 2903.97 USD per group for 5 days is the wrong trip for the two of us on a mid budget, and From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees does not solve the way we actually travel.

- **product:From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees** · masai-mara-002 · couple · mean PI 3.06 · 55-64 traveler from other, traveling as couple, mid budget, planning horizon weeks, first timer, accessibility none, interest migration, starting point already_in_kenya, on desktop via paid.
  > I am unsure about From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees. 1593.74 USD per group and 3 days could work for the two of us on a mid budget, but I am not convinced the card tells me what I would actually get.

- **product:From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha & Amboseli with Stays and Entry Fees** · masai-mara-004 · family_with_kids · mean PI 2.70 · 45-54 traveler from AE, traveling as family_with_kids, mid budget, planning horizon months, repeat, accessibility none, interest migration, starting point nairobi, on mobile via direct.
  > I probably would not book this. From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha & Amboseli with Stays and Entry Fees is 7 days at 1080.37 USD per person, which is a stretch for our family with kids on a mid budget, so I would keep looking rather than book it.

- **product:From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees** · masai-mara-004 · family_with_kids · mean PI 3.03 · 45-54 traveler from AE, traveling as family_with_kids, mid budget, planning horizon months, repeat, accessibility none, interest migration, starting point nairobi, on mobile via direct.
  > I would probably book this. From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees at 1593.74 USD per group for 3 days fits this trip for our family with kids on a mid budget, as long as the inclusions on the card are the ones in the booking.

- **product:From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays, and Entry Fees** · masai-mara-007 · friends · mean PI 2.90 · 25-34 traveler from IN, traveling as friends, mid budget, planning horizon months, repeat, accessibility none, interest photography, starting point nairobi, on mobile via organic.
  > I would probably book this. From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays, and Entry Fees at 785.92 USD per person for 5 days fits this trip for our group of friends on a mid budget, as long as the inclusions on the card are the ones in the booking.

- **product:From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees** · masai-mara-007 · friends · mean PI 3.04 · 25-34 traveler from IN, traveling as friends, mid budget, planning horizon months, repeat, accessibility none, interest photography, starting point nairobi, on mobile via organic.
  > I would probably book this. From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees at 320.72 USD per group for 17 hrs fits this trip for our group of friends on a mid budget, as long as the inclusions on the card are the ones in the booking.

## Sources

- https://www.masai-mara-safaris.com/ — Headout microbrand homepage. CMS payload and schema.org FAQ.
- https://www.masai-mara-safaris.com/legal/ — Legal entity Headout Inc, 82 Nassau Street, New York.
- https://www.headout.com/masai-mara-c-7324/ — headout.com collection. SSR product cards and empty long-form payload.
- https://api-ho.headout.com/api/v2/collections/7324/product-cards/?currency=USD&language=EN&sort-type=POPULARITY — Collection product-card API, currency=USD, sort=POPULARITY. 17 products.
- https://www.viator.com/tours/Nairobi/3-DAYS-2-NIGHTS-BUDGET-GROUP-SAFARI-TO-MAASAI-MARA-NATIONAL-RESERVE/d5280-60115P2 — Competitor context. From $195.56 per person plus $20 paid in destination.
- https://www.getyourguide.com/nairobi-l267/from-nairobi-maasai-mara-3-day-budget-safari-holiday-t453629/ — Competitor context. Page showed $345 per person and told travelers to pay park fees separately.
- https://www.headout.com/safari/from-nairobi-3-day-masai-mara-budget-camping-safari-e-56686/ — Headout budget camping safari that is not in collection 7324. Price was not on the fetched page.
