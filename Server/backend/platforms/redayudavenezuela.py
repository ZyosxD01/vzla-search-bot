"""redayudavenezuela.com adapter.

This platform runs its own chat-style search assistant (name or photo) over
its combined missing/hospitalized/found registries (~55k+ combined records
as of Jul 2026). Typing a name into its search box and pressing Enter drives
that assistant and renders one result button per match, each holding two
`<p>` lines: the person's name (`font-semibold`) and a status/location line
("En un hospital — <place>", "Desaparecido — <place>", etc).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)

_STATUS_KEYWORDS = (
    ("fallecid", "deceased"),
    ("encontr", "found"),
    ("hospital", "hospitalized"),
    ("desaparecid", "missing"),
)


def _map_status(detail: str) -> str:
    lowered = detail.lower()
    for keyword, status in _STATUS_KEYWORDS:
        if keyword in lowered:
            return status
    return "unknown"


class RedAyudaVenezuelaSearcher(BaseSearcher):
    slug = "redayudavenezuela"
    label = "Red Ayuda Venezuela"
    url = "https://redayudavenezuela.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(1500)

                input_handle = await page.query_selector("input[placeholder*='ombre' i]")
                if not input_handle:
                    logger.info("redayudavenezuela: no search input found")
                    return matches

                await input_handle.fill(query)
                await input_handle.press("Enter")
                await page.wait_for_timeout(3000)

                cards = await page.query_selector_all("button:has(p.truncate.font-semibold)")
                for card in cards[:20]:
                    ps = await card.query_selector_all("p")
                    if not ps:
                        continue
                    name = (await ps[0].inner_text()).strip()
                    detail = (await ps[1].inner_text()).strip() if len(ps) > 1 else ""
                    if not name:
                        continue

                    matches.append({
                        "name": name[:120],
                        "status": _map_status(detail),
                        "last_seen": detail.split("—", 1)[-1].strip()[:200] if "—" in detail else detail[:200],
                        "age": None,
                        "source_url": self.url,
                        "photo_url": None,
                    })
        except Exception as exc:  # noqa: BLE001
            logger.exception("redayudavenezuela search failed: %s", exc)
        return matches
