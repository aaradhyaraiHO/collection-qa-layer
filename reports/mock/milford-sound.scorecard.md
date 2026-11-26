# MOCK scorecard — Milford Sound cruises

MOCK OUTPUT. Free-text reactions come from a rule-based stand-in, not Claude. Embeddings: sentence-transformers/all-MiniLM-L6-v2. Read purchase-intent numbers as a worked example of the scorecard. Read deterministic checks as findings about the fetched pages. Catalog seeded from live Headout pages and APIs.

- Collection `milford-sound` · public id 3945 · headout_collection · live_headout
- Fetched 2026-11-26 · personas 30 · seed 20261126
- LLM: mock-rule-based · embeddings: sentence-transformers/all-MiniLM-L6-v2
- SSR: ε=0.0, T=1.0, anchor sets=['booking_plain', 'booking_now', 'fit_for_me', 'value', 'choose_over_others', 'commitment']
- Estimated live cost: $1.91 (Rough estimate at 4 characters per token and 180 output tokens per call. Excludes Claude thinking tokens.)
- Actual API spend recorded this run: $0.0000

## How to read this

Purchase-intent distributions are 5-point booking-intent pmfs from semantic similarity rating. The mean is the expected rating. Pass ≥ 3.6, warn ≥ 3.0, and below 3.0 is a research fail. Those bands are uncalibrated assumptions and do not block go-live. A gate fails only when a deterministic check fails.

**Gate A (post-assortment):** fail · research signal fail

**Gate B (post-content-lock):** fail · research signal warn

## Unknowns in the spec

- No Headout microbrand for Milford Sound was found in this pass.
- The public collection id is 3945. The EOS Combined Entity id is not on the public page.
- The collection SSR payload's long-form body was empty. A client-rendered guide may exist and was not confirmed. A rendered-markdown fetch produced a long FAQ and prices such as NZ$143.20 and NZ$179; those strings were not in the raw HTML fetched from this environment and are not used.
- The headout.com HTML fetched here embedded USD from-prices (for example 84.98 USD on product 29695). The catalog below is the NZD API response. The two are not compared.
- Inclusions are marked unknown where the product page was not opened.
- Secondary cities on the collection record are QUEENSTOWN and TE_ANAU.

## Deterministic and assortment checks

| Severity | Id | Gate | Blocks | What it found |
| --- | --- | --- | --- | --- |
| fail | pickup_stated | both | yes | Some products do not state a meeting point or say that pickup is not included. |
| warn | pickup_stated | both | no | Pickup or transfers are marked as depending on the option selected. The collection card does not name the meeting point. |
| warn | duration_span | A | no | These cards publish a duration range at least 3× wide and at least 3 hours across. The from-price is then hard to read as one experience. |
| warn | duration_claim | B | no | The page says “Experience a 2-hour Milford Sound Cruise with a view of the iconic Mitre Peak.” (2 hours). The lead card Milford Sound Cruise with Optional Lunch is 1 hr 40 mins - 6 hrs. The claimed length sits inside that range, so the line is not false, but it hides the range. |
| warn | zero_reviews | A | no | 11 of 24 products have 0 reviews on the collection card. |
| warn | assortment_scope | A | no | These product titles do not contain the collection scope keywords (milford). Confirm they belong on this collection. |
| warn | faq_coverage | B | no | No FAQ question and answer was confirmed in the fetched page. The collection SSR payload's long-form body was empty, which matches other Headout collection pages, so a client-rendered guide may still exist. |
| warn | accessibility_disclosure | B | no | A fetched product page says the cruise is not fully wheelchair accessible. The confirmed collection copy does not say so. |
| info | competitor_gap | A | no | Viator lists “Cruise Milford NZ small boutique cruise, and other fiord cruises” from 88 USD. Comparability is 'currency_unknown'. The listing page showed from-prices in US dollars, from about US$88 for a RealNZ cruise and US$103 for a small-boat cruise. Not compared with the NZD catalog. |
| info | competitor_gap | A | no | GetYourGuide lists “From Queenstown: Milford Sound Discover More Longest Cruise” from 188 None. Comparability is 'currency_unknown'. Southern Discoveries coach-and-cruise, about 13.5 hours, from $188 per person. The fetched page did not confirm the currency. |
| warn | cannibalisation | A | no | 1 product pair(s) share a duration, a from-price within 12%, and a title overlap of at least 62%. Review whether both need to sit on the collection. First pairs: 56773 vs 55218 (J=0.75) |
| warn | choice_overload | A | no | 24 products on one collection. The review trigger is 15, which is an assumption for this QA layer, not a Headout policy. Synthetic mean PI standard deviation across products is 0.12. |

Passed: price_consistency, mixed_price_units, duration_present, cancellation_present, reseller_disclosure, price_ladder_fit.

## Research signals (synthetic purchase intent, not a go-live block)

| Severity | Id | Gate | Blocks | What it found |
| --- | --- | --- | --- | --- |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Milford Sound Scenic Flyover & Cruise is 2.85. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Te Anau: Milford Sound Day Trip with Cruise & Return Transfers is 3.15. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for Milford Sound Boutique Small-Boat Cruise is 3.12. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Milford Sound Day Trip with Cruise, & Return Transfers is 3.06. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for Milford Sound Extended Scenic Cruise by Southern Discoveries with Optional Transfers is 3.18. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Manapouri: Doubtful Sound Wilderness Cruise is 3.11. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for Milford Sound Cruise with Optional Lunch is 3.08. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Milford Sound Premium Small Group Tour with Cruise & Lunch is 3.09. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for Overnight Milford Sound Cruise with Dinner & Activities is 2.68. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine is 2.91. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: 1.5 to 2-Hour Milford Sound Helicopter Tour is 3.03. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Business Class Milford Sound Tour with Premium Cruise & Gourmet Lunch is 2.83. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for Milford Sound Cruise by RealNZ is 3.15. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for Milford Sound Nature Cruise is 3.18. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Te Anau: Small-Group Milford Sound Tour with Captain's VIP Cruise & Picnic Lunch is 3.01. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Small-Group Milford Sound Tour and Captain’s VIP All-Inclusive Food & Beverages is 2.96. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Small-Group Tour with Longest Milford Sound Cruise and Picnic Lunch is 2.98. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Te Anau: Small-Group Day Trip with Extended Milford Sound Cruise & Picnic Lunch is 3.04. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford is 3.14. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Te Anau: Milford Sound Premium Small-Group Tour with Cruise (Max 13 Guests) is 3.04. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Milford Sound Discover More Cruise Day Trip with Small-Group Transfers and Lunch is 3.03. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Queenstown: Milford Sound Small-Group Tour with Captain's VIP Cruise is 2.97. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| fail | synthetic_product_pi | A | no | Synthetic mean booking intent for From Te Anau: Milford Sound Small-Group Tour with Captain's VIP Lounge Cruise is 2.99. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_product_pi | A | no | Synthetic mean booking intent for Te Anau Glowworm Caves and Milford Sound Cruise Experience is 3.22. Pass ≥ 3.6, warn ≥ 3.0, below that is a research fail. These bands are uncalibrated and do not block go-live. |
| warn | synthetic_page_pi | B | no | Synthetic mean booking intent for the page is 3.32. Pass ≥ 3.6, warn ≥ 3.0. Uncalibrated; does not block go-live. |

## Gate A — products

| Product | Price | Mean PI | Distribution | Reviews |
| --- | --- | --- | --- | --- |
| Milford Sound Cruise with Optional Lunch | 155 NZD per_person | 3.08 | 1:0.17 2:0.13 3:0.29 4:0.26 5:0.15 | 2097 |
| Milford Sound Boutique Small-Boat Cruise | 179 NZD per_person | 3.12 | 1:0.14 2:0.16 3:0.28 4:0.26 5:0.15 | 2052 |
| From Te Anau: Milford Sound Day Trip with Cruise & Return Transfers | 230 NZD per_person | 3.15 | 1:0.16 2:0.14 3:0.26 4:0.27 5:0.17 | 782 |
| Milford Sound Cruise by RealNZ | 155 NZD per_person | 3.15 | 1:0.14 2:0.16 3:0.27 4:0.26 5:0.17 | 377 |
| From Manapouri: Doubtful Sound Wilderness Cruise | 359 NZD per_person | 3.11 | 1:0.17 2:0.17 3:0.21 4:0.27 5:0.18 | 251 |
| From Queenstown: Milford Sound Day Trip with Cruise, & Return Transfers | 275 NZD per_person | 3.06 | 1:0.18 2:0.15 3:0.26 4:0.25 5:0.17 | 637 |
| From Queenstown: Milford Sound Scenic Flyover & Cruise | 835 NZD per_person | 2.85 | 1:0.24 2:0.18 3:0.23 4:0.20 5:0.15 | 338 |
| Milford Sound Extended Scenic Cruise by Southern Discoveries with Optional Transfers | 199 NZD per_person | 3.18 | 1:0.15 2:0.11 3:0.32 4:0.27 5:0.16 | 27 |
| Overnight Milford Sound Cruise with Dinner & Activities | 839 NZD per_person | 2.68 | 1:0.26 2:0.22 3:0.21 4:0.20 5:0.11 | 18 |
| Milford Sound Nature Cruise | 179 NZD per_person | 3.18 | 1:0.13 2:0.13 3:0.34 4:0.25 5:0.15 | 0 |
| From Queenstown: 1.5 to 2-Hour Milford Sound Helicopter Tour | 1490 NZD per_person | 3.03 | 1:0.20 2:0.19 3:0.18 4:0.25 5:0.18 | 0 |
| From Queenstown: Milford Sound Discover More Cruise Day Trip with Small-Group Transfers and Lunch | 449 NZD per_person | 3.03 | 1:0.17 2:0.17 3:0.27 4:0.24 5:0.15 | 0 |
| Te Anau Glowworm Caves and Milford Sound Cruise Experience | 272.64 NZD per_person | 3.22 | 1:0.13 2:0.18 3:0.23 4:0.26 5:0.20 | 1791 |
| From Te Anau: Milford Sound Small-Group Tour with Captain's VIP Lounge Cruise | 449 NZD per_person | 2.98 | 1:0.18 2:0.18 3:0.25 4:0.25 5:0.14 | 0 |
| From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford | 275 NZD per_person | 3.13 | 1:0.16 2:0.17 3:0.24 4:0.25 5:0.18 | 95 |
| From Queenstown: Milford Sound Premium Small Group Tour with Cruise & Lunch | 369 NZD per_person | 3.09 | 1:0.16 2:0.18 3:0.26 4:0.24 5:0.17 | 76 |
| Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine | 389 NZD per_person | 2.91 | 1:0.21 2:0.16 3:0.27 4:0.22 5:0.13 | 20 |
| From Queenstown: Milford Sound Small-Group Tour with Captain's VIP Cruise | 529 NZD per_person | 2.97 | 1:0.21 2:0.18 3:0.21 4:0.23 5:0.17 | 0 |
| From Queenstown: Business Class Milford Sound Tour with Premium Cruise & Gourmet Lunch | 699 NZD per_person | 2.83 | 1:0.24 2:0.19 3:0.21 4:0.21 5:0.14 | 0 |
| From Te Anau: Small-Group Milford Sound Tour with Captain's VIP Cruise & Picnic Lunch | 449 NZD per_person | 3.01 | 1:0.19 2:0.17 3:0.24 4:0.24 5:0.16 | 0 |
| From Queenstown: Small-Group Milford Sound Tour and Captain’s VIP All-Inclusive Food & Beverages | 529 NZD per_person | 2.96 | 1:0.21 2:0.20 3:0.19 4:0.24 5:0.16 | 0 |
| From Te Anau: Milford Sound Premium Small-Group Tour with Cruise (Max 13 Guests) | 359 NZD per_person | 3.04 | 1:0.18 2:0.18 3:0.23 4:0.25 5:0.16 | 0 |
| From Queenstown: Small-Group Tour with Longest Milford Sound Cruise and Picnic Lunch | 449 NZD per_person | 2.98 | 1:0.19 2:0.18 3:0.26 4:0.22 5:0.16 | 0 |
| From Te Anau: Small-Group Day Trip with Extended Milford Sound Cruise & Picnic Lunch | 369 NZD per_person | 3.04 | 1:0.19 2:0.18 3:0.21 4:0.25 5:0.17 | 0 |

### Top and bottom by segment

**budget_tier**

- budget (n=11): high Milford Sound Nature Cruise (3.19), Milford Sound Extended Scenic Cruise by Southern Discoveries with Optional Transfers (3.17); low Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (2.64), Overnight Milford Sound Cruise with Dinner & Activities (2.65)
- mid (n=17): high Te Anau Glowworm Caves and Milford Sound Cruise Experience (3.29), From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.20); low Overnight Milford Sound Cruise with Dinner & Activities (2.65), From Queenstown: Business Class Milford Sound Tour with Premium Cruise & Gourmet Lunch (2.81)
- premium (n=2): high Te Anau Glowworm Caves and Milford Sound Cruise Experience (3.33), From Queenstown: Small-Group Milford Sound Tour and Captain’s VIP All-Inclusive Food & Beverages (3.28); low From Queenstown: 1.5 to 2-Hour Milford Sound Helicopter Tour (3.01), Overnight Milford Sound Cruise with Dinner & Activities (3.06)

**trip_type**

- solo (n=8): high Te Anau Glowworm Caves and Milford Sound Cruise Experience (3.20), Milford Sound Extended Scenic Cruise by Southern Discoveries with Optional Transfers (3.16); low Overnight Milford Sound Cruise with Dinner & Activities (2.69), From Queenstown: Business Class Milford Sound Tour with Premium Cruise & Gourmet Lunch (2.82)
- couple (n=10): high Te Anau Glowworm Caves and Milford Sound Cruise Experience (3.31), Milford Sound Nature Cruise (3.21); low Overnight Milford Sound Cruise with Dinner & Activities (2.70), From Queenstown: Business Class Milford Sound Tour with Premium Cruise & Gourmet Lunch (2.83)
- family_with_kids (n=3): high Milford Sound Extended Scenic Cruise by Southern Discoveries with Optional Transfers (3.18), Te Anau Glowworm Caves and Milford Sound Cruise Experience (3.17); low Overnight Milford Sound Cruise with Dinner & Activities (2.64), From Queenstown: Small-Group Tour with Longest Milford Sound Cruise and Picnic Lunch (2.78)
- friends (n=9): high Milford Sound Cruise by RealNZ (3.19), Milford Sound Nature Cruise (3.19); low Overnight Milford Sound Cruise with Dinner & Activities (2.65), From Queenstown: Business Class Milford Sound Tour with Premium Cruise & Gourmet Lunch (2.85)

**experience**

- first_timer (n=20): high Te Anau Glowworm Caves and Milford Sound Cruise Experience (3.23), Milford Sound Nature Cruise (3.19); low Overnight Milford Sound Cruise with Dinner & Activities (2.67), From Queenstown: Business Class Milford Sound Tour with Premium Cruise & Gourmet Lunch (2.81)
- repeat (n=10): high Te Anau Glowworm Caves and Milford Sound Cruise Experience (3.19), Milford Sound Extended Scenic Cruise by Southern Discoveries with Optional Transfers (3.19); low Overnight Milford Sound Cruise with Dinner & Activities (2.69), From Queenstown: Business Class Milford Sound Tour with Premium Cruise & Gourmet Lunch (2.86)

## Gate B — page

Mean PI **3.32**. Distribution 1:0.09 2:0.16 3:0.26 4:0.29 5:0.19.

## Sample persona quotes

- **page** · milford-sound-012 · 18-24 traveler from NZ, traveling as friends, budget budget, planning horizon weeks, first timer, accessibility none, interest wildlife, starting point queenstown, on mobile via direct.
  > I am unsure about booking from this page. Milford Sound cruises is why our group of friends on a budget budget is looking, but I am not convinced which card is the one to reserve.

- **page** · milford-sound-023 · 25-34 traveler from DE, traveling as couple, premium budget, planning horizon weeks, repeat, accessibility none, interest scenery, starting point te_anau, on desktop via organic.
  > I would book from this page. Milford Sound cruises has the experience the two of us on a premium budget wants, and I am ready to book it.

- **product:Overnight Milford Sound Cruise with Dinner & Activities** · milford-sound-001 · solo · mean PI 2.69 · 35-44 traveler from AU, traveling as solo, budget budget, planning horizon weeks, first timer, accessibility none, interest photography, starting point te_anau, on mobile via organic.
  > I would not book this. 839 NZD per person for 17 hrs - 1 day 7 hrs is the wrong trip for me traveling alone on a budget budget, and Overnight Milford Sound Cruise with Dinner & Activities does not solve the way we actually travel.

- **product:Te Anau Glowworm Caves and Milford Sound Cruise Experience** · milford-sound-001 · solo · mean PI 3.20 · 35-44 traveler from AU, traveling as solo, budget budget, planning horizon weeks, first timer, accessibility none, interest photography, starting point te_anau, on mobile via organic.
  > I probably would not book this. Te Anau Glowworm Caves and Milford Sound Cruise Experience is 1 hr 40 mins - 2 hrs 15 mins at 272.64 NZD per person, which is a stretch for me traveling alone on a budget budget, so I would keep looking rather than book it.

- **product:Overnight Milford Sound Cruise with Dinner & Activities** · milford-sound-002 · couple · mean PI 2.70 · 55-64 traveler from other, traveling as couple, mid budget, planning horizon weeks, first timer, accessibility none, interest photography, starting point te_anau, on desktop via paid.
  > I would not book this. 839 NZD per person for 17 hrs - 1 day 7 hrs is the wrong trip for the two of us on a mid budget, and Overnight Milford Sound Cruise with Dinner & Activities does not solve the way we actually travel.

- **product:Te Anau Glowworm Caves and Milford Sound Cruise Experience** · milford-sound-002 · couple · mean PI 3.31 · 55-64 traveler from other, traveling as couple, mid budget, planning horizon weeks, first timer, accessibility none, interest photography, starting point te_anau, on desktop via paid.
  > I would book this. Te Anau Glowworm Caves and Milford Sound Cruise Experience at 272.64 NZD per person for 1 hr 40 mins - 2 hrs 15 mins is exactly the experience the two of us on a mid budget came for, and I am ready to book it.

- **product:Overnight Milford Sound Cruise with Dinner & Activities** · milford-sound-004 · family_with_kids · mean PI 2.64 · 45-54 traveler from IN, traveling as family_with_kids, mid budget, planning horizon weeks, repeat, accessibility none, interest scenery, starting point te_anau, on mobile via direct.
  > I would not book this. 839 NZD per person for 17 hrs - 1 day 7 hrs is the wrong trip for our family with kids on a mid budget, and Overnight Milford Sound Cruise with Dinner & Activities does not solve the way we actually travel.

- **product:Milford Sound Extended Scenic Cruise by Southern Discoveries with Optional Transfers** · milford-sound-004 · family_with_kids · mean PI 3.18 · 45-54 traveler from IN, traveling as family_with_kids, mid budget, planning horizon weeks, repeat, accessibility none, interest scenery, starting point te_anau, on mobile via direct.
  > I would probably book this. Milford Sound Extended Scenic Cruise by Southern Discoveries with Optional Transfers at 199 NZD per person for 2 hrs 15 mins - 13 hrs 30 mins fits this trip for our family with kids on a mid budget, as long as the inclusions on the card are the ones in the booking.

- **product:Overnight Milford Sound Cruise with Dinner & Activities** · milford-sound-007 · friends · mean PI 2.66 · 25-34 traveler from CN, traveling as friends, budget budget, planning horizon weeks, repeat, accessibility none, interest photography, starting point queenstown, on mobile via organic.
  > I would not book this. 839 NZD per person for 17 hrs - 1 day 7 hrs is the wrong trip for our group of friends on a budget budget, and Overnight Milford Sound Cruise with Dinner & Activities does not solve the way we actually travel.

- **product:Milford Sound Cruise by RealNZ** · milford-sound-007 · friends · mean PI 3.19 · 25-34 traveler from CN, traveling as friends, budget budget, planning horizon weeks, repeat, accessibility none, interest photography, starting point queenstown, on mobile via organic.
  > I would probably book this. Milford Sound Cruise by RealNZ at 155 NZD per person for 2 hrs fits this trip for our group of friends on a budget budget, as long as the inclusions on the card are the ones in the booking.

## Sources

- https://www.headout.com/milford-sound-cruise-tickets-c-3945/ — headout.com collection. H1, meta description, and nine SSR cards confirmed in the HTML. Long-form payload empty.
- https://api-ho.headout.com/api/v2/collections/3945/product-cards/?currency=NZD&language=EN&sort-type=POPULARITY — Collection product-card API, currency=NZD, sort=POPULARITY. 24 products.
- https://www.headout.com/milford-sound-cruise-tickets/milford-sound-cruise-by-realnz-e-37309/ — RealNZ product page, including the wheelchair limitation.
- https://www.viator.com/en-NZ/Fiordland-and-Milford-Sound-tours/Cruises-Sailing-and-Water-Tours/d756-g3 — Competitor context. Cruise from-prices were shown in US dollars.
- https://www.getyourguide.com/queenstown-l498/from-queenstown-milford-sound-discover-more-longest-cruise-t1068280/ — Competitor context. Queenstown coach-and-cruise from $188. Currency label was not confirmed.
