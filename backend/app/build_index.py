"""Build the vector index from the scraped listings snapshot.

Run once locally (the artifacts are committed and baked into the image):

    python -m app.build_index

Produces, under DATA_DIR:
    embeddings.npy   normalized float32 embedding matrix (N x dim)
    meta.json        listings aligned 1:1 with the matrix rows, for retrieval

For a few-hundred-listing snapshot, brute-force cosine similarity over this
matrix (a single numpy matmul) is instant and avoids a heavier ANN dependency.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_settings


def listing_to_document(listing: dict) -> str:
    """Flatten a listing into the text we embed (and later show the model)."""
    parts: list[str] = [f"{listing['source']} property listing."]
    if listing.get("title"):
        parts.append(listing["title"] + ".")
    if listing.get("property_type"):
        parts.append(f"Type: {listing['property_type']}.")
    parts.append(f"Listing type: for {listing.get('listing_type', 'sale')}.")

    loc = ", ".join(
        x for x in [listing.get("district"), listing.get("city"), listing.get("country")] if x
    )
    if loc:
        parts.append(f"Location: {loc}.")

    if listing.get("price"):
        cur = listing.get("currency") or ""
        parts.append(f"Price: {listing['price']:,.0f} {cur}.".strip())
    else:
        parts.append("Price: on request.")

    if listing.get("bedrooms"):
        parts.append(f"Bedrooms: {listing['bedrooms']}.")
    if listing.get("bathrooms"):
        parts.append(f"Bathrooms: {listing['bathrooms']}.")
    if listing.get("area_sqm"):
        parts.append(f"Area: {listing['area_sqm']:g} sqm.")
    if listing.get("amenities"):
        parts.append("Amenities: " + ", ".join(listing["amenities"][:12]) + ".")
    if listing.get("description"):
        parts.append(listing["description"])
    return " ".join(parts)


def build_index() -> None:
    settings = get_settings()
    data_dir = Path(settings.data_dir)
    listings = json.loads((data_dir / "listings.json").read_text(encoding="utf-8"))
    if not listings:
        raise SystemExit("data/listings.json is empty — run the scraper first.")

    print(f"[build_index] {len(listings)} listings; loading {settings.embedding_model}")
    model = SentenceTransformer(settings.embedding_model)
    docs = [listing_to_document(l) for l in listings]

    embeddings = model.encode(
        docs, batch_size=64, show_progress_bar=True,
        convert_to_numpy=True, normalize_embeddings=True,
    ).astype("float32")

    np.save(data_dir / "embeddings.npy", embeddings)
    # Store the document text alongside each listing for prompt building.
    for listing, doc in zip(listings, docs):
        listing["_document"] = doc
    (data_dir / "meta.json").write_text(
        json.dumps(listings, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[build_index] wrote embeddings.npy {embeddings.shape} + meta.json")


if __name__ == "__main__":
    build_index()
