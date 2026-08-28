"""Shared Playwright helpers for the DarGlobal + Wasalt scrapers.

Both target sites sit behind JS bot-protection (DarGlobal → Imperva Incapsula,
Wasalt → Cloudflare), so a plain HTTP client cannot read their content pages.
A real headless browser executes the challenge, obtains the clearance cookie,
and can then load the Next.js pages whose data we want. All extraction reads the
embedded ``__NEXT_DATA__`` JSON blob rather than scraping the rendered DOM, which
is far more stable than CSS selectors.
"""
from __future__ import annotations

import json
from typing import Any, Optional

from playwright.sync_api import Browser, BrowserContext, Page

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def new_context(browser: Browser) -> BrowserContext:
    """A context that looks like a normal desktop Chrome session."""
    return browser.new_context(
        user_agent=USER_AGENT,
        locale="en-US",
        viewport={"width": 1366, "height": 900},
        java_script_enabled=True,
    )


def read_next_data(page: Page) -> Optional[dict[str, Any]]:
    """Return the parsed ``__NEXT_DATA__`` JSON from the current page, or None."""
    txt = page.evaluate(
        "() => { const el = document.getElementById('__NEXT_DATA__');"
        " return el ? el.textContent : null; }"
    )
    if not txt:
        return None
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return None


def goto_with_challenge(page: Page, url: str, settle_ms: int = 4000) -> None:
    """Navigate and give any bot-protection challenge time to run and clear."""
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(settle_ms)
