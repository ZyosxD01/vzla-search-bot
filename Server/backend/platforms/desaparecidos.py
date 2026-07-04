"""Adapter for desaparecidosterremotovenezuela.com — comprehensive scrape.

Strategy: scroll the homepage to lazy-load as many person cards as
possible, then filter client-side by the user query.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from platforms.base import BaseSearcher
from platforms._browser import new_page


_STATUS_MAP = {
    "sin contacto": "missing",
    "localizado": "found",
    "localizada": "found",
    "en hospital": "hospitalized",
    "hospitalizado": "hospitalized",
    "hospitalizada": "hospitalized",
    "fallecido": "deceased",
    "fallecida": "deceased",
    "en centro": "in_center",
}

# JS code to extract a link URL from a card element. Defined outside the
# async method so it survives any quoting/escaping issues with the heredoc.
_FIND_LINK_JS = (
    "el => { const link = el.closest('a') || el.querySelector('a');"
    " return link ? link.href : null; }"
)


class DesaparecidosSearcher(BaseSearcher):
    slug = "desaparecidosterremotovenezuela"
    label = "Desaparecidos Terremoto Venezuela"
    url = "https://desaparecidosterremotovenezuela.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                await page.goto(self.url, wait_until="networkidle", timeout=30000)
                await page.wait_for_timeout(2500)

                # Scroll to trigger lazy loading
                for _ in range(6):
                    await page.evaluate("window.scrollBy(0, window.innerHeight)")
                    await page.wait_for_timeout(800)
                await page.evaluate("window.scrollTo(0, 0)")
                await page.wait_for_timeout(500)

                cards = await page.query_selector_all("[class*=\"styles_card\"]")
                query_lc = query.lower().strip()

                for card in cards:
                    try:
                        name_el = await card.query_selector("[class*=\"styles_name\"]")
                        name = (await name_el.inner_text()).strip() if name_el else ""

                        body_el = await card.query_selector("[class*=\"styles_body\"]")
                        body_text = (await body_el.inner_text()).strip() if body_el else ""

                        searchable = (name + " " + body_text).lower()
                        if query_lc not in searchable:
                            continue

                        badge_el = await card.query_selector("[class*=\"styles_badge\"]")
                        badge_text = (await badge_el.inner_text()).strip() if badge_el else ""
                        status = "unknown"
                        for key, value in _STATUS_MAP.items():
                            if key in badge_text.lower():
                                status = value
                                break

                        photo_el = await card.query_selector("[class*=\"styles_photo\"]")
                        photo_url = await photo_el.get_attribute("src") if photo_el else None

                        href = await card.evaluate(_FIND_LINK_JS)
                        source_url = href or self.url

                        last_seen = body_text.replace(name, "").strip()
                        for line in last_seen.split("\n"):
                            line = line.strip()
                            if line and len(line) > 4:
                                last_seen = line
                                break

                        matches.append({
                            "name": name,
                            "status": status,
                            "last_seen": last_seen[:200],
                            "age": None,
                            "source_url": source_url,
                            "photo_url": photo_url,
                        })
                    except Exception:
                        continue
        except Exception:
            raise
        return matches
