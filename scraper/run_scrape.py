"""Orchestrate the DarGlobal + Wasalt scrape and write data/listings.json.

Run offline on a dev machine (NOT inside the deployed container):

    scraper/.venv/bin/playwright install chromium     # one-time
    scraper/.venv/bin/python scraper/run_scrape.py            # full snapshot
    scraper/.venv/bin/python scraper/run_scrape.py --quick    # fast smoke test

The cleaned snapshot it produces is committed to the repo and baked into the
image, so the live chatbot never depends on the target sites being reachable.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from playwright.sync_api import sync_playwright

from common import new_context
from darglobal import scrape_darglobal
from wasalt import scrape_wasalt

DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def summarize(rows: list[dict]) -> None:
    by_source: dict[str, int] = {}
    priced = 0
    for r in rows:
        by_source[r["source"]] = by_source.get(r["source"], 0) + 1
        if r.get("price"):
            priced += 1
    print("\n===== SNAPSHOT SUMMARY =====")
    print(f"total listings : {len(rows)}")
    for src, n in sorted(by_source.items()):
        print(f"  {src:10s}: {n}")
    print(f"with price     : {priced}/{len(rows)}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Scrape DarGlobal + Wasalt")
    ap.add_argument("--quick", action="store_true",
                    help="small run: a few DarGlobal projects + 1 Wasalt city")
    ap.add_argument("--dg-limit", type=int, default=None,
                    help="cap number of DarGlobal candidate slugs")
    ap.add_argument("--max-per-page", type=int, default=None,
                    help="cap listings taken per Wasalt city page")
    ap.add_argument("--skip-darglobal", action="store_true")
    ap.add_argument("--skip-wasalt", action="store_true")
    args = ap.parse_args()

    dg_limit = args.dg_limit
    wasalt_cities = None
    max_per_page = args.max_per_page
    if args.quick:
        dg_limit = dg_limit or 6
        wasalt_cities = ["riyadh"]
        max_per_page = max_per_page or 8

    rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            if not args.skip_darglobal:
                ctx = new_context(browser)
                page = ctx.new_page()
                for listing in scrape_darglobal(page, limit=dg_limit):
                    rows.append(listing.to_dict())
                ctx.close()

            if not args.skip_wasalt:
                ctx = new_context(browser)
                page = ctx.new_page()
                for listing in scrape_wasalt(page, cities=wasalt_cities,
                                             max_per_page=max_per_page):
                    rows.append(listing.to_dict())
                ctx.close()
        finally:
            browser.close()

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "listings.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (DATA_DIR / "scraped_at.txt").write_text(date.today().isoformat(), encoding="utf-8")
    summarize(rows)
    print(f"\nwrote {DATA_DIR / 'listings.json'}")


if __name__ == "__main__":
    main()
