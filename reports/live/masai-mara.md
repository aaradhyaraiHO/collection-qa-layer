# Collection QA scorecard: Masai Mara safaris

- Collection id: `masai-mara`
- CE / collection id on Headout: `7324`
- Destination: Masai Mara National Reserve, Kenya
- Provenance: **live_headout**. Live Headout collection plus the Headout-operated microbrand masai-mara-safaris.com. This is not a competitor-built proposal. Numeric "from" prices were not rendered for these safaris in the captures below (the public product-card API returned HTTP 403, and the HTML render did not include a currency amount for the Mara cards). Prices are left null on purpose.

- Source pages fetched: 2026-11-26
- Scorecard generated: 2026-11-26T21:50:31.782430+00:00

## Method

Semantic Similarity Rating (arXiv 2510.08338): free-text booking intent, embedded with `sentence-transformers:sentence-transformers/all-MiniLM-L6-v2`, cosine similarity to 6 sets of travel Likert anchors, minimum-similarity subtraction (epsilon=0.0, temperature=1.0), then the per-set distributions are averaged.

Panel: 30 personas, seed 7, profile weights are assumptions. Model `claude-sonnet-5-5`, 1 completion(s) per prompt. LLM calls made: 250. Cache hits: 230.

Assumption, not measured Headout demand. Replace with booking-mix weights before a segment gap is used as a go-live gate. Axes are sampled independently; real travelers are correlated.

## Cost

Cost (actual API usage, published price)
  model: claude-sonnet-5-5
  calls: 480
  input tokens: 364178
  output tokens: 114822
  rates: $2.0/MTok in, $10.0/MTok out
  estimated USD: $1.8766
Live Anthropic usage.

## Gate results

| Gate | Severity | Code | Finding |
| --- | --- | --- | --- |
| B | fail | `assertion:nakuru-on-4-day-plus` | The microbrand says Lake Nakuru National Park is included with 4+ day safaris. Mara-only itineraries of 4 and 5 days are on the same page.
 — 6 of 10 in-scope products do not mention nakuru. |
| deterministic | fail | `missing_cancellation` | 8 of 14 products are missing cancellation. |
| deterministic | fail | `missing_pickup` | 6 of 14 products are missing pickup. |
| A | warn | `cannibalisation_intent` | From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees and From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees draw almost the same purchase intent (means 3.38 vs 3.34) on the same shelf. |
| A | warn | `cannibalisation_intent` | From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees and From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees draw almost the same purchase intent (means 3.38 vs 3.43) on the same shelf. |
| A | warn | `cannibalisation_intent` | From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees and From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees draw almost the same purchase intent (means 3.34 vs 3.43) on the same shelf. |
| A | warn | `cannibalisation_intent` | From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees and From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees draw almost the same purchase intent (means 3.30 vs 3.34) on the same shelf. |
| A | warn | `cannibalisation_intent` | From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees and From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees draw almost the same purchase intent (means 3.38 vs 3.42) on the same shelf. |
| A | warn | `choice_overload` | The assortment has 14 products (warn at 12, fail at 20). |
| A | warn | `gap:balloon-as-product` | A sunrise balloon is only an optional extra (about USD 450 on the Headout 2-day exclusions, about USD 420–540 on Viator and GetYourGuide). It is not its own bookable card in the captured list.
 No matching product was confirmed in this assortment. Competitors also sell the balloon as an add-on. This is a packaging note, not a unique Headout miss. |
| A | warn | `gap:conservancy-night-drive` | Microbrand copy describes private conservancies with fewer vehicles and, on some, night drives, bush walks, or off-road driving. No product title in the captured card list is a conservancy stay.
 No matching product was confirmed in this assortment. The format table is about the National Reserve and add-on parks, not conservancies. |
| A | warn | `price_ladder` | Fewer than half the products have a numeric price, so the ladder cannot be judged. |
| A | warn | `product_intent` | product 'e-57711' mean purchase intent is 3.17 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'e-57793' mean purchase intent is 3.25 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'e-57795' mean purchase intent is 3.29 (pass ≥ 3.3, warn ≥ 2.6). |
| A | warn | `product_intent` | product 'mara-fly-5' mean purchase intent is 3.30 (pass ≥ 3.3, warn ≥ 2.6). |
| B | warn | `faq_capture_unknown` | primary surface (headout.com) did not include an FAQ block in the capture. Absence is not confirmed. |
| B | warn | `faq_topics` | microbrand FAQs do not mention: cancellation, access. |
| B | warn | `microbrand_disclaimer` | The microbrand at https://www.masai-mara-safaris.com/ does not show a 'not the official venue or operator site' line. First-time visitors can read an attraction-branded domain as the operator. |
| B | warn | `page_intent` | page 'microbrand' mean purchase intent is 3.39 (pass ≥ 3.6, warn ≥ 3.2). |
| B | warn | `page_intent` | page 'primary' mean purchase intent is 3.37 (pass ≥ 3.6, warn ≥ 3.2). |
| B | warn | `segment_page_intent` | page:primary by trip_type 'couple' mean purchase intent is 3.36 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by trip_type 'family_with_kids' mean purchase intent is 3.37 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by trip_type 'friends' mean purchase intent is 3.36 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by trip_type 'solo' mean purchase intent is 3.38 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by budget_tier 'luxury' mean purchase intent is 3.33 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by budget_tier 'mid' mean purchase intent is 3.40 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:primary by budget_tier 'premium' mean purchase intent is 3.36 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by trip_type 'family_with_kids' mean purchase intent is 3.38 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by trip_type 'friends' mean purchase intent is 3.37 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by trip_type 'solo' mean purchase intent is 3.35 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by budget_tier 'luxury' mean purchase intent is 3.36 (pass ≥ 3.4, warn ≥ 2.8). |
| B | warn | `segment_page_intent` | page:microbrand by budget_tier 'premium' mean purchase intent is 3.34 (pass ≥ 3.4, warn ≥ 2.8). |
| deterministic | warn | `duration_consistency` | From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees: duration statements differ by 3.5 hours (collection_card=17 hrs, product_itinerary=13–14 hours). |
| deterministic | pass | `currency_consistency` | No numeric prices were captured to compare. |
| deterministic | pass | `missing_duration` | Every product states duration. |
| deterministic | pass | `price_consistency` | No comparable price claims were captured, so nothing conflicted. |

## Page purchase intent (Gate B)

### primary: Experience the best of the Masai Mara from Nairobi

Page type: headout.com. URL: https://www.headout.com/masai-mara-c-7324/.

- All personas: mean **3.37** (n=30; 1=0.12, 2=0.14, 3=0.25, 4=0.23, 5=0.26)

By trip_type:

- family_with_kids: mean **3.37** (n=5; 1=0.12, 2=0.15, 3=0.24, 4=0.23, 5=0.26)
- couple: mean **3.36** (n=14; 1=0.13, 2=0.14, 3=0.24, 4=0.23, 5=0.26)
- friends: mean **3.36** (n=5; 1=0.12, 2=0.14, 3=0.26, 4=0.23, 5=0.25)
- solo: mean **3.38** (n=6; 1=0.12, 2=0.13, 3=0.26, 4=0.23, 5=0.26)

By budget_tier:

- budget: mean **3.43** (n=3; 1=0.10, 2=0.15, 3=0.24, 4=0.25, 5=0.27)
- luxury: mean **3.33** (n=10; 1=0.13, 2=0.14, 3=0.25, 4=0.23, 5=0.25)
- mid: mean **3.40** (n=6; 1=0.12, 2=0.14, 3=0.24, 4=0.24, 5=0.27)
- premium: mean **3.36** (n=11; 1=0.12, 2=0.14, 3=0.26, 4=0.22, 5=0.26)


### microbrand: Book Masai Mara Safaris

Page type: microbrand. URL: https://www.masai-mara-safaris.com/.

- All personas: mean **3.39** (n=30; 1=0.12, 2=0.13, 3=0.24, 4=0.25, 5=0.26)

By trip_type:

- family_with_kids: mean **3.38** (n=5; 1=0.13, 2=0.13, 3=0.23, 4=0.26, 5=0.25)
- couple: mean **3.43** (n=14; 1=0.12, 2=0.12, 3=0.23, 4=0.26, 5=0.27)
- friends: mean **3.37** (n=5; 1=0.12, 2=0.12, 3=0.27, 4=0.23, 5=0.25)
- solo: mean **3.35** (n=6; 1=0.13, 2=0.14, 3=0.24, 4=0.24, 5=0.25)

By budget_tier:

- budget: mean **3.55** (n=3; 1=0.12, 2=0.08, 3=0.22, 4=0.30, 5=0.28)
- luxury: mean **3.36** (n=10; 1=0.13, 2=0.13, 3=0.23, 4=0.26, 5=0.25)
- mid: mean **3.48** (n=6; 1=0.11, 2=0.10, 3=0.25, 4=0.25, 5=0.28)
- premium: mean **3.34** (n=11; 1=0.13, 2=0.14, 3=0.24, 4=0.23, 5=0.25)


## Product purchase intent (Gate A)

| Product | Mean PI | n | pmf 1–5 |
| --- | ---: | ---: | --- |
| From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 3.44 | 30 | 1:0.11 2:0.14 3:0.22 4:0.25 5:0.28 |
| From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees | 3.43 | 30 | 1:0.12 2:0.13 3:0.23 4:0.26 5:0.27 |
| From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees | 3.42 | 30 | 1:0.11 2:0.13 3:0.25 4:0.25 5:0.26 |
| From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays and Entry Fees | 3.41 | 30 | 1:0.11 2:0.14 3:0.25 4:0.24 5:0.27 |
| From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees | 3.38 | 30 | 1:0.12 2:0.13 3:0.25 4:0.24 5:0.26 |
| From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees | 3.38 | 30 | 1:0.13 2:0.13 3:0.25 4:0.23 5:0.27 |
| From Nairobi: Fly-In 3-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 3.37 | 30 | 1:0.13 2:0.15 3:0.21 4:0.24 5:0.27 |
| From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees | 3.34 | 30 | 1:0.13 2:0.15 3:0.24 4:0.23 5:0.26 |
| From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees | 3.34 | 30 | 1:0.11 2:0.15 3:0.25 4:0.25 5:0.23 |
| From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha and Amboseli with Stays and Entry Fees | 3.32 | 30 | 1:0.13 2:0.16 3:0.24 4:0.22 5:0.26 |
| From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees | 3.30 | 30 | 1:0.14 2:0.15 3:0.22 4:0.23 5:0.25 |
| From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees | 3.29 | 30 | 1:0.14 2:0.15 3:0.23 4:0.24 5:0.24 |
| From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees | 3.25 | 30 | 1:0.16 2:0.14 3:0.24 4:0.21 5:0.25 |
| From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees | 3.17 | 30 | 1:0.17 2:0.18 3:0.21 4:0.19 5:0.25 |

## Top and bottom products by segment

### trip_type

- **family_with_kids** — top: From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha and Amboseli with Stays and Entry Fees (3.48); From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees (3.47); From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees (3.41). Bottom, lowest first: From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees (3.15); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.25); From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.30).
- **couple** — top: From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.45); From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees (3.44); From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays and Entry Fees (3.41). Bottom, lowest first: From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.08); From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.20); From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.25).
- **friends** — top: From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.53); From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees (3.48); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (3.44). Bottom, lowest first: From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha and Amboseli with Stays and Entry Fees (3.22); From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees (3.28); From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.28).
- **solo** — top: From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees (3.44); From Nairobi: 4-Day Masai Mara Safari with Stays and Entry Fees (3.43); From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays and Entry Fees (3.43). Bottom, lowest first: From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.19); From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.28); From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees (3.31).

### budget_tier

- **budget** — top: From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees (3.53); From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees (3.51); From Nairobi: 6-Day Masai Mara, Lake Nakuru, and Amboseli Safari With Stays and Entry Fees (3.46). Bottom, lowest first: From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.05); From Nairobi: Fly-In 5-Day Masai Mara and Amboseli Private Safari with Luxury Stays and Entry Fees (3.17); From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.21).
- **luxury** — top: From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.44); From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays and Entry Fees (3.39); From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees (3.39). Bottom, lowest first: From Nairobi: Fly-In 5-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.16); From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.21); From Nairobi: 7-Day Ultimate Kenya Safari to Masai Mara, Nakuru, Naivasha and Amboseli with Stays and Entry Fees (3.22).
- **mid** — top: From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees (3.50); From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees (3.49); From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (3.48). Bottom, lowest first: From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.13); From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.22); From Nairobi: 3-Day Masai Mara Safari With Stays and Entry Fees (3.30).
- **premium** — top: From Nairobi: 4-Day Masai Mara and Lake Nakuru Safari With Stays and Entry Fees (3.45); From Nairobi: 5-Day Masai Mara, Nakuru, and Naivasha Safari with Stays and Entry Fees (3.44); From Nairobi: 6-Day Masai Mara, Lake Naivasha, and Amboseli Safari with Stays and Entry Fees (3.43). Bottom, lowest first: From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (3.19); From Nairobi: 4-Day Masai Mara and Lake Naivasha Safari With Stays and Entry Fees (3.23); From Nairobi: 2-Day Masai Mara Safari with Stays and Entry Fees (3.28).

## Sample persona quotes

- **p0016** on Book Masai Mara Safaris (mean PI 2.91, anthropic): 25-34 solo from France, luxury budget, first timer, planning months 1 3, via app; interests: big_five, maasai_culture
  > Je suis intéressée, mais pas prête à réserver tout de suite. Les safaris en fly-in privés avec hébergements de luxe (3 à 5 jours) correspondent à ce que je cherche pour une première fois : big five, et si possible une vraie rencontre avec la culture maasai. Le tableau comparatif est pratique, et l'annulation gratuite plus l'assistance 24/7 me rassurent sur une appli.

Ce qui me freine : aucun prix affiché sur les 14 produits, aucun nom de camp ni de lodge pour les "luxury stays", et rien sur une visite de village maasai respectueuse. Je ne sais pas non plus qui est vraiment l'opérateur, puisque Headout est un intermédiaire new-yorkais, et pour un budget luxe, seule, je veux plus de détails avant de payer.

- **p0005** on Book Masai Mara Safaris (mean PI 3.11, anthropic): 25-34 family with kids from Germany, premium budget, first timer, planning weeks 1 4, via mobile_web; interests: birding, maasai_culture
  > I'd say it's moderately likely, but I wouldn't book from this page today. The fly-in private safaris with luxury stays look right for us as a premium family with kids, and I like that Lake Naivasha and Lake Nakuru are combined for the birding. The free cancellation and the vetting of operators also reassure me. What stops me is that no prices are shown on any of the 14 products, and I can't tell whether camps accept young children. Nothing mentions a Maasai village visit or a birding guide either, and the 5–6 hour road drive would be hard with kids. I also don't know who actually runs the trip on the ground, since Headout is only a curator. I'd want those answers before I commit, and I'm planning on a short timeline, so I'd probably message them or compare other sites first.

- **p0004** on Book Masai Mara Safaris (mean PI 3.67, anthropic): 35-44 couple from India, budget budget, first timer, planning last minute, via mobile_web; interests: photography, great_migration
  > I'm interested but wouldn't book yet. The road-safari options, like the 3-day with stays and entry fees, fit a budget couple, and the Great Migration season info is useful for my photography. The 3-day road trip might even work last minute. But not a single price is shown across 14 products, and I can't tell whether this fits my budget without clicking into each one. I'm also unsure about Headout. It says it vets operators, but I don't know which camp or vehicle I'd get, or whether I'd have a window seat for photos in a shared van. I'd keep the page open and compare a couple of listings, but I'd want clear prices, a cancellation policy and the vehicle details before paying on my phone.

- **p0003** on Book Masai Mara Safaris (mean PI 3.67, anthropic): 18-24 friends from China, mid budget, first timer, planning weeks 1 4, via mobile_web; interests: birding, big_five
  > I'm interested but probably won't book straight from this page. I like that it covers the big five and has a 4-day Mara and Lake Nakuru option. Nakuru is great for birding, and a table comparing 2- to 7-day trips helps a first-timer like me. The free cancellation and 24/7 support also matter since I'd be going with friends and have never done a safari.

What stops me is that no prices are shown on any of the 14 products. I'm on my phone with a mid budget and need to split costs with friends, so I can't tell if this is affordable. I also don't know who Headout is, and the page doesn't say whether the actual operator is licensed. I'd want to see prices, a real operator name, and whether the guides know birds. I'd keep the tab open and compare with other sites first.

- **p0026** on From Nairobi: Private Day Trip to Masai Mara Reserve with Lunch and Entry Fees (mean PI 2.84, anthropic): 35-44 couple from Germany, budget budget, first timer, planning months 1 3, via mobile_web; interests: luxury_camps, big_five
  > I'm only lukewarm on this one. A private 4x4 with park fees, lunch and hotel pickup included is appealing for a budget couple, and a day trip would let us see the Big Five without paying for a camp. But 13 or more hours, mostly on the road for a single game drive, sounds exhausting, and it's nothing like the luxury camp feeling we actually want. What would stop me is that no price is shown, the card says 17 hours while the itinerary says 13-14, no operator is named, and the free cancellation has no cutoff. I'd ke

- **p0021** on From Nairobi: Fly-In 4-Day Masai Mara Private Safari with Luxury Stays and Entry Fees (mean PI 3.65, anthropic): 45-54 friends from United States, premium budget, first timer, planning months 3 plus, via desktop; interests: luxury_camps, great_migration
  > I'm pretty interested, but I wouldn't click "book" yet. A private fly-in with luxury camps, six game drives, and park fees included is what I want for my first safari, and I'm planning months ahead with a premium budget. A 4.9 from 70 reviews is encouraging too. What stops me is that the price isn't shown, the operator isn't named, and there's no cancellation policy. I'm not wiring a big deposit to an unnamed company. I also want to know which camp I'd be in and whether the timing lines up with the Great Migration river crossings, since that's the main reason I'm going. If those details check out, I'd probably book.

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

Uncalibrated assumptions. See anchors.CALIBRATION_PLAN.

- page_mean_pass: 3.6
- page_mean_warn: 3.2
- segment_mean_pass: 3.4
- segment_mean_warn: 2.8
- product_mean_pass: 3.3
- product_mean_warn: 2.6
- cannibal_pi_delta: 0.25

Calibration against live CVR is not done in this scorecard. Shadow the next MMP and compare product rank to realized conversion before these pass/warn/fail cuts become a gate.
