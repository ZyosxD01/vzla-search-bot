"""venezuelatebusca.com adapter.

TEMPLATE — selectors and DOM assumptions need validation against the live
site before this will return real results. The adapter is wired up so the
bot keeps working even when it returns [].

To activate:
  1. Open https://venezuelatebusca.com/ in a real browser
  2. Inspect the search input — note its selector and placeholder
  3. Inspect a search results page — note the result-card selector
  4. Update SEARCH_URL, the input selectors, and the card selectors below
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)


class VenezuelaBuscaSearcher(BaseSearcher):
    slug = "venezuelatebusca"
    label = "Venezuela Te Busca"
    url = "https://venezuelatebusca.com/"

    SEARCH_URL = "https://venezuelatebusca.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                await page.goto(self.SEARCH_URL, wait_until="domcontentloaded", timeout=15000)

                # TODO: validate these selectors against the live site.
                input_handle = await page.query_selector(
                    "input[type='search'], input[name='q'], input[placeholder*='uscar' i]"
                )
                if not input_handle:
                    logger.info("venezuelatebusca: no search input found (selector may need update)")
                    return matches

                await input_handle.fill(query)
                await input_handle.press("Enter")

                try:
                    await page.wait_for_selector("a[href*='/persona'], .result, .card", timeout=10000)
                except Exception:  # noqa: BLE001
                    return matches

                cards = await page.query_selector_all(".result, .card, article, li")
                for card in cards[:20]:
                    text = (await card.inner_text()).strip()
                    if not text or not re.search(re.escape(query[:3]), text, re.IGNORECASE):
                        continue
                    a = await card.query_selector("a[href]")
                    href = (await a.get_attribute("href")) if a else ""
                    if href and not href.startswith("http"):
                        href = f"https://venezuelatebusca.com{href}"
                    matches.append(
                        {
                            "name": text.splitlines()[0][:120],
                            "status": "missing",
                            "last_seen": " — ".join(text.splitlines()[1:3])[:200],
                            "age": None,
                            "source_url": href,
                            "photo_url": None,
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            logger.exception("venezuelatebusca search failed: %s", exc)
        return matches