"""desaparecidosterremotovenezuela.com adapter.

This is the most thoroughly documented adapter — it serves as the reference
implementation for adding new platforms. The site is fully JS-rendered
(React), so we use Playwright to type the query, wait for results, and
extract structured data from the DOM.

NOTE: Selector strings are best-guess and should be validated against the
live site before relying on them in production. The graceful-degradation
behaviour (return [] on any error) means a broken selector just yields zero
matches, never a 500.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import quote_plus

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)


class DesaparecidosSearcher(BaseSearcher):
    slug = "desaparecidosterremotovenezuela"
    label = "Desaparecidos Terremoto Venezuela"
    url = "https://desaparecidosterremotovenezuela.com/"

    # The site exposes a search input on /identificar/ and likely a top-level
    # search bar on /. We try the homepage first, then fall back to the
    # facial-recognition flow's text search if needed.
    SEARCH_URL = "https://desaparecidosterremotovenezuela.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                await page.goto(self.SEARCH_URL, wait_until="domcontentloaded", timeout=15000)
                # Wait for the search UI to hydrate. Adjust the selector to
                # whatever the live site exposes (best-guess below).
                try:
                    await page.wait_for_selector(
                        "input[type='search'], input[name='q'], input[placeholder*='uscar' i]",
                        timeout=8000,
                    )
                except Exception:  # noqa: BLE001
                    logger.warning("desaparecidos: search input never appeared")

                # Try multiple selector strategies for the input.
                input_handle = None
                for selector in (
                    "input[type='search']",
                    "input[name='q']",
                    "input[placeholder*='uscar' i]",
                    "input[placeholder*='ombre' i]",
                ):
                    handle = await page.query_selector(selector)
                    if handle:
                        input_handle = handle
                        break

                if not input_handle:
                    logger.warning("desaparecidos: no search input found")
                    return matches

                await input_handle.fill(query)
                await input_handle.press("Enter")

                # Wait for results to render — adjust selector if the site
                # uses a different result-card class.
                try:
                    await page.wait_for_selector(
                        ".result, .card, [data-testid='result'], article",
                        timeout=10000,
                    )
                except Exception:  # noqa: BLE001
                    logger.warning("desaparecidos: no result elements appeared")

                # Extract candidate cards. We grab a generous superset of
                # selectors so the adapter survives DOM changes gracefully.
                cards = await page.query_selector_all(
                    ".result, .card, article, [data-testid='result'], li"
                )

                for card in cards[:20]:
                    text = (await card.inner_text()).strip()
                    if not text or len(text) < 5:
                        continue
                    if not re.search(re.escape(query[:3]), text, re.IGNORECASE):
                        # Skip cards that don't even contain a fragment of
                        # the query — most likely noise.
                        continue
                    href = await card.get_attribute("href") or ""
                    if not href or href.startswith("#"):
                        # If the card itself isn't a link, look for the first <a>.
                        a = await card.query_selector("a[href]")
                        if a:
                            href = await a.get_attribute("href") or ""
                    photo_handle = await card.query_selector("img")
                    photo_url = await photo_handle.get_attribute("src") if photo_handle else None

                    matches.append(
                        {
                            "name": text.splitlines()[0][:120],
                            "status": "missing",
                            "last_seen": " — ".join(text.splitlines()[1:3])[:200],
                            "age": None,
                            "source_url": (
                                href if href.startswith("http")
                                else f"https://desaparecidosterremotovenezuela.com{href}"
                            ),
                            "photo_url": photo_url,
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            logger.exception("desaparecidos search failed: %s", exc)
            return []

        return matches