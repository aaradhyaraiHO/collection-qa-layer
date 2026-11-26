# Collection QA scorecard: Milford Sound cruises

- Collection id: `milford-sound-cruises`
- CE / collection id on Headout: `3945`
- Destination: Milford Sound, Fiordland, New Zealand
- Provenance: **live_headout**. Live headout.com collection, not a competitor-built proposal. Prices are the "from" figures rendered on the public pages listed below. The product-card API returned HTTP 403 from this environment, so nothing here came from api-ho.headout.com.

- Source pages fetched: 2026-11-26
- Scorecard generated: 2026-11-26T21:54:15.381104+00:00

## Method

Semantic Similarity Rating (arXiv 2510.08338): free-text booking intent, embedded with `sentence-transformers:sentence-transformers/all-MiniLM-L6-v2`, cosine similarity to 6 sets of travel Likert anchors, minimum-similarity subtraction (epsilon=0.0, temperature=1.0), then the per-set distributions are averaged.

Panel: 30 personas, seed 7, profile weights are assumptions. Model `claude-sonnet-5-5`, 1 completion(s) per prompt. LLM calls made: 300. Cache hits: 0.

Assumption, not measured Headout demand. Replace with booking-mix weights before a segment gap is used as a go-live gate. Axes are sampled independently; real travelers are correlated.

## Cost

Cost (actual API usage, published price)
  model: claude-sonnet-5-5
  calls: 300
  input tokens: 238080
  output tokens: 79095
  rates: $2.0/MTok in, $10.0/MTok out
  estimated USD: $1.2671
Live Anthropic usage.

## Gate results

| Gate | Severity | Code | Finding |
| --- | --- | --- | --- |
| A | warn | `cannibalisation` | Milford Sound Boutique Small-Boat Cruise and Milford Sound Cruise by RealNZ share a shelf and their prices differ by only 0.0%. |
| A | warn | `cannibalisation_intent` | Milford Sound Boutique Small-Boat Cruise and Milford Sound Cruise by RealNZ draw almost the same purchase intent (means 3.46 vs 3.43) on the same shelf. |
| A | warn | `gap:named-operator-on-lead-card` | The first collection card (optional lunch) and the boutique small-boat card do not name the boat operator, while RealNZ, Pure Milford, and Southern Discoveries are named elsewhere.
 No matching product was confirmed in this assortment. Treated as a merchandising gap, not a missing tour. |
| A | warn | `gap:overnight-cruise` | The collection long-form describes an overnight Milford cruise (about 18–24 hours) and RealNZ sells an overnight cruise from NZ$799, but no bookable overnight product with a price was in the captured cards.
 No matching product was confirmed in this assortment. The long-form is educational copy, not a product card. |
| A | warn | `product_intent` | product 'milford-fly-cruise' mean purchase intent is 3.21 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'milford-pure-queenstown' mean purchase intent is 3.27 (pass ≥ 3.3, warn ≥ 2.6). |
| B | warn | `page_intent` | page 'primary' mean purchase intent is 3.32 (pass ≥ 3.6, warn ≥ 3.2). |
| B | warn | `segment_page_intent` | page:primary by trip_type 'couple' mean purchase intent is 3.33 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by trip_type 'family_with_kids' mean purchase intent is 3.31 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by trip_type 'friends' mean purchase intent is 3.31 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by trip_type 'solo' mean purchase intent is 3.31 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by budget_tier 'budget' mean purchase intent is 3.37 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by budget_tier 'luxury' mean purchase intent is 3.19 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by budget_tier 'mid' mean purchase intent is 3.32 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by budget_tier 'premium' mean purchase intent is 3.36 (pass ≥ 3.4, warn ≥ 2.8). |
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

- All personas: mean **3.32** (n=30; 1=0.16, 2=0.14, 3=0.22, 4=0.20, 5=0.29)

By trip_type:

- family_with_kids: mean **3.31** (n=6; 1=0.15, 2=0.15, 3=0.22, 4=0.21, 5=0.27)
- couple: mean **3.33** (n=11; 1=0.16, 2=0.13, 3=0.22, 4=0.20, 5=0.29)
- friends: mean **3.31** (n=7; 1=0.16, 2=0.14, 3=0.21, 4=0.20, 5=0.29)
- solo: mean **3.31** (n=6; 1=0.16, 2=0.13, 3=0.23, 4=0.19, 5=0.29)

By budget_tier:

- budget: mean **3.37** (n=4; 1=0.13, 2=0.15, 3=0.21, 4=0.23, 5=0.28)
- premium: mean **3.36** (n=9; 1=0.15, 2=0.13, 3=0.21, 4=0.21, 5=0.29)
- mid: mean **3.32** (n=12; 1=0.16, 2=0.14, 3=0.22, 4=0.19, 5=0.29)
- luxury: mean **3.19** (n=5; 1=0.20, 2=0.12, 3=0.23, 4=0.18, 5=0.27)


## Product purchase intent (Gate A)

| Product | Mean PI | n | pmf 1–5 |
| --- | ---: | ---: | --- |
| Milford Sound Boutique Small-Boat Cruise | 3.46 | 30 | 1:0.12 2:0.13 3:0.20 4:0.28 5:0.27 |
| Milford Sound Cruise by RealNZ | 3.43 | 30 | 1:0.11 2:0.16 3:0.20 4:0.25 5:0.28 |
| Milford Sound Cruise with Optional Lunch | 3.42 | 30 | 1:0.12 2:0.13 3:0.24 4:0.23 5:0.28 |
| Milford Sound Nature Cruise | 3.40 | 30 | 1:0.12 2:0.14 3:0.23 4:0.24 5:0.27 |
| From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers | 3.40 | 30 | 1:0.14 2:0.10 3:0.25 4:0.24 5:0.27 |
| From Te Anau: Milford Sound Day Trip with Cruise and Return Transfers | 3.37 | 30 | 1:0.14 2:0.12 3:0.26 4:0.21 5:0.27 |
| Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine | 3.30 | 30 | 1:0.14 2:0.15 3:0.23 4:0.22 5:0.26 |
| From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford | 3.27 | 30 | 1:0.16 2:0.17 3:0.20 4:0.21 5:0.27 |
| From Queenstown: Milford Sound Scenic Flyover and Cruise | 3.21 | 30 | 1:0.18 2:0.15 3:0.21 4:0.21 5:0.25 |

## Top and bottom products by segment

### trip_type

- **family_with_kids** — top: Milford Sound Boutique Small-Boat Cruise (3.47); Milford Sound Cruise with Optional Lunch (3.42); Milford Sound Cruise by RealNZ (3.41). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (3.12); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.25); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.31).
- **couple** — top: Milford Sound Boutique Small-Boat Cruise (3.49); Milford Sound Cruise by RealNZ (3.45); Milford Sound Cruise with Optional Lunch (3.44). Bottom, lowest first: From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.27); From Queenstown: Milford Sound Scenic Flyover and Cruise (3.28); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.31).
- **friends** — top: Milford Sound Boutique Small-Boat Cruise (3.52); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.44); Milford Sound Cruise with Optional Lunch (3.38). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (3.18); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.28); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.30).
- **solo** — top: Milford Sound Nature Cruise (3.48); Milford Sound Cruise by RealNZ (3.46); Milford Sound Cruise with Optional Lunch (3.42). Bottom, lowest first: From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.17); From Queenstown: Milford Sound Scenic Flyover and Cruise (3.18); Milford Sound Boutique Small-Boat Cruise (3.30).

### budget_tier

- **budget** — top: Milford Sound Boutique Small-Boat Cruise (3.44); Milford Sound Nature Cruise (3.40); Milford Sound Cruise with Optional Lunch (3.39). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (3.16); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.21); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.33).
- **premium** — top: Milford Sound Boutique Small-Boat Cruise (3.51); Milford Sound Cruise by RealNZ (3.45); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.38). Bottom, lowest first: From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.23); From Queenstown: Milford Sound Scenic Flyover and Cruise (3.29); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.35).
- **mid** — top: Milford Sound Cruise with Optional Lunch (3.48); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.46); Milford Sound Nature Cruise (3.45). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (3.21); Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.24); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.26).
- **luxury** — top: Milford Sound Ultra Premium Cruise with Gourmet Meal, Reserved Seating, and Sparkling Wine (3.43); Milford Sound Boutique Small-Boat Cruise (3.43); Milford Sound Cruise with Optional Lunch (3.41). Bottom, lowest first: From Queenstown: Milford Sound Scenic Flyover and Cruise (3.09); From Queenstown: Milford Sound Day Tour with Scenic Cruise and Lunch by Pure Milford (3.29); From Queenstown: Milford Sound Day Trip with Cruise and Return Transfers (3.30).

## Sample persona quotes

- **p0016** on Experience the best cruises in Milford Sound (mean PI 3.01, anthropic): 25-34 solo from Germany, luxury budget, first timer, planning months 1 3, via app; interests: scenery, hiking
  > Fairly likely, and I'd probably go for the fly-and-cruise or the Ultra Premium cruise with the gourmet meal and reserved seating. Since I'm a first-timer and travelling solo on a luxury budget, I like that the page spells out the boarding point and has a compare block for the cruise types, and the 4.8 from over 6,000 travellers plus the free cancellation and guarantees make me comfortable booking in the app. What holds me back is that it's a marketplace with no clear statement of who actually runs the cruise. Several listings also don't show a price, and the weather cancellation policy is vague. I'd want to check that the product page spells out the refund terms and the exact departure time before I pay, because I don't want to lose a flight-based day to fog or cloud.

- **p0026** on Experience the best cruises in Milford Sound (mean PI 3.02, anthropic): 35-44 family with kids from United Kingdom, budget budget, first timer, planning weeks 1 4, via mobile_web; interests: short_on_time, scenery
  > As a budget family of four doing this for the first time, I like the 4.8 rating from over 6,000 people and the free cancellation. The cruise-only options at 155–179 NZD look doable, and it's reassuring that cruises usually run in the rain and strollers are allowed. What would stop me is the cost per person adding up, and I can't tell whether kids get a discount. The Queenstown day trip at 309 NZD each is a 12-13 hour day with little ones, and I'm not sure if we'd drive ourselves. I'd probably go further down the page to check child pricing and the transport, so I'm leaning towards booking but won't do it straight away on my phone.

- **p0020** on Experience the best cruises in Milford Sound (mean PI 3.56, anthropic): 25-34 couple from Australia, budget budget, repeat, planning months 1 3, via desktop; interests: wildlife, short_on_time
  > I'd probably book from here, since I've done Milford before and I'm mostly after the Nature Cruise for the seals and the odd penguin or dolphin. The 4.8 from over 6,000 reviews, the 24-hour free cancellation and the clear boarding point all help, and the 155 NZD cruise-only option works for a budget couple. What holds me back is that the Nature Cruise has no price showing, and I can't tell from this page who actually runs it, since it's a Headout marketplace listing and not the operator's own site. I'd open the operator's own site in another tab to compare prices, and then book here only if it's about the same. We're short on time, so I'd also want to know the drive from Queenstown fits the schedule before I commit.

- **p0021** on Experience the best cruises in Milford Sound (mean PI 3.57, anthropic): 45-54 friends from Australia, premium budget, first timer, planning months 1 3, via desktop; interests: short_on_time, photography
  > I'm fairly likely to book, probably within a few weeks. The fly-and-cruise from Queenstown at 835 NZD suits me best: I'm short on time and want photos from the air as well as from the water, and my friends and I are on a premium budget. The Ultra Premium cruise with reserved seating is my backup, since a good deck spot matters for photography. What would slow me down is that the page doesn't say whether Headout is an authorised reseller, and some prices aren't shown. I'd also want the weather cancellation and flyover refund terms spelled out before I pay, since a cloudy day would waste a lot of money.

- **p0005** on From Queenstown: Milford Sound Scenic Flyover and Cruise (mean PI 2.77, anthropic): 25-34 friends from United Kingdom, mid budget, first timer, planning weeks 1 4, via mobile_web; interests: weather_comfort, hiking
  > Honestly, I'm leaning towards not booking it as it stands. The flyover plus a small boat sounds like a brilliant first-time way to see Milford Sound, and hotel pickup and window seats are a big plus, especially if the weather turns grumpy and I want the best view. But 835 NZD is roughly £400 each, which is a stretch on a mid budget with friends. The listing doesn't name the operator or give a cancellation policy, and I've no idea what happens if the weather grounds the flight. The duration range of 4.5 to 13 hours is also vague. I'd want those answers, pl

- **p0028** on Milford Sound Boutique Small-Boat Cruise (mean PI 3.69, anthropic): 35-44 family with kids from New Zealand, premium budget, first timer, planning months 3 plus, via mobile_web; interests: wildlife, hiking
  > I'm fairly interested, but I wouldn't book it yet. A small boat with a 75-passenger cap, close-up waterfalls, wildlife and a skipper who does commentary suits my kids and me, and the optional guided Milford Track walk is a nice bonus for a hiking family. Free cancellation up to 24 hours helps since I'm planning months out.

What holds me back is that the operator isn't named, so I can't tell which boat I'd actually be on. Pickup is also blank, and with kids I need to know how we get there from Te Anau or Queenstown, since that's a long day. A perfect 5.0 across 2,000+ reviews and a review count that doesn't match between pages make me want to check things on the operator's own site before paying 179 NZD each.

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
