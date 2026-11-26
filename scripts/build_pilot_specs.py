"""Build the pilot collection specs from trimmed public API extracts.

Run from the repo root:

    PYTHONPATH=src python scripts/build_pilot_specs.py

Product rows come from specs/source/*.products.json, captured 2026-11-26 from
the Headout collection product-card API. Page copy in this file is limited to
strings confirmed in the raw HTML or the microbrand CMS payload the same day.
"""

from __future__ import annotations

import html
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from collection_qa.tags import infer_tags  # noqa: E402

SOURCE = ROOT / "specs" / "source"
OUT = ROOT / "specs"

MARA_SSR = ["57711", "57793", "57723", "57795", "57690", "57697", "57698", "57724", "57638"]
MILFORD_SSR = ["29695", "18125", "18103", "56753", "56772", "37309", "23887", "15588", "36204"]

HAND = {
    "57795": {
        "pickup_status": "stated",
        "pickup": "Nairobi hotel",
        "inclusions_status": "stated",
        "inclusions": [
            "3-day Masai Mara safari",
            "3 game drives",
            "All park entry fees",
            "Expert guide",
            "Round-trip transfers",
            "4x4 Land Cruiser with pop-up roof",
            "2 nights in a self-contained tent",
            "Meals as per itinerary, with a picnic lunch on day 2",
            "Bottled water",
            "Shared or private, and budget, comfort, or luxury, as selected",
        ],
        "exclusions": ["Tips", "Drinks", "Pickup from hotels in Naivasha"],
        "notes": "Product page fetched 2026-11-26. That page states a 60–72 hour itinerary.",
    },
    "57723": {
        "pickup_status": "stated",
        "pickup": "Masai Mara airstrip after the flight from Nairobi. Not a Nairobi hotel pickup.",
        "inclusions_status": "stated",
        "inclusions": [
            "3-day private luxury fly-in safari",
            "4 game drives",
            "Park entry fees",
            "Flights during the tour within a fixed budget",
            "Luxury stay at Sarova Mara, Mara Serena, Mara West, or Emayian, subject to availability",
            "Meals as per itinerary",
            "Drinking water",
            "Round-trip transfers",
        ],
        "exclusions": [
            "Breakfast on day 1 and dinner on day 3",
            "Spirits and liquor",
            "Spa treatments",
            "Accommodation before and after the tour",
        ],
        "notes": "Product page fetched 2026-11-26. Balloon, Maasai village, bush breakfast, and sundowners are extra.",
    },
    "57699": {
        "pickup_status": "stated",
        "pickup": "Nairobi hotel. Drop-off in Westlands or Nairobi centre; airport drop-off is extra.",
        "inclusions_status": "stated",
        "inclusions": [
            "4 game drives",
            "English-speaking driver-guide",
            "4 nights' accommodation",
            "All park entry fees",
            "Meals as per itinerary",
            "4x4 Land Cruiser with pop-up roof",
            "Bottled water",
            "Nairobi hotel pickup",
        ],
        "exclusions": [
            "Maasai village visit (USD 20 on the product page)",
            "Balloon safari",
            "Drinks",
            "Gratuity",
        ],
        "notes": "Product page fetched 2026-11-26.",
    },
    "37309": {
        "pickup_status": "not_included",
        "pickup": "Milford Sound Terminal. Coach transfers are excluded on the product page.",
        "inclusions_status": "stated",
        "inclusions": [
            "Up to 2-hour Milford Sound cruise",
            "Nature guide commentary",
            "Viewing decks",
            "Wildlife spotting, not guaranteed",
            "Tea and coffee",
            "Multi-language audio guide app",
        ],
        "exclusions": ["Food and beverages for purchase", "Coach transfers"],
        "accessibility": (
            "The cruise is not fully wheelchair accessible. Electric wheelchairs cannot be accommodated. "
            "Accessible bathrooms are at the terminal, not onboard."
        ),
        "notes": "Product page fetched 2026-11-26. Cancellation on that page is 24 hours.",
    },
    "29695": {
        "pickup_status": "variant_dependent",
        "pickup": "Card says pickup depends on the option. A fly-cruise-fly upgrade from Queenstown is offered.",
        "inclusions_status": "stated",
        "inclusions": [
            "1-hour 45-minute to 2-hour cruise",
            "Skipper commentary",
            "Tea and coffee",
            "Outdoor decks and indoor lounge",
            "Multi-language audio guide app",
            "Scenic flight transfers from Queenstown if that option is selected",
        ],
        "exclusions": ["Other food and beverages"],
        "notes": "Product page fetched 2026-11-26. The card duration is 1 hr 40 mins–6 hrs because options include a longer fly package.",
    },
    "23887": {
        "pickup_status": "variant_dependent",
        "pickup": "Hotel transfers from Queenstown are included only on the option that says so.",
        "inclusions_status": "stated",
        "inclusions": [
            "Milford Sound cruise with live commentary",
            "Coach, luxury vehicle, or scenic flights, as selected",
            "Hotel transfers from Queenstown, as selected",
            "Walks at Mirror Lakes, Eglinton Valley, and Monkey Creek, as selected",
            "Tea and coffee, as selected",
        ],
        "exclusions": ["Food and drinks not listed in the selected option"],
        "notes": "Product page fetched 2026-11-26. A rendered markdown fetch showed an original price of NZ$309; that string was not in the raw HTML from this environment and is not used as a price.",
    },
}


def _load(name: str) -> dict:
    return json.loads((SOURCE / name).read_text(encoding="utf-8"))


def _features(raw: dict) -> list[str]:
    labels = {
        "FREE_CANCELLATION": "Free cancellation",
        "BOOK_NOW_PAY_LATER": "Book now, pay later",
        "TRANSFERS": "Transfers",
        "MEALS_INCLUDED": "Meals",
        "GUIDED_TOUR": "Guided tour",
        "HOTEL_PICKUP": "Hotel pickup",
        "AUDIO_GUIDE": "Audio guide",
    }
    features = []
    for code, description in (raw.get("descriptor_notes") or {}).items():
        if code == "DURATION" or code not in labels:
            continue
        if description and "based on your selection" in description.lower():
            features.append(f"{labels[code]} (depends on the option)")
        else:
            features.append(labels[code])
    for persona in raw.get("personas") or []:
        features.append(f"Headout persona tag: {persona}")
    return features


def _hours(ms) -> float | None:
    if ms is None:
        return None
    return round(ms / 3_600_000, 2)


def _product(raw: dict, ssr_index: dict[str, int], currency_note: str) -> dict:
    product_id = raw["id"]
    hand = HAND.get(product_id, {})
    codes = raw.get("descriptor_codes") or []
    if "pickup_status" in hand:
        pickup_status = hand["pickup_status"]
    elif "HOTEL_PICKUP" in codes or "TRANSFERS" in codes:
        pickup_status = "variant_dependent"
    else:
        pickup_status = "not_stated"
    category = raw.get("category") or ""
    if "safari" in category.lower():
        product_type = "safari"
    elif "cruise" in category.lower():
        product_type = "cruise"
    elif "tour" in category.lower() or "aerial" in category.lower():
        product_type = "tour"
    else:
        product_type = "experience"
    slug = raw["url_slug"]
    url = "https://www.headout.com" + slug
    observations = [
        {
            "amount": raw["price"],
            "currency": raw["currency"],
            "source": "collection product-card API",
            "source_url": currency_note,
            "note": "finalPrice with the currency query parameter in the source URL",
        }
    ]
    if product_id == "57711":
        observations.append(
            {
                "amount": 321.19,
                "currency": "USD",
                "source": "headout.com collection SSR embed",
                "source_url": "https://www.headout.com/masai-mara-c-7324/",
                "note": "listingPrice.finalPrice for tour group 57711 in the 2026-11-26 HTML __NEXT_DATA__ payload",
            }
        )
    record = {
        "id": product_id,
        "title": raw["title"],
        "url": url,
        "product_type": product_type,
        "price": raw["price"],
        "original_price": raw["original_price"],
        "currency": raw["currency"],
        "price_unit": raw["price_unit"],
        "other_prices_exist": raw["other_prices_exist"],
        "best_discount_percent": raw["best_discount_percent"],
        "duration": raw["duration_label"],
        "duration_hours_min": _hours(raw["duration_ms_min"]),
        "duration_hours_max": _hours(raw["duration_ms_max"]),
        "tags": infer_tags(
            raw["title"],
            multi_variant=raw["multi_variant"],
            combo=raw["combo"],
            category=category or None,
        ),
        "features": _features(raw),
        "rating": raw["rating"],
        "review_count": raw["review_count"],
        "inclusions": hand.get("inclusions", []),
        "inclusions_status": hand.get("inclusions_status", "unknown"),
        "exclusions": hand.get("exclusions", []),
        "pickup_status": pickup_status,
        "pickup": hand.get("pickup"),
        "cancellation": raw["cancellation"],
        "accessibility": hand.get("accessibility"),
        "multi_variant": raw["multi_variant"],
        "api_guest_count": raw.get("guest_count"),
        "popularity_rank": raw["popularity_rank"],
        "page_ssr_rank": ssr_index.get(product_id),
        "price_observations": observations,
        "notes": hand.get("notes"),
    }
    return {key: value for key, value in record.items() if value is not None}


def _dump(path: Path, payload: dict) -> None:
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True, width=100),
        encoding="utf-8",
    )
    print(f"wrote {path}")


def build_mara() -> None:
    raw = _load("masai-mara.products.json")
    faqs = [
        {"q": item["q"], "a": html.unescape(item["a"])}
        for item in json.loads((SOURCE / "masai-mara.faqs.json").read_text(encoding="utf-8"))
    ]
    ssr = {product_id: index + 1 for index, product_id in enumerate(MARA_SSR)}
    products = [_product(item, ssr, raw["source_url"]) for item in raw["products"]]
    spec = {
        "id": "masai-mara",
        "name": "Masai Mara",
        "destination": "Masai Mara National Reserve, Kenya, departing Nairobi",
        "page_type": "microbrand",
        "catalog_status": "live_headout",
        "collection_id": "7324",
        "ce_id": None,
        "collection_type": "POI",
        "primary_city_code": "NAIROBI",
        "fetched_at": "2026-11-26",
        "currency": "USD",
        "scope_keywords": ["masai mara", "maasai mara"],
        "lead_product_id": "57711",
        "sources": [
            {
                "url": "https://www.masai-mara-safaris.com/",
                "role": "Headout microbrand homepage. CMS payload and schema.org FAQ.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": "https://www.masai-mara-safaris.com/legal/",
                "role": "Legal entity Headout Inc, 82 Nassau Street, New York.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": "https://www.headout.com/masai-mara-c-7324/",
                "role": "headout.com collection. SSR product cards and empty long-form payload.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": raw["source_url"],
                "role": "Collection product-card API, currency=USD, sort=POPULARITY. 17 products.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": "https://www.viator.com/tours/Nairobi/3-DAYS-2-NIGHTS-BUDGET-GROUP-SAFARI-TO-MAASAI-MARA-NATIONAL-RESERVE/d5280-60115P2",
                "role": "Competitor context. From $195.56 per person plus $20 paid in destination.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": "https://www.getyourguide.com/nairobi-l267/from-nairobi-maasai-mara-3-day-budget-safari-holiday-t453629/",
                "role": "Competitor context. Page showed $345 per person and told travelers to pay park fees separately.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": "https://www.headout.com/safari/from-nairobi-3-day-masai-mara-budget-camping-safari-e-56686/",
                "role": "Headout budget camping safari that is not in collection 7324. Price was not on the fetched page.",
                "fetched_at": "2026-11-26",
            },
        ],
        "unknowns": [
            "The public collection id is 7324. The EOS Combined Entity id is not on the public page. Vatican and Colosseum used the same number for both; that pattern was not verified here.",
            "multiVariant and otherPricesExist are true on several cards. The from-price is not labeled with a stay tier (budget, comfort, luxury) or shared versus private.",
            "Price of Headout product 56686, the 3-day budget camping safari, was not in the fetched product page.",
            "A rendered fetch of the homepage did not include the sentence 'Crafted by Headout'. That sentence was on the about and fly-in URLs in search snippets. The homepage payload does contain 'Headout Inc'.",
            "Competitor park-fee treatment is not fully comparable. The Viator extract lists a $20 destination payment and an ambiguous park-fee line. The GetYourGuide extract tells the traveler to pay park fees of $200 or $400.",
        ],
        "also_surfaces": [
            {
                "type": "headout_collection",
                "url": "https://www.headout.com/masai-mara-c-7324/",
                "h1": "Experience the best of the Masai Mara from Nairobi",
                "ssr_longform_empty": True,
                "ssr_card_ids": MARA_SSR,
                "note": "First nine card ids in the 2026-11-26 HTML payload. API popularity order is different.",
            }
        ],
        "page": {
            "url": "https://www.masai-mara-safaris.com/",
            "hero": "Book Masai Mara Safaris",
            "meta_description": (
                "Lions, cheetahs, elephants, and the Great Migration across Kenya's open plains. "
                "Choose a safari by days, budget, transport, and how you want to experience the Mara."
            ),
            "usps": [
                "Park fees included",
                "Flexible bookings",
                "Verified operators. Headout checks safari operators for licensing, guide experience, vehicle type, and inclusions.",
                "How Headout makes choosing experiences effortless: curate, vet suppliers, keep options in one place, free cancellations, flexible payments, and 24/7 support.",
            ],
            "trust_signals": [
                "Homepage payload identifies Headout Inc.",
                "Legal page names Headout Inc, 82 Nassau Street #60351, New York, NY 10038.",
                "The fetched homepage names Headout and does not carry a separate sentence that the site is distinct from the reserve operator.",
            ],
            "faqs": faqs,
            "sections": [
                {
                    "id": "road",
                    "heading": "Road",
                    "body": (
                        "Travel from Nairobi by safari vehicle or transfer. The journey takes around 5–6 hours "
                        "and can include a Rift Valley stop or scenic detour. Best for: lower-cost trips, longer "
                        "itineraries, and multi-park circuits."
                    ),
                },
                {
                    "id": "fly_in",
                    "heading": "Fly-in",
                    "body": (
                        "Fly from Nairobi's Wilson Airport to an airstrip in the Mara. The flight takes about 45 minutes, "
                        "followed by a transfer to your camp or lodge. Best for: short trips when you want to spend more "
                        "of your time on safari."
                    ),
                },
                {
                    "id": "shared",
                    "heading": "Shared safari",
                    "body": "Share the vehicle and safari costs with other travellers. This keeps the price lower and works well for budget-conscious travellers.",
                },
                {
                    "id": "private",
                    "heading": "Private safari",
                    "body": "Have a vehicle dedicated to your group. You get more control over the pace and can spend longer at sightings that matter to you.",
                },
                {
                    "id": "four_day_table",
                    "heading": "4-day safari in the comparison table",
                    "body": "Masai Mara, or Masai Mara with Lake Naivasha or Lake Nakuru.",
                },
            ],
            "claims": [
                {
                    "id": "nakuru_on_4_day",
                    "text": "Lake Nakuru National Park (included with 4+ days safaris)",
                    "source_url": "https://www.masai-mara-safaris.com/",
                    "expects_tag": "lake_nakuru",
                    "min_duration_days": 4,
                    "severity": "warn",
                    "counter_quote": "Masai Mara, or Masai Mara with Lake Naivasha or Lake Nakuru.",
                },
                {
                    "id": "naivasha_on_4_day",
                    "text": "Lake Naivasha & Hell's Gate (included with 4+ days safaris)",
                    "source_url": "https://www.masai-mara-safaris.com/",
                    "expects_tag": "lake_naivasha",
                    "min_duration_days": 4,
                    "severity": "warn",
                    "counter_quote": "Masai Mara, or Masai Mara with Lake Naivasha or Lake Nakuru.",
                },
                {
                    "id": "amboseli_on_5_day",
                    "text": "Amboseli National Park (included with 5–7-day safaris)",
                    "source_url": "https://www.masai-mara-safaris.com/",
                    "expects_tag": "amboseli",
                    "min_duration_days": 5,
                    "severity": "warn",
                    "counter_quote": "The comparison table describes 5-day routes as Masai Mara, Lake Nakuru and Lake Naivasha, or Masai Mara and Amboseli.",
                },
            ],
            "rating": 4.8,
            "review_count": 2196,
            "rating_note": "Rendered homepage showed 4.8/5 from 2,196 travellers. The count 2196 is in the raw HTML. The same 2,196 figure is on the headout.com collection HTML.",
            "longform_in_ssr": None,
        },
        "products": products,
        "outside_collection": [
            {
                "id": "56686",
                "title": "From Nairobi: 3-Day Masai Mara Budget Camping Safari",
                "url": "https://www.headout.com/safari/from-nairobi-3-day-masai-mara-budget-camping-safari-e-56686/",
                "product_type": "safari",
                "price": None,
                "original_price": None,
                "currency": "USD",
                "price_unit": "per_person",
                "duration": "3 days",
                "duration_hours_min": 72,
                "duration_hours_max": 72,
                "tags": ["budget_camping", "masai_mara", "mara_only"],
                "features": ["Free cancellation", "Park fees included on the product page"],
                "inclusions": [
                    "Masai Mara National Reserve entry fees and taxes",
                    "English-speaking guide",
                    "Morning, afternoon, and full-day game drives",
                    "2 nights in a budget safari tented camp",
                    "Full-board meals",
                    "Round-trip 4x4 Land Cruiser",
                    "Nairobi hotel or airport pickup",
                    "Bottled water on game drives",
                ],
                "inclusions_status": "stated",
                "exclusions": [
                    "Gratuities",
                    "Maasai village visit, about $20–25 per person on the product page",
                    "Hot-air balloon, about $450–485 per person on the product page",
                    "Spirits and soft drinks",
                ],
                "pickup_status": "stated",
                "pickup": "Nairobi hotel or airport",
                "cancellation": "Cancel for a full refund up to 24 hours before the experience",
                "notes": "Live on Headout on 2026-11-26 and absent from collection 7324's 17-card API response. Price was not in the fetched page.",
            }
        ],
        "benchmarks": [
            {
                "id": "viator_budget_3day",
                "seller": "Viator",
                "url": "https://www.viator.com/tours/Nairobi/3-DAYS-2-NIGHTS-BUDGET-GROUP-SAFARI-TO-MAASAI-MARA-NATIONAL-RESERVE/d5280-60115P2",
                "fetched_at": "2026-11-26",
                "title": "3 days 2 nights budget group safari to Maasai Mara National Reserve",
                "price_from": 195.56,
                "currency": "USD",
                "price_unit": "per_person",
                "tag": "budget_camping",
                "comparability": "fees_unclear",
                "note": "From $195.56 per person plus $20 paid in destination. Park-fee inclusion was ambiguous in the fetched extract, so this is not a like-for-like gap.",
            },
            {
                "id": "gyg_budget_3day",
                "seller": "GetYourGuide",
                "url": "https://www.getyourguide.com/nairobi-l267/from-nairobi-maasai-mara-3-day-budget-safari-holiday-t453629/",
                "fetched_at": "2026-11-26",
                "title": "From Nairobi: Maasai Mara 3-Day Budget Safari Holiday by Jeep",
                "price_from": 345,
                "currency": "USD",
                "price_unit": "per_person",
                "tag": "budget_camping",
                "comparability": "fees_unclear",
                "note": "The fetched page showed $345 per person and told travelers to pay park entrance fees of $200 (Jan–Jun) or $400 (Jul–Dec). Currency was the symbol shown, not a confirmed ISO label. Not like-for-like with Headout cards that say entry fees are included.",
            },
        ],
    }
    _dump(OUT / "masai-mara.yaml", spec)


def build_milford() -> None:
    raw = _load("milford-sound.products.json")
    ssr = {product_id: index + 1 for index, product_id in enumerate(MILFORD_SSR)}
    products = [_product(item, ssr, raw["source_url"]) for item in raw["products"]]
    spec = {
        "id": "milford-sound",
        "name": "Milford Sound cruises",
        "destination": "Milford Sound, Fiordland, New Zealand, with day trips from Queenstown and Te Anau",
        "page_type": "headout_collection",
        "catalog_status": "live_headout",
        "collection_id": "3945",
        "ce_id": None,
        "collection_type": "DAY_TRIP",
        "primary_city_code": "MILFORD_SOUND",
        "fetched_at": "2026-11-26",
        "currency": "NZD",
        "scope_keywords": ["milford"],
        "lead_product_id": "29695",
        "sources": [
            {
                "url": "https://www.headout.com/milford-sound-cruise-tickets-c-3945/",
                "role": "headout.com collection. H1, meta description, and nine SSR cards confirmed in the HTML. Long-form payload empty.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": raw["source_url"],
                "role": "Collection product-card API, currency=NZD, sort=POPULARITY. 24 products.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": "https://www.headout.com/milford-sound-cruise-tickets/milford-sound-cruise-by-realnz-e-37309/",
                "role": "RealNZ product page, including the wheelchair limitation.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": "https://www.viator.com/en-NZ/Fiordland-and-Milford-Sound-tours/Cruises-Sailing-and-Water-Tours/d756-g3",
                "role": "Competitor context. Cruise from-prices were shown in US dollars.",
                "fetched_at": "2026-11-26",
            },
            {
                "url": "https://www.getyourguide.com/queenstown-l498/from-queenstown-milford-sound-discover-more-longest-cruise-t1068280/",
                "role": "Competitor context. Queenstown coach-and-cruise from $188. Currency label was not confirmed.",
                "fetched_at": "2026-11-26",
            },
        ],
        "unknowns": [
            "No Headout microbrand for Milford Sound was found in this pass.",
            "The public collection id is 3945. The EOS Combined Entity id is not on the public page.",
            "The collection SSR payload's long-form body was empty. A client-rendered guide may exist and was not confirmed. A rendered-markdown fetch produced a long FAQ and prices such as NZ$143.20 and NZ$179; those strings were not in the raw HTML fetched from this environment and are not used.",
            "The headout.com HTML fetched here embedded USD from-prices (for example 84.98 USD on product 29695). The catalog below is the NZD API response. The two are not compared.",
            "Inclusions are marked unknown where the product page was not opened.",
            "Secondary cities on the collection record are QUEENSTOWN and TE_ANAU.",
        ],
        "also_surfaces": [],
        "page": {
            "url": "https://www.headout.com/milford-sound-cruise-tickets-c-3945/",
            "hero": "Experience the best cruises in Milford Sound",
            "meta_description": "Experience a 2-hour Milford Sound Cruise with a view of the iconic Mitre Peak. Onboard commentary. Cancel for free. 24/7 support.",
            "usps": [
                "Onboard commentary",
                "Cancel for free",
                "24/7 support",
            ],
            "trust_signals": [
                "Marketplace page on headout.com.",
                "Meta description offers free cancellation and 24/7 support.",
            ],
            "faqs": [],
            "sections": [
                {
                    "id": "meta",
                    "heading": "Meta description",
                    "body": "Experience a 2-hour Milford Sound Cruise with a view of the iconic Mitre Peak.",
                }
            ],
            "claims": [],
            "rating": None,
            "review_count": None,
            "rating_note": "A rendered fetch showed 4.8/5 from 6,363 travellers. That count was not in the raw HTML payload fetched from this environment, so it is not stored as the collection rating.",
            "duration_claim_hours": 2,
            "duration_claim_text": "Experience a 2-hour Milford Sound Cruise with a view of the iconic Mitre Peak.",
            "longform_in_ssr": False,
        },
        "products": products,
        "outside_collection": [],
        "benchmarks": [
            {
                "id": "viator_small_cruise",
                "seller": "Viator",
                "url": "https://www.viator.com/en-NZ/Fiordland-and-Milford-Sound-tours/Cruises-Sailing-and-Water-Tours/d756-g3",
                "fetched_at": "2026-11-26",
                "title": "Cruise Milford NZ small boutique cruise, and other fiord cruises",
                "price_from": 88,
                "currency": "USD",
                "price_unit": "per_person",
                "tag": "terminal_cruise",
                "comparability": "currency_unknown",
                "note": "The listing page showed from-prices in US dollars, from about US$88 for a RealNZ cruise and US$103 for a small-boat cruise. Not compared with the NZD catalog.",
            },
            {
                "id": "gyg_queenstown_day",
                "seller": "GetYourGuide",
                "url": "https://www.getyourguide.com/queenstown-l498/from-queenstown-milford-sound-discover-more-longest-cruise-t1068280/",
                "fetched_at": "2026-11-26",
                "title": "From Queenstown: Milford Sound Discover More Longest Cruise",
                "price_from": 188,
                "currency": None,
                "price_unit": "per_person",
                "tag": "from_queenstown",
                "comparability": "currency_unknown",
                "note": "Southern Discoveries coach-and-cruise, about 13.5 hours, from $188 per person. The fetched page did not confirm the currency.",
            },
        ],
    }
    _dump(OUT / "milford-sound.yaml", spec)


if __name__ == "__main__":
    build_mara()
    build_milford()
