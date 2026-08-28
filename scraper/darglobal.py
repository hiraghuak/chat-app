"""Scrape luxury development data from darglobal.co.uk.

Strategy: the sitemap (the only openly served resource) enumerates every page.
Real project pages are top-level single-segment slugs. We warm up the browser on
the homepage so Incapsula issues its clearance cookie, then visit each candidate
and keep the ones whose ``__NEXT_DATA__`` carries a ``projectDetailsData`` object.
All fields are read from that JSON, not the rendered DOM.
"""
from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Optional

from playwright.sync_api import Page

from common import USER_AGENT, goto_with_challenge, read_next_data
from normalize import Listing, clean_text

SITEMAP_URL = "https://darglobal.co.uk/sitemap.xml"
BASE = "https://darglobal.co.uk"

# Top-level slugs that are site sections / content, never a development.
NON_PROJECT = {
    "about", "blog", "press", "insights", "projects", "partners", "contact",
    "become-a-broker", "become-an-agent", "pay-online", "terms-conditions",
    "terms-of-uses", "privacy-policy", "cookie-policy", "thank-you", "success",
    "sitemap", "aida-360", "aston-martin-media", "one-of-one", "landing-page",
    "tokenization", "why-invest", "win-a-trip-to-dubai", "careers", "media",
    "news", "faqs", "faq", "sustainability", "investor-relations",
}

COUNTRY_HINTS = [
    (("dubai", "abu dhabi", "rak", "ras al khaimah", "marjan", "uae",
      "united arab emirates", "sharjah", "ajman"), "United Arab Emirates"),
    (("jeddah", "riyadh", "makkah", "mecca", "saudi", "ksa", "neom"), "Saudi Arabia"),
    (("muscat", "oman", "sohar", "aida"), "Oman"),
    (("doha", "qatar", "lusail"), "Qatar"),
    (("london", "uk", "united kingdom", "england"), "United Kingdom"),
    (("marbella", "spain", "costa"), "Spain"),
    (("maldives",), "Maldives"),
]


def _infer_country(location: str) -> Optional[str]:
    loc = (location or "").lower()
    for keys, country in COUNTRY_HINTS:
        if any(k in loc for k in keys):
            return country
    return None


def _sitemap_slugs() -> list[str]:
    req = urllib.request.Request(SITEMAP_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        xml = resp.read().decode("utf-8", "replace")
    root = ET.fromstring(xml)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    slugs: list[str] = []
    for loc in root.findall(".//sm:url/sm:loc", ns):
        url = (loc.text or "").strip()
        path = url.replace(BASE, "").strip("/")
        if path and "/" not in path and path not in NON_PROJECT:
            slugs.append(path)
    # stable, de-duplicated order
    return list(dict.fromkeys(slugs))


def _first(details: dict, *keys) -> Any:
    node = details
    for k in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(k)
    return node


def _extract(slug: str, next_data: dict) -> Optional[Listing]:
    page_props = next_data.get("props", {}).get("pageProps", {})
    pdd = page_props.get("projectDetailsData")
    if not pdd:
        return None
    attrs = pdd.get("attributes", {})
    details = attrs.get("ProjectDetails", {}) or {}

    banner = details.get("ProjectBanner", {}) or {}
    title = clean_text(banner.get("Heading") or attrs.get("title") or slug)
    location = clean_text(
        banner.get("Location")
        or _first(details, "loaction", "locationDetailsWithImages", "location")
        or ""
    )

    about = details.get("AboutProject", {}) or {}
    description_parts = [clean_text(about.get("description"))]
    why = details.get("whyInvest", {}) or {}
    if why.get("description"):
        description_parts.append("Why invest: " + clean_text(why.get("description")))

    property_type = None
    for row in about.get("AboutDetailsType", []) or []:
        if "property type" in str(row.get("name", "")).lower():
            property_type = clean_text(row.get("value"))

    amenities = [
        clean_text(a.get("name"))
        for a in (details.get("Amenities", {}) or {}).get("amenitiesList", []) or []
        if a.get("name")
    ]

    url = _first(details, "SEO", "canonicalURL") or f"{BASE}/{slug}"

    return Listing(
        id=f"darglobal:{slug}",
        source="DarGlobal",
        title=title,
        listing_type="sale",
        country=_infer_country(location),
        city=location or None,
        property_type=property_type,
        description=" ".join(p for p in description_parts if p),
        amenities=amenities or None,
        url=url,
    )


def scrape_darglobal(page: Page, limit: Optional[int] = None) -> list[Listing]:
    slugs = _sitemap_slugs()
    if limit:
        slugs = slugs[:limit]
    print(f"[darglobal] {len(slugs)} candidate project slugs from sitemap")

    # Warm up so Incapsula sets its clearance cookie on this context.
    goto_with_challenge(page, BASE, settle_ms=7000)

    listings: list[Listing] = []
    for i, slug in enumerate(slugs, 1):
        try:
            goto_with_challenge(page, f"{BASE}/{slug}", settle_ms=3000)
            nd = read_next_data(page)
            if not nd:
                continue
            listing = _extract(slug, nd)
            if listing and listing.title and "404" not in listing.title[:6]:
                listings.append(listing)
                print(f"[darglobal] {i}/{len(slugs)} ✓ {slug} -> {listing.title[:50]}")
        except Exception as exc:  # noqa: BLE001 - skip a bad page, keep going
            print(f"[darglobal] {i}/{len(slugs)} ✗ {slug}: {type(exc).__name__}")
    print(f"[darglobal] extracted {len(listings)} projects")
    return listings
