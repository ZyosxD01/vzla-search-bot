"""hospitalesenvenezuela.com adapter.

Purpose-built for one thing: confirming whether someone is admitted at a
hospital after the earthquake. Volunteers register admitted patients; the
site's own search (name/cédula) flags a match with a `.found` card per
result — matched cards already carry patient name, optional age/sector,
and the admitting hospital.

No per-record detail links exist (the site withholds medical status by
design, "por privacidad"), so source_url always points at the search page.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)


class HospitalesEnVenezuelaSearcher(BaseSearcher):
    slug = "hospitalesenvenezuela"
    label = "Hospitales en Venezuela"
    url = "https://hospitalesenvenezuela.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(1500)

                input_handle = await page.query_selector(
                    "input[placeholder*='ombre' i], input[placeholder*='dula' i]"
                )
                if not input_handle:
                    logger.info("hospitalesenvenezuela: no search input found")
                    return matches

                await input_handle.fill(query)
                await input_handle.press("Enter")
                await page.wait_for_timeout(2500)

                cards = await page.query_selector_all(".found")
                for card in cards[:20]:
                    name_el = await card.query_selector(".where")
                    name = (await name_el.inner_text()).strip() if name_el else ""
                    if not name:
                        continue

                    age_el = await card.query_selector(".city")
                    age_sector = (await age_el.inner_text()).strip() if age_el else ""

                    hospital_el = await card.query_selector(".ingreso b")
                    hospital = (await hospital_el.inner_text()).strip() if hospital_el else ""

                    last_seen = " — ".join(v for v in (hospital, age_sector) if v)

                    matches.append({
                        "name": name[:120],
                        "status": "hospitalized",
                        "last_seen": last_seen[:200],
                        "age": None,
                        "source_url": self.url,
                        "photo_url": None,
                    })
        except Exception as exc:  # noqa: BLE001
            logger.exception("hospitalesenvenezuela search failed: %s", exc)
        return matches
