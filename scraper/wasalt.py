"""Scrape property listings from wasalt.sa (Saudi Arabia).

Each city listing page (e.g. /en/properties-for-sale-in-riyadh) embeds up to ~32
fully-populated listing objects in ``__NEXT_DATA__`` at
``props.pageProps.searchResult.properties`` — so we never need to open the
individual detail pages. We iterate a handful of major cities for both sale and
rent. Cloudflare is cleared by the headless browser on first navigation.
"""
from __future__ import annotations

import re
from typing import Optional

from playwright.sync_api import Page

from common import goto_with_challenge, read_next_data
from normalize import Listing, clean_text, to_float, to_int

BASE = "https://wasalt.sa"

CITIES = ["riyadh", "jeddah", "makkah", "madinah", "dammam", "al-khobar", "khamis-mushayt"]
PURPOSES = {"sale": "properties-for-sale-in", "rent": "properties-for-rent-in"}

# Price field names differ between sale and rent payloads.
PRICE_KEYS = ("salePrice", "rentPrice", "price", "conversionPrice")


def _price(info: dict) -> Optional[float]:
    for key in PRICE_KEYS:
        val = to_float(info.get(key))
        if val:
            return val
    return None


def _attr_map(prop: dict) -> dict[str, str]:
    return {a.get("key"): a.get("value") for a in prop.get("attributes", []) or [] if a.get("key")}


def _find_properties(next_data: Optional[dict]) -> list[dict]:
    """Locate the listings array in __NEXT_DATA__ resiliently.

    The expected path is props.pageProps.searchResult.properties, but the shape
    varies between sale/rent variants and A/B tests, so we fall back to scanning
    for any list of dicts that carry a ``propertyInfo`` object.
    """
    if not next_data:
        return []
    page_props = next_data.get("props", {}).get("pageProps", {})
    sr = page_props.get("searchResult")
    if isinstance(sr, dict) and isinstance(sr.get("properties"), list):
        return [p for p in sr["properties"] if isinstance(p, dict)]
    if isinstance(sr, list) and sr and isinstance(sr[0], dict) and "propertyInfo" in sr[0]:
        return [p for p in sr if isinstance(p, dict)]

    found: list[dict] = []

    def walk(obj):
        if found:
            return
        if isinstance(obj, list):
            if obj and isinstance(obj[0], dict) and "propertyInfo" in obj[0]:
                found.extend(obj)
                return
            for item in obj:
                walk(item)
        elif isinstance(obj, dict):
            for value in obj.values():
                walk(value)

    walk(page_props)
    return found


def _href_by_id(page: Page) -> dict[str, str]:
    """Map a listing id -> its detail href, read from the rendered anchors."""
    hrefs = page.evaluate(
        "() => Array.from(document.querySelectorAll('a[href]'))"
        ".map(a => a.getAttribute('href')).filter(Boolean)"
    )
    out: dict[str, str] = {}
    for h in hrefs:
        m = re.search(r"/property/[^ ]*?-(\d+)$", h)
        if m:
            out[m.group(1)] = h if h.startswith("http") else BASE + h
    return out


def _extract(prop: dict, listing_type: str, href_map: dict[str, str]) -> Optional[Listing]:
    if not isinstance(prop, dict):
        return None
    info = prop.get("propertyInfo", {}) or {}
    pid = str(prop.get("id") or "").strip()
    if not pid:
        return None
    attrs = _attr_map(prop)

    city = clean_text(info.get("city"))
    district = clean_text(info.get("district"))
    ptype = clean_text(info.get("propertySubType"))
    beds = to_int(attrs.get("noOfBedrooms"))
    baths = to_int(attrs.get("noOfBathrooms"))
    area = to_float(attrs.get("builtUpArea")) or to_float(prop.get("floorSize"))
    title = clean_text(info.get("title") or info.get("propertyName") or ptype or "Property")

    # Listing pages carry no long description; compose one for retrieval quality.
    bits = [f"{ptype or 'Property'} for {listing_type} in {district or city or 'Saudi Arabia'}"]
    if city and city != district:
        bits.append(city)
    if beds:
        bits.append(f"{beds} bedrooms")
    if baths:
        bits.append(f"{baths} bathrooms")
    if area:
        bits.append(f"{area:g} sqm built-up area")
    if info.get("address"):
        bits.append("Address: " + clean_text(info.get("address")))
    description = ". ".join(bits) + "."

    return Listing(
        id=f"wasalt:{pid}",
        source="Wasalt",
        title=title,
        listing_type=listing_type,
        country="Saudi Arabia",
        city=city or None,
        district=district or None,
        price=_price(info),
        currency=clean_text(info.get("currencyType")) or "SAR",
        property_type=ptype or None,
        bedrooms=beds,
        bathrooms=baths,
        area_sqm=area,
        description=description,
        url=href_map.get(pid) or f"{BASE}/en/property/{listing_type}/{pid}",
    )


def scrape_wasalt(page: Page, cities: Optional[list[str]] = None,
                  max_per_page: Optional[int] = None) -> list[Listing]:
    cities = cities or CITIES
    listings: list[Listing] = []
    seen: set[str] = set()

    for city in cities:
        for listing_type, prefix in PURPOSES.items():
            url = f"{BASE}/en/{prefix}-{city}"
            try:
                # Cloudflare occasionally serves an empty/variant payload on rapid
                # sequential requests; a slower reload reliably recovers the data.
                props: list[dict] = []
                for attempt in range(3):
                    goto_with_challenge(page, url, settle_ms=6000 + attempt * 3000)
                    props = _find_properties(read_next_data(page))
                    if props:
                        break
                    page.wait_for_timeout(2500)
                if not props:
                    print(f"[wasalt] {city}/{listing_type}: no listings after retries")
                    continue
                href_map = _href_by_id(page)
                if max_per_page:
                    props = props[:max_per_page]
                added = 0
                for prop in props:
                    listing = _extract(prop, listing_type, href_map)
                    if listing and listing.id not in seen:
                        seen.add(listing.id)
                        listings.append(listing)
                        added += 1
                print(f"[wasalt] {city}/{listing_type}: +{added} (total {len(listings)})")
            except Exception as exc:  # noqa: BLE001
                print(f"[wasalt] {city}/{listing_type} ✗ {type(exc).__name__}: {exc}")
    print(f"[wasalt] extracted {len(listings)} listings")
    return listings
