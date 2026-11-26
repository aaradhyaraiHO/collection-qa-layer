# Collection QA scorecard: Milford Sound cruises

> **MOCK OUTPUT. Reactions are deterministic templates, not Claude. Embeddings are lexical-bow, not a judgment of real travelers. Do not use these scores as market research or as a go-live decision.**

- Collection id: `milford-sound-cruises`
- CE / collection id on Headout: `3945`
- Destination: Milford Sound, Fiordland, New Zealand
- Provenance: **live_headout**. Live headout.com collection, not a competitor-built proposal. Prices are the "from" figures rendered on the public pages listed below. The product-card API returned HTTP 403 from this environment, so nothing here came from api-ho.headout.com.

- Source pages fetched: 2026-11-26
- Scorecard generated: 2026-11-26T21:33:24.234598+00:00

## Method

Semantic Similarity Rating (arXiv 2510.08338): free-text booking intent, embedded with `lexical-bow`, cosine similarity to 6 sets of travel Likert anchors, minimum-similarity subtraction (epsilon=0.0, temperature=1.0), then the per-set distributions are averaged.

Panel: 30 personas, seed 20261126, profile weights are assumptions. Model `claude-sonnet-5-5`, 1 completion(s) per prompt. LLM calls made: 300. Cache hits: 0.

Assumption, not measured Headout demand. Replace with booking-mix weights before a segment gap is used as a go-live gate. Axes are sampled independently; real travelers are correlated.

## Cost

Cost (pre-run estimate, published price)
  model: claude-sonnet-5-5
  calls: 300
  input tokens: 157248
  output tokens: 20789
  rates: $2.0/MTok in, $10.0/MTok out
  estimated USD: $0.5224
MOCK run. Token counts are length estimates of template prompts. USD applies the published rate to those estimates so you can see what a live run of this size would cost. No API call was made.

## Gate results

| Gate | Severity | Code | Finding |
| --- | --- | --- | --- |
| A | warn | `cannibalisation` | Milford Sound Boutique Small-Boat Cruise and Milford Sound Cruise by RealNZ share a shelf and their prices differ by only 0.0%. |
| A | warn | `cannibalisation_intent` | Milford Sound Boutique Small-Boat Cruise and Milford Sound Cruise by RealNZ draw almost the same purchase intent (means 3.63 vs 3.73) on the same shelf. |
| A | warn | `gap:named-operator-on-lead-card` | The first collection card (optional lunch) and the boutique small-boat card do not name the boat operator, while RealNZ, Pure Milford, and Southern Discoveries are named elsewhere.
 No matching product was confirmed in this assortment. Treated as a merchandising gap, not a missing tour. |
| A | warn | `gap:overnight-cruise` | The collection long-form describes an overnight Milford cruise (about 18–24 hours) and RealNZ sells an overnight cruise from NZ$799, but no bookable overnight product with a price was in the captured cards.
 No matching product was confirmed in this assortment. The long-form is educational copy, not a product card. |
| A | warn | `product_intent` | product 'milford-fly-cruise' mean purchase intent is 2.96 (pass ≥ 3.3, warn ≥ 2.6). |
| deterministic | warn | `missing_cancellation` | 1 of 9 products is missing cancellation. |
| deterministic | warn | `missing_pickup` | 1 of 9 products is missing pickup. |
| deterministic | warn | `price_consistency` | Milford Sound Cruise with Optional Lunch: from prices in NZD differ by 8.2% across sections (collection_card=143.2, product_page=155). |
| A | pass | `choice_overload` | The assortment has 9 products (warn at 12, fail at 20). |
| A | pass | `price_ladder` | budget (NZD 0–180) has 3 product(s). |
| A | pass | `price_ladder` | mid (NZD 180–350) has 2 product(s). |
| A | pass | `price_ladder` | premium (NZD 350–700) has 1 product(s). |
| A | pass | `price_ladder` | luxury (NZD 700–100000) has 1 product(s). |
| B | pass | `faq_topics` | primary FAQs cover cancellation, getting there, and access. |
| deterministic | pass | `currency_consistency` | Prices that were captured use a single currency. |
| deterministic | pass | `missing_duration` | Every product states duration. |
| deterministic | pass | `price_consistency` | From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers: from prices in NZD differ by 1.1% across sections (collection_card=207.2, product_page=205). |

## Page purchase intent (Gate B)

### primary: Experience the best cruises in Milford Sound

Page type: headout.com. URL: https://www.headout.com/milford-sound-cruise-tickets-c-3945/.

- All personas: mean **3.68** (n=30; 1=0.17, 2=0.07, 3=0.02, 4=0.41, 5=0.33)

By trip_type:

- family_with_kids: mean **3.67** (n=6; 1=0.16, 2=0.07, 3=0.02, 4=0.41, 5=0.34)
- friends: mean **3.61** (n=9; 1=0.17, 2=0.09, 3=0.02, 4=0.39, 5=0.33)
- couple: mean **3.73** (n=13; 1=0.16, 2=0.06, 3=0.01, 4=0.44, 5=0.33)
- solo: mean **3.67** (n=2; 1=0.19, 2=0.06, 3=0.02, 4=0.37, 5=0.36)

By budget_tier:

- budget: mean **3.72** (n=8; 1=0.15, 2=0.07, 3=0.01, 4=0.45, 5=0.32)
- premium: mean **3.68** (n=8; 1=0.17, 2=0.07, 3=0.02, 4=0.41, 5=0.33)
- mid: mean **3.64** (n=11; 1=0.17, 2=0.08, 3=0.02, 4=0.40, 5=0.33)
- luxury: mean **3.69** (n=3; 1=0.19, 2=0.05, 3=0.02, 4=0.36, 5=0.38)


## Product purchase intent (Gate A)

| Product | Mean PI | n | pmf 1–5 |
| --- | ---: | ---: | --- |
| From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers | 3.73 | 30 | 1:0.16 2:0.07 3:0.07 4:0.27 5:0.43 |
| From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers | 3.73 | 30 | 1:0.16 2:0.07 3:0.07 4:0.27 5:0.43 |
| Milford Sound Cruise with Optional Lunch | 3.73 | 30 | 1:0.17 2:0.07 3:0.07 4:0.26 5:0.43 |
| Milford Sound Cruise by RealNZ | 3.73 | 30 | 1:0.17 2:0.07 3:0.07 4:0.26 5:0.43 |
| Milford Sound Boutique Small-Boat Cruise | 3.63 | 30 | 1:0.17 2:0.09 3:0.06 4:0.32 5:0.37 |
| Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine | 3.60 | 30 | 1:0.16 2:0.08 3:0.11 4:0.28 5:0.36 |
| Milford Sound Nature Cruise | 3.53 | 30 | 1:0.17 2:0.09 3:0.11 4:0.31 5:0.32 |
| From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford | 3.53 | 30 | 1:0.16 2:0.07 3:0.17 4:0.25 5:0.34 |
| From Queenstown: Milford Sound Scenic Flyover and Cruise | 2.96 | 30 | 1:0.23 2:0.21 3:0.16 4:0.18 5:0.22 |

## Top and bottom products by segment

### trip_type

- **family_with_kids** — top: Milford Sound Cruise with Optional Lunch (3.78); Milford Sound Cruise by RealNZ (3.78); From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers (3.72). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (2.96); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.45); Milford Sound Nature Cruise (3.55).
- **friends** — top: Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.67); From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers (3.66); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.66). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (2.92); Milford Sound Nature Cruise (3.41); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.43).
- **couple** — top: From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers (3.77); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.77); Milford Sound Cruise with Optional Lunch (3.77). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (3.00); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.56); Milford Sound Nature Cruise (3.59).
- **solo** — top: From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers (3.83); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.83); Milford Sound Cruise with Optional Lunch (3.82). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (2.86); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.62); Milford Sound Nature Cruise (3.66).

### budget_tier

- **budget** — top: Milford Sound Cruise with Optional Lunch (3.79); Milford Sound Cruise by RealNZ (3.79); Milford Sound Boutique Small-Boat Cruise (3.72). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (2.89); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.19); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.47).
- **premium** — top: From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers (3.80); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.80); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.80). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (2.99); Milford Sound Nature Cruise (3.53); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.59).
- **mid** — top: From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers (3.79); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.79); Milford Sound Cruise with Optional Lunch (3.79). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (2.84); Milford Sound Nature Cruise (3.53); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.64).
- **luxury** — top: Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.76); From Queenstown: Milford Sound Scenic Flyover and Cruise (3.51); From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers (3.44). Bottom, lowest first: From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.11); Milford Sound Boutique Small-Boat Cruise (3.18); Milford Sound Nature Cruise (3.39).

## Sample persona quotes

These quotes were written by the mock template, not by Claude.

- **p0003** on Experience the best cruises in Milford Sound (mean PI 3.47, mock-template): 55-64 couple from New Zealand, mid budget, first timer, planning weeks 1 4, via mobile_web; interests: photography, scenery
  > This fits my trip well. This looks like fair value and I would consider booking. Looking at Experience the best cruises in Milford Sound, the page answers practical questions. I am a 55-64 traveler from New Zealand on a couple trip, mid budget, first timer.

- **p0004** on Experience the best cruises in Milford Sound (mean PI 3.47, mock-template): 25-34 friends from Australia, mid budget, first timer, planning months 3 plus, via app; interests: photography, hiking
  > This fits my trip well. This looks like fair value and I would consider booking. Looking at Experience the best cruises in Milford Sound, the page answers practical questions. I am a 25-34 traveler from Australia on a friends trip, mid budget, first timer.

- **p0006** on Experience the best cruises in Milford Sound (mean PI 3.83, mock-template): 45-54 couple from Australia, mid budget, first timer, planning months 1 3, via mobile_web; interests: wildlife, photography
  > I would book this for my upcoming trip. I would choose this over the alternatives I have seen. Looking at Experience the best cruises in Milford Sound, the page answers practical questions. I am a 45-54 traveler from Australia on a couple trip, mid budget, first timer.

- **p0015** on Experience the best cruises in Milford Sound (mean PI 3.83, mock-template): 55-64 family with kids from China, mid budget, first timer, planning months 1 3, via mobile_web; interests: photography, food_onboard
  > I would book this for my upcoming trip. I would choose this over the alternatives I have seen. Looking at Experience the best cruises in Milford Sound, the page answers practical questions. I am a 55-64 traveler from China on a family with kids trip, mid budget, first timer.

- **p0002** on From Queenstown: Milford Sound Scenic Flyover and Cruise (mean PI 2.46, mock-template): 35-44 friends from Germany, premium budget, first timer, planning weeks 1 4, via desktop; interests: wildlife, scenery
  > I might book this later, but I am not sure. I might book this or an alternative; I cannot tell yet. Looking at From Queenstown: Milford Sound Scenic Flyover and Cruise, it is a step more expensive than I expected. I am a 35-44 traveler from Germany on a friends trip, premium budget, first timer.

- **p0001** on From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (mean PI 3.86, mock-template): 18-24 family with kids from United Kingdom, budget budget, first timer, planning weeks 1 4, via mobile_web; interests: photography, wildlife
  > I would book this for my upcoming trip. I would choose this over the alternatives I have seen. Looking at From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers, it is a step more expensive than I expected. I am a 18-24 traveler from United Kingdom on a family with kids trip, budget budget, first timer.

## Unknowns in the source capture

- api-ho.headout.com collection and product-card endpoints returned HTTP 403, so catalog totals, persona tags, and a single currency from the API were not available.
- No Milford Sound microbrand (separate attraction domain operated by Headout) was identified. Gate B reseller-disclaimer checks do not apply to a second surface.
- Product URL, cancellation cutoff, and full inclusions for the fly-cruise card and the Pure Milford Queenstown card were not captured.
- Nature cruise price, rating, and confirmed operator were not on the fetched pages.
- Whether e-30130 is on collection 3945 or only in the same URL folder was not confirmed; the first collection extract did not list it.
- Collection-card review counts and product-page review counts drifted by a few reviews in the same fetch. The spec keeps the product-page count when both existed.
- Viator prices are USD and are context only.
- Accessibility is discussed in the collection FAQ, but individual product cards that were opened did not repeat wheelchair access, so accessibility_noted is false at product level.

## Sources

- 2026-11-26: Headout collection page, hero, cards, long-form, FAQs — https://www.headout.com/milford-sound-cruise-tickets-c-3945/
- 2026-11-26: Optional-lunch cruise product page — https://www.headout.com/milford-sound-cruise-tickets/milford-sound-cruise-e-29695/
- 2026-11-26: Boutique small-boat product page — https://www.headout.com/milford-sound-cruise-tickets/small-group-guided-tour-milford-sound-cruise-e-18125/
- 2026-11-26: RealNZ cruise product page — https://www.headout.com/milford-sound-cruise-tickets/milford-sound-cruise-by-realnz-e-37309/
- 2026-11-26: RealNZ collection card showing from NZ$155 — https://www.headout.com/realnz-c-7688/
- 2026-11-26: Nature cruise product page — https://www.headout.com/milford-sound-cruise-tickets/milford-sound-nature-cruise-with-cascade-lounge-e-40298/
- 2026-11-26: Queenstown day trip product page — https://www.headout.com/milford-sound-cruise-tickets/full-day-tour-of-milford-sound-with-cruise-lunch-return-transfers-e-23887/
- 2026-11-26: Te Anau day trip product page — https://www.headout.com/milford-sound-cruise-tickets/day-tour-from-te-anau-to-milford-sound-including-a-cruise-e-18103/
- 2026-11-26: Ultra-premium cruise product page — https://www.headout.com/milford-sound-cruise-tickets/premium-milford-sound-cruise-with-gourmet-canapes-champagne-e-30130/
- 2026-11-26: Operator price comparison dated 10 November 2026 — https://www.realnz.com/en/blog/milford-sound-cruise-comparison/
- 2026-11-26: Third-party operator price roundup, prices marked October 2026 — https://milfordsoundtravel.com/things-to-do-in-milford-sound/best-milford-sound-cruises/
- 2026-11-26: Viator cruise category, USD from-prices — https://www.viator.com/Fiordland-and-Milford-Sound-tours/Cruises-Sailing-and-Water-Tours/d756-g3

## Thresholds

Uncalibrated assumptions. See anchors.CALIBRATION_PLAN.

- page_mean_pass: 3.6
- page_mean_warn: 3.2
- segment_mean_pass: 3.4
- segment_mean_warn: 2.8
- product_mean_pass: 3.3
- product_mean_warn: 2.6
- cannibal_pi_delta: 0.25

Calibration against live CVR is not done in this scorecard. Shadow the next MMP and compare product rank to realized conversion before these pass/warn/fail cuts become a gate.
