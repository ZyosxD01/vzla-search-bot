"""statusvzla.com adapter — the most feature-rich platform in the list.

It already has a "Búsqueda Cruzada" feature, so this adapter can either:
  (a) call its public search endpoint directly, OR
  (b) render /buscar-persona in Playwright and extract results.

Start with (b) because (a) requires reverse-engineering their API and may
violate their ToS. The site is JS-rendered (Next.js / similar).

TEMPLATE — selectors need validation against the live site.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)


class StatusVzlaSearcher(BaseSearcher):
    slug = "statusvzla"
    label = "StatusVzla"
    url = "https://statusvzla.com/"

    # The site has a dedicated /buscar-persona page — better starting point
    # than the homepage for a federated search.
    SEARCH_URL = "https://statusvzla.com/buscar-persona"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                await page.goto(self.SEARCH_URL, wait_until="domcontentloaded", timeout=15000)

                # TODO: validate selectors against the live site.
                input_handle = await page.query_selector(
                    "input[type='search'], input[name='q'], input[name='nombre']"
                )
                if not input_handle:
                    logger.info("statusvzla: no search input found")
                    return matches

                await input_handle.fill(query)
                await input_handle.press("Enter")

                try:
                    await page.wait_for_selector(
                        ".persona, .result, a[href*='/persona/']", timeout=10000
                    )
                except Exception:  # noqa: BLE001
                    return matches

                # statusvzla likely uses links like /persona/<id> for detail pages.
                links = await page.query_selector_all("a[href*='/persona/']")
                for link in links[:20]:
                    text = (await link.inner_text()).strip()
                    href = await link.get_attribute("href")
                    if not text or not re.search(re.escape(query[:3]), text, re.IGNORECASE):
                        continue
                    if href and not href.startswith("http"):
                        href = f"https://statusvzla.com{href}"
                    matches.append(
                        {
                            "name": text.splitlines()[0][:120],
                            "status": "missing",
                            "last_seen": "Ver en plataforma",
                            "age": None,
                            "source_url": href,
                            "photo_url": None,
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            logger.exception("statusvzla search failed: %s", exc)
        return matches