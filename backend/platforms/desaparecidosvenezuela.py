"""desaparecidosvenezuela.com adapter.

Not to be confused with desaparecidosterremotovenezuela.com (a different,
older platform already covered by platforms/desaparecidos.py) — this one
covers La Guaira, Caracas, Yaracuy, Aragua and Carabobo separately.

Its search page (`/buscar?q=...`) renders each result as an `<a>` card
(not a `.card`/`.result` div, so the generic adapter's selectors miss it):
the name is the first `<p class="font-medium ...">` inside the anchor,
and the anchor's own href is the direct record permalink.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus, urljoin

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)


class DesaparecidosVenezuelaSearcher(BaseSearcher):
    slug = "desaparecidosvenezuela"
    label = "Desaparecidos Venezuela"
    url = "https://www.desaparecidosvenezuela.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                search_url = f"{self.url}buscar?q={quote_plus(query)}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2500)

                cards = await page.query_selector_all("a:has(p.font-medium)")
                for card in cards[:20]:
                    name_el = await card.query_selector("p.font-medium")
                    name = (await name_el.inner_text()).strip() if name_el else ""
                    if not name:
                        continue

                    full_text = (await card.inner_text()).strip()
                    lines = [l.strip() for l in full_text.split("\n") if l.strip() and l.strip() != name]
                    last_seen = " — ".join(lines[:3])[:200]

                    href = await card.get_attribute("href") or ""
                    source_url = urljoin(self.url, href) if href else self.url

                    status = "found" if "encontrad" in full_text.lower() else "missing"

                    matches.append({
                        "name": name[:120],
                        "status": status,
                        "last_seen": last_seen,
                        "age": None,
                        "source_url": source_url,
                        "photo_url": None,
                    })
        except Exception as exc:  # noqa: BLE001
            logger.exception("desaparecidosvenezuela search failed: %s", exc)
        return matches
