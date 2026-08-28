"""Unified listing schema + cleaning helpers shared by both site scrapers."""
from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class Listing:
    id: str
    source: str                 # "DarGlobal" | "Wasalt"
    title: str
    listing_type: str           # "sale" | "rent"
    country: Optional[str] = None
    city: Optional[str] = None
    district: Optional[str] = None
    price: Optional[float] = None       # None => "on request" / not published
    currency: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[int] = None
    area_sqm: Optional[float] = None
    description: str = ""
    amenities: Optional[list[str]] = None
    url: Optional[str] = None
    image_url: Optional[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        if d.get("amenities") is None:
            d["amenities"] = []
        return d


def clean_text(value: Optional[str]) -> str:
    """Collapse whitespace and strip HTML tags from CMS rich text."""
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)          # drop any HTML tags
    value = value.replace(" ", " ")
    return re.sub(r"\s+", " ", value).strip()


def to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def to_int(value) -> Optional[int]:
    f = to_float(value)
    return int(f) if f is not None else None
