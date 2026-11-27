"""Resolve a Combined Entity from the public Headout site.

The live product-card API returned HTTP 403 when these specs were first seeded,
so the JSON shapes below are defensive. Confirm them against a successful
response before treating a field as guaranteed.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable

Fetch = Callable[[str], tuple[int, str]]

COLLECTION_API = "https://api-ho.headout.com/api/v2/collections/{ce_id}/?language=EN"
CARDS_API = (
    "https://api-ho.headout.com/api/v2/collections/{ce_id}/product-cards/"
    "?currency=USD&language=EN&sort-type=POPULARITY&limit=30&offset=0"
)
COLLECTION_PAGE = "https://www.headout.com/search?q={query}"


@dataclass
class ResolvedProduct:
    id: str
    title: str
    price: float | None = None
    currency: str | None = None
    duration: str | None = None
    rating: float | None = None
    review_count: int | None = None
    inclusions: list[str] = field(default_factory=list)
    url: str | None = None
    cancellation: str | None = None
    pickup: str | None = None


@dataclass
class ResolvedCE:
    ce_id: str | None
    name: str
    collection_url: str | None
    destination: str | None
    hero_title: str | None
    hero_copy: str | None
    microbrand_url: str | None
    products: list[ResolvedProduct]
    page_live: bool
    notes: list[str] = field(default_factory=list)


def _loads(text: str) -> dict | None:
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _dig(payload: dict, *paths: tuple[str, ...]):
    for path in paths:
        cursor = payload
        ok = True
        for key in path:
            if not isinstance(cursor, dict) or key not in cursor:
                ok = False
                break
            cursor = cursor[key]
        if ok:
            return cursor
    return None


def _cards(payload: dict) -> list[dict]:
    found = _dig(
        payload,
        ("result", "productCards", "items"),
        ("productCards", "items"),
        ("items",),
        ("products",),
        ("data", "products"),
    )
    if isinstance(found, list):
        return [item for item in found if isinstance(item, dict)]
    if isinstance(found, dict) and isinstance(found.get("items"), list):
        return [item for item in found["items"] if isinstance(item, dict)]
    return []


def _product(raw: dict) -> ResolvedProduct:
    price_block = raw.get("listingPrice") or raw.get("price") or {}
    if isinstance(price_block, (int, float)):
        price = float(price_block)
        currency = raw.get("currency")
    elif isinstance(price_block, dict):
        amount = price_block.get("finalPrice", price_block.get("amount", price_block.get("value")))
        price = float(amount) if isinstance(amount, (int, float)) else None
        currency = price_block.get("currency") or raw.get("currency")
    else:
        price = None
        currency = raw.get("currency")
    inclusions = raw.get("inclusions") or raw.get("highlights") or []
    if isinstance(inclusions, str):
        inclusions = [inclusions]
    return ResolvedProduct(
        id=str(raw.get("id") or raw.get("tourGroupId") or raw.get("title") or "unknown"),
        title=str(raw.get("title") or raw.get("name") or "Untitled"),
        price=price,
        currency=currency,
        duration=raw.get("duration") or raw.get("durationText"),
        rating=_float(raw.get("rating") or raw.get("averageRating")),
        review_count=_int(raw.get("ratingCount") or raw.get("reviewCount")),
        inclusions=[str(item) for item in inclusions],
        url=raw.get("url"),
        cancellation=raw.get("cancellation") or raw.get("cancellationPolicy"),
        pickup=raw.get("pickup"),
    )


def _float(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _int(value) -> int | None:
    return int(value) if isinstance(value, int) else None


def _collection_fields(payload: dict) -> dict:
    found = _dig(payload, ("result", "collection"), ("collection",), ("result",))
    return found if isinstance(found, dict) else payload


def _id_from_query(query: str) -> str | None:
    match = re.search(r"(?:^|c-)(\d+)$", query.strip())
    if match:
        return match.group(1)
    if query.strip().isdigit():
        return query.strip()
    return None


def _id_from_html(html: str) -> str | None:
    match = re.search(r"-c-(\d+)/", html)
    return match.group(1) if match else None


class HeadoutLookup:
    """Public-site resolver. `fetch` returns (status_code, body)."""

    def __init__(self, fetch: Fetch):
        self.fetch = fetch

    def resolve(self, query: str) -> ResolvedCE:
        notes: list[str] = []
        ce_id = _id_from_query(query)
        if ce_id is None:
            status, body = self._safe(COLLECTION_PAGE.format(query=query.replace(" ", "+")))
            if status == 200:
                ce_id = _id_from_html(body)
            else:
                notes.append(f"Headout search returned HTTP {status}.")
        if ce_id is None:
            return ResolvedCE(
                ce_id=None,
                name=query,
                collection_url=None,
                destination=None,
                hero_title=None,
                hero_copy=None,
                microbrand_url=None,
                products=[],
                page_live=False,
                notes=notes + ["No collection id was found on the public site."],
            )
        status, body = self._safe(COLLECTION_API.format(ce_id=ce_id))
        payload = _loads(body) if status == 200 else None
        if payload is None:
            notes.append(f"Collection API for {ce_id} returned HTTP {status}. Shape not confirmed.")
            info: dict = {}
        else:
            info = _collection_fields(payload)
        card_status, card_body = self._safe(CARDS_API.format(ce_id=ce_id))
        card_payload = _loads(card_body) if card_status == 200 else None
        products = _cards(card_payload) if card_payload else []
        if card_status != 200:
            notes.append(
                f"Product-card API returned HTTP {card_status}. "
                "A 403 was seen from this environment when the pilot specs were seeded."
            )
        parsed = [_product(item) for item in products]
        name = str(info.get("displayName") or info.get("name") or query)
        url = info.get("url") or info.get("collectionUrl")
        if not url:
            slug = info.get("slug")
            url = f"https://www.headout.com/{slug}/" if slug else None
        micro = info.get("microbrandUrl") or info.get("microBrandUrl")
        return ResolvedCE(
            ce_id=ce_id,
            name=name,
            collection_url=url,
            destination=info.get("cityCode") or info.get("destination") or info.get("city"),
            hero_title=info.get("heroTitle") or info.get("title"),
            hero_copy=info.get("subtext") or info.get("heroCopy") or info.get("description"),
            microbrand_url=micro,
            products=parsed,
            page_live=bool(parsed),
            notes=notes,
        )

    def _safe(self, url: str) -> tuple[int, str]:
        try:
            return self.fetch(url)
        except Exception as exc:  # network and parser errors stay in the report
            return 0, str(exc)
