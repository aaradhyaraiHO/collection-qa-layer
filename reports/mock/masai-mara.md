# Collection QA scorecard: Masai Mara safaris

> **MOCK OUTPUT. Reactions are deterministic templates, not Claude. Embeddings are lexical-bow, not a judgment of real travelers. Do not use these scores as market research or as a go-live decision.**

- Collection id: `masai-mara`
- CE / collection id on Headout: `7324`
- Destination: Masai Mara National Reserve, Kenya
- Provenance: **live_headout**. Live Headout collection plus the Headout-operated microbrand masai-mara-safaris.com. This is not a competitor-built proposal. Numeric "from" prices were not rendered for these safaris in the captures below (the public product-card API returned HTTP 403, and the HTML render did not include a currency amount for the Mara cards). Prices are left null on purpose.

- Source pages fetched: 2026-11-26
- Scorecard generated: 2026-11-26T21:59:27.034235+00:00
- Persona seed: **7**

## Method

Semantic Similarity Rating (arXiv 2510.08338): free-text booking intent, embedded with `lexical-bow`, cosine similarity to 6 sets of travel Likert anchors, minimum-similarity subtraction (epsilon=0.0, temperature=1.0), then the per-set distributions are averaged.

Panel: 30 personas, seed 7, profile weights are assumptions. Model `claude-sonnet-5-5`, 1 completion(s) per prompt. LLM calls made: 480. Cache hits: 0.

Assumption, not measured Headout demand. Replace with booking-mix weights before a segment gap is used as a go-live gate. Axes are sampled independently; real travelers are correlated.

## Cost

Cost (pre-run estimate, published price)
  model: claude-sonnet-5-5
  calls: 480
  input tokens: 257239
  output tokens: 35867
  rates: $2.0/MTok in, $10.0/MTok out
  estimated USD: $0.8731
MOCK run. Token counts are length estimates of template prompts. USD applies the published rate to those estimates so you can see what a live run of this size would cost. No API call was made.

## Gate results

| Gate | Severity | Code | Finding |
| --- | --- | --- | --- |
| A | fail | `relative_rank` | From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees is -1.53 standard deviations below this collection's mean purchase intent (2.82). This flag is relative. Absolute thresholds still need a CVR calibration. |
| A | fail | `relative_rank` | From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees is -1.53 standard deviations below this collection's mean purchase intent (2.82). This flag is relative. Absolute thresholds still need a CVR calibration. |
| B | fail | `assertion:nakuru-on-4-day-plus` | The microbrand says Lake Nakuru National Park is included with 4+ day safaris. Mara-only itineraries of 4 and 5 days are on the same page.
 — 6 of 10 in-scope products do not mention nakuru. |
| B | fail | `page_intent` | page 'primary' mean purchase intent is 2.71 (pass ≥ 3.6, warn ≥ 3.2). |
| B | fail | `segment_page_intent` | page:primary by trip_type 'couple' mean purchase intent is 2.69 (pass ≥ 3.4, warn ≥ 2.8). |
| B | fail | `segment_page_intent` | page:primary by trip_type 'family_with_kids' mean purchase intent is 2.74 (pass ≥ 3.4, warn ≥ 2.8). |
| B | fail | `segment_page_intent` | page:primary by trip_type 'friends' mean purchase intent is 2.64 (pass ≥ 3.4, warn ≥ 2.8). |
| B | fail | `segment_page_intent` | page:primary by trip_type 'solo' mean purchase intent is 2.79 (pass ≥ 3.4, warn ≥ 2.8). |
| B | fail | `segment_page_intent` | page:primary by budget_tier 'budget' mean purchase intent is 2.51 (pass ≥ 3.4, warn ≥ 2.8). |
| B | fail | `segment_page_intent` | page:primary by budget_tier 'luxury' mean purchase intent is 2.74 (pass ≥ 3.4, warn ≥ 2.8). |
| B | fail | `segment_page_intent` | page:primary by budget_tier 'mid' mean purchase intent is 2.77 (pass ≥ 3.4, warn ≥ 2.8). |
| B | fail | `segment_page_intent` | page:primary by budget_tier 'premium' mean purchase intent is 2.70 (pass ≥ 3.4, warn ≥ 2.8). |
| deterministic | fail | `missing_cancellation` | 8 of 14 products are missing cancellation. |
| deterministic | fail | `missing_pickup` | 6 of 14 products are missing pickup. |
| A | warn | `cannibalisation_intent` | From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees and From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees draw almost the same purchase intent (means 3.56 vs 3.51) on the same shelf. |
| A | warn | `cannibalisation_intent` | From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees and From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees draw almost the same purchase intent (means 2.82 vs 2.82) on the same shelf. |
| A | warn | `cannibalisation_intent` | From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees and From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees draw almost the same purchase intent (means 2.93 vs 2.93) on the same shelf. |
| A | warn | `choice_overload` | The assortment has 14 products (warn at 12, fail at 20). |
| A | warn | `gap:balloon-as-product` | A sunrise balloon is only an optional extra (about USD 450 on the Headout 2-day exclusions, about USD 420–540 on Viator and GetYourGuide). It is not its own bookable card in the captured list.
 No matching product was confirmed in this assortment. Competitors also sell the balloon as an add-on. This is a packaging note, not a unique Headout miss. |
| A | warn | `gap:conservancy-night-drive` | Microbrand copy describes private conservancies with fewer vehicles and, on some, night drives, bush walks, or off-road driving. No product title in the captured card list is a conservancy stay.
 No matching product was confirmed in this assortment. The format table is about the National Reserve and add-on parks, not conservancies. |
| A | warn | `price_ladder` | Fewer than half the products have a numeric price, so the ladder cannot be judged. |
| A | warn | `product_intent` | product 'e-57723' mean purchase intent is 3.11 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'e-57724' mean purchase intent is 3.11 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'mara-4d-nakuru' mean purchase intent is 3.23 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'mara-5d-lakes' mean purchase intent is 3.29 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'mara-6d-naivasha' mean purchase intent is 2.93 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'mara-6d-nakuru' mean purchase intent is 2.93 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'mara-fly-5' mean purchase intent is 2.82 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'mara-fly-5-amboseli' mean purchase intent is 2.82 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `relative_rank` | From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees is -1.13 standard deviations below this collection's mean purchase intent (2.93). This flag is relative. Absolute thresholds still need a CVR calibration. |
| A | warn | `relative_rank` | From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees is -1.13 standard deviations below this collection's mean purchase intent (2.93). This flag is relative. Absolute thresholds still need a CVR calibration. |
| B | warn | `faq_capture_unknown` | primary surface (headout.com) did not include an FAQ block in the capture. Absence is not confirmed. |
| B | warn | `faq_topics` | microbrand FAQs do not mention: cancellation, access. |
| B | warn | `microbrand_disclaimer` | The microbrand at https://www.masai-mara-safaris.com/ does not show a 'not the official venue or operator site' line. First-time visitors can read an attraction-branded domain as the operator. |
| B | warn | `page_intent` | page 'microbrand' mean purchase intent is 3.29 (pass ≥ 3.6, warn ≥ 3.2). |
| B | warn | `segment_page_intent` | page:microbrand by trip_type 'couple' mean purchase intent is 3.34 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by trip_type 'family_with_kids' mean purchase intent is 3.26 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by trip_type 'friends' mean purchase intent is 3.11 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by trip_type 'solo' mean purchase intent is 3.34 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by budget_tier 'budget' mean purchase intent is 3.05 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by budget_tier 'luxury' mean purchase intent is 3.18 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by budget_tier 'premium' mean purchase intent is 3.27 (pass ≥ 3.4, warn ≥ 2.8). |
| deterministic | warn | `duration_consistency` | From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees: duration statements differ by 3.5 hours (collection_card=17 hrs, product_itinerary=13–14 hours). |
| deterministic | pass | `currency_consistency` | No numeric prices were captured to compare. |
| deterministic | pass | `missing_duration` | Every product states duration. |
| deterministic | pass | `price_consistency` | No comparable price claims were captured, so nothing conflicted. |

## Page purchase intent (Gate B)

### primary: Experience the best of the Masai Mara from Nairobi

Page type: headout.com. URL: https://www.headout.com/masai-mara-c-7324/.

- All personas: mean **2.71** (n=30; 1=0.32, 2=0.09, 3=0.31, 4=0.14, 5=0.14)

By trip_type:

- family_with_kids: mean **2.74** (n=5; 1=0.32, 2=0.08, 3=0.30, 4=0.15, 5=0.15)
- couple: mean **2.69** (n=14; 1=0.32, 2=0.09, 3=0.30, 4=0.14, 5=0.14)
- friends: mean **2.64** (n=5; 1=0.33, 2=0.10, 3=0.31, 4=0.13, 5=0.13)
- solo: mean **2.79** (n=6; 1=0.30, 2=0.07, 3=0.32, 4=0.15, 5=0.16)

By budget_tier:

- budget: mean **2.51** (n=3; 1=0.35, 2=0.12, 3=0.30, 4=0.12, 5=0.11)
- luxury: mean **2.74** (n=10; 1=0.32, 2=0.08, 3=0.30, 4=0.14, 5=0.16)
- mid: mean **2.77** (n=6; 1=0.30, 2=0.09, 3=0.30, 4=0.16, 5=0.15)
- premium: mean **2.70** (n=11; 1=0.32, 2=0.09, 3=0.32, 4=0.14, 5=0.14)


### microbrand: Book Masai Mara Safaris

Page type: microbrand. URL: https://www.masai-mara-safaris.com/.

- All personas: mean **3.29** (n=30; 1=0.18, 2=0.05, 3=0.32, 4=0.21, 5=0.24)

By trip_type:

- family_with_kids: mean **3.26** (n=5; 1=0.17, 2=0.05, 3=0.36, 4=0.19, 5=0.23)
- couple: mean **3.34** (n=14; 1=0.18, 2=0.05, 3=0.29, 4=0.23, 5=0.26)
- friends: mean **3.11** (n=5; 1=0.20, 2=0.05, 3=0.39, 4=0.16, 5=0.20)
- solo: mean **3.34** (n=6; 1=0.16, 2=0.05, 3=0.33, 4=0.22, 5=0.24)

By budget_tier:

- budget: mean **3.05** (n=3; 1=0.22, 2=0.04, 3=0.39, 4=0.17, 5=0.18)
- luxury: mean **3.18** (n=10; 1=0.20, 2=0.06, 3=0.33, 4=0.18, 5=0.23)
- mid: mean **3.63** (n=6; 1=0.12, 2=0.04, 3=0.22, 4=0.31, 5=0.30)
- premium: mean **3.27** (n=11; 1=0.17, 2=0.05, 3=0.36, 4=0.18, 5=0.24)


## Product purchase intent (Gate A)

| Product | Mean PI | z vs collection | n | pmf 1–5 |
| --- | ---: | ---: | ---: | --- |
| From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees | 3.57 | +1.24 | 30 | 1:0.16 2:0.09 3:0.10 4:0.32 5:0.33 |
| From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees | 3.56 | +1.23 | 30 | 1:0.17 2:0.08 3:0.11 4:0.28 5:0.35 |
| From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees | 3.51 | +1.03 | 30 | 1:0.17 2:0.09 3:0.12 4:0.29 5:0.33 |
| From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees | 3.51 | +1.03 | 30 | 1:0.18 2:0.10 3:0.10 4:0.30 5:0.33 |
| From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha and Amboseli with Stays and Entry Fees | 3.44 | +0.76 | 30 | 1:0.16 2:0.09 3:0.19 4:0.26 5:0.30 |
| From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees | 3.44 | +0.76 | 30 | 1:0.18 2:0.10 3:0.14 4:0.26 5:0.32 |
| From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays and Entry Fees | 3.29 | +0.20 | 30 | 1:0.20 2:0.12 3:0.16 4:0.25 5:0.27 |
| From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees | 3.23 | -0.00 | 30 | 1:0.18 2:0.09 3:0.27 4:0.22 5:0.24 |
| From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 3.11 | -0.46 | 30 | 1:0.21 2:0.13 3:0.24 4:0.20 5:0.23 |
| From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 3.11 | -0.46 | 30 | 1:0.21 2:0.13 3:0.24 4:0.20 5:0.23 |
| From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees | 2.93 | -1.13 | 30 | 1:0.22 2:0.13 3:0.33 4:0.14 5:0.18 |
| From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees | 2.93 | -1.13 | 30 | 1:0.22 2:0.13 3:0.33 4:0.14 5:0.18 |
| From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 2.82 | -1.53 | 30 | 1:0.26 2:0.18 3:0.22 4:0.14 5:0.20 |
| From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees | 2.82 | -1.53 | 30 | 1:0.26 2:0.18 3:0.22 4:0.14 5:0.20 |

z is this product's mean minus the mean of product means in this run, divided by their standard deviation. Absolute pass lines are not calibrated to conversion. A negative z is a product this panel liked less than the rest of the collection, even when every mean sits in a narrow band.

## Top and bottom products by segment

### trip_type

- **family_with_kids** — top: From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.63); From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.61); From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees (3.61). Bottom, lowest first: From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (2.97); From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (3.18); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.18).
- **couple** — top: From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees (3.56); From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.51); From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.48). Bottom, lowest first: From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.72); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (2.72); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (2.77).
- **friends** — top: From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.52); From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.52); From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.52). Bottom, lowest first: From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.77); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (2.77); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (2.92).
- **solo** — top: From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.67); From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.67); From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees (3.67). Bottom, lowest first: From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.82); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (2.82); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (2.97).

### budget_tier

- **budget** — top: From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.57); From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees (3.44); From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.30). Bottom, lowest first: From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.57); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (2.57); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (2.57).
- **luxury** — top: From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees (3.63); From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha and Amboseli with Stays and Entry Fees (3.63); From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.55). Bottom, lowest first: From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (3.07); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.07); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (3.07).
- **mid** — top: From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.63); From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.56); From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.56). Bottom, lowest first: From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.62); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (2.62); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (2.73).
- **premium** — top: From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.61); From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees (3.60); From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha and Amboseli with Stays and Entry Fees (3.60). Bottom, lowest first: From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (2.78); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (2.78); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (3.01).

## Sample persona quotes

These quotes were written by the mock template, not by Claude.

- **p0001** on Experience the best of the Masai Mara from Nairobi (mean PI 2.39, mock-template): 25-34 family with kids from United Kingdom, budget budget, first timer, planning months 1 3, via mobile_web; interests: photography, big_five
  > I might book this later, but I am not sure. I might book this or an alternative; I cannot tell yet. Looking at Experience the best of the Masai Mara from Nairobi, I still have practical questions the page does not answer. I am a 25-34 traveler from United Kingdom on a family with kids trip, budget budget, first timer.

- **p0002** on Experience the best of the Masai Mara from Nairobi (mean PI 2.39, mock-template): 25-34 couple from United States, luxury budget, first timer, planning weeks 1 4, via mobile_web; interests: balloon, photography
  > I might book this later, but I am not sure. I might book this or an alternative; I cannot tell yet. Looking at Experience the best of the Masai Mara from Nairobi, I still have practical questions the page does not answer. I am a 25-34 traveler from United States on a couple trip, luxury budget, first timer.

- **p0029** on Book Masai Mara Safaris (mean PI 3.84, mock-template): 35-44 couple from Germany, luxury budget, repeat, planning months 1 3, via app, accessibility: mobility; interests: great_migration, maasai_culture
  > I would likely book this. This fits my trip well. Looking at Book Masai Mara Safaris, the page answers practical questions. I am a 35-44 traveler from Germany on a couple trip, luxury budget, repeat.

- **p0014** on Book Masai Mara Safaris (mean PI 3.85, mock-template): 25-34 solo from United States, mid budget, repeat, planning last minute, via mobile_web; interests: big_five, photography
  > I would choose this over the alternatives I have seen. I would likely book this. Looking at Book Masai Mara Safaris, the page answers practical questions. I am a 25-34 traveler from United States on a solo trip, mid budget, repeat.

- **p0003** on From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (mean PI 2.13, mock-template): 18-24 friends from China, mid budget, first timer, planning weeks 1 4, via mobile_web; interests: birding, big_five
  > This does not fit my trip at all. This is not worth booking at this price. Looking at From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees, I cannot see a clear price, so I hesitate. I am a 18-24 traveler from China on a friends trip, mid budget, first timer.

- **p0015** on From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees (mean PI 3.73, mock-template): 25-34 friends from United Kingdom, luxury budget, first timer, planning months 1 3, via mobile_web; interests: big_five, photography
  > I would book this for my upcoming trip. I would choose this over the alternatives I have seen. Looking at From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees, I cannot see a clear price, so I hesitate. I am a 25-34 traveler from United Kingdom on a friends trip, luxury budget, first timer.

## Unknowns in the source capture

- No numeric Headout from-price was captured for these Mara products. Do not treat competitor USD prices as Headout prices.
- api-ho.headout.com returned HTTP 403, so collection size, currency, and persona tags from the API are unknown.
- Several microbrand cards (4-day Nakuru, 5-day fly-in, both 6-day trips, 5-day lakes) were not opened as product pages. Their URLs, cancellation, and real inclusions are unknown. Title words were not upgraded into a full fact sheet except where noted.
- Whether every card on the microbrand is also on collection 7324 is unknown. The collection fetch was truncated. The 7-day trip has its own collection id 7723.
- A related Headout listing, e-56385, shows KSh 73,000 and excludes park fees (USD 100/day Jan–Jun, USD 200/day Jul–Dec). Its URL is under /day-trips/, and it was not confirmed on collection 7324 or the microbrand card list, so it is not in this assortment.
- Homepage footer legal block (address on the homepage itself, not only /legal/) was not confirmed in the extract.
- KSh amounts on the fly-in page were attached to other Nairobi cards in that render and are not used.
- Cancellation cutoffs are unknown except the 2-day product, which says 3 days.

## Sources

- 2026-11-26: Headout collection hero and first cards — https://www.headout.com/masai-mara-c-7324/
- 2026-11-26: Headout microbrand homepage, format table, FAQs, card titles and ratings — https://www.masai-mara-safaris.com/
- 2026-11-26: Fly-in explainer. Crafted by Headout line. KSh prices on that page were for other Nairobi cards, not copied onto Mara products. — https://www.masai-mara-safaris.com/fly-in-tours/
- 2026-11-26: Headout Inc. legal entity — https://www.masai-mara-safaris.com/legal/
- 2026-11-26: Private day trip product page — https://www.headout.com/masai-mara/from-nairobi-private-day-trip-masai-mara-reserve-e-57711/
- 2026-11-26: 2-day safari product page — https://www.headout.com/masai-mara/from-nairobi-2-day-masai-mara-safari-e-57793/
- 2026-11-26: 3-day road safari product page — https://www.headout.com/masai-mara/from-nairobi-3-day-masai-mara-safari-with-stays-and-entry-fees-e-57795/
- 2026-11-26: 3-day fly-in product page — https://www.headout.com/masai-mara/from-nairobi-fly-in-3-day-masai-mara-private-safari-e-57723/
- 2026-11-26: 4-day Mara safari product page — https://www.headout.com/masai-mara/from-nairobi-4-day-masai-mara-safari-masai-village-visit-e-57697/
- 2026-11-26: 4-day fly-in product page — https://www.headout.com/masai-mara/from-nairobi-fly-in-4-day-masai-mara-private-safari-e-57724/
- 2026-11-26: 7-day Kenya safari collection — https://www.headout.com/masai-mara-7-day-trip-c-7723/
- 2026-11-26: Viator budget 3-day, park fees excluded — https://www.viator.com/tours/Nairobi/3-DAYS-2-NIGHTS-BUDGET-GROUP-SAFARI-TO-MAASAI-MARA-NATIONAL-RESERVE/d5280-60115P2
- 2026-11-26: Viator 3-day, seasonal park-fee add-on — https://www.viator.com/tours/Nairobi/2-nights-Safari-Tour-Maasai-Mara/d5280-15254P2
- 2026-11-26: GetYourGuide 3-day from USD 295 — https://www.getyourguide.com/nairobi-l267/3days-gamedrive-safari-in-masai-mara-on-4x4-landcruiser-jeep-t679185/
- 2026-11-26: GetYourGuide 3-day from USD 390 with entry fees — https://www.getyourguide.com/nairobi-l267/from-nairobi-3-days-masai-mara-national-reserve-safari-t396317/

## Thresholds

Absolute cuts are not calibrated to Headout CVR. A live Sonnet 5.5 pilot (seed 7, 30 personas) compressed product means into about 3.17–3.46, so these pass lines mostly warn. Use z_vs_collection and relative_rank until a backtest replaces the cuts. See anchors.CALIBRATION_PLAN.

- page_mean_pass: 3.6
- page_mean_warn: 3.2
- segment_mean_pass: 3.4
- segment_mean_warn: 2.8
- product_mean_pass: 3.3
- product_mean_warn: 2.6
- cannibal_pi_delta: 0.25
- relative_z_warn: -1.0
- relative_z_fail: -1.5
- compression_range: 0.4
- absolute_thresholds_calibrated: False

Calibration against live CVR is not done in this scorecard. Shadow the next MMP and compare product rank to realized conversion before these pass/warn/fail cuts become a gate.
