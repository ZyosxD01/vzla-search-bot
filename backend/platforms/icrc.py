"""ICRC Restoring Family Links adapter.

This is the OFFICIAL international standard for disaster missing-persons
search, run by the International Committee of the Red Cross. It already has
a public form at https://familylinks.icrc.org — using it gives the bot
maximum legitimacy and aligns with the project editorial policy of
preferring verified institutional sources.

TEMPLATE — selectors need validation against the live site.
"""

from __future__ import annotations

import logging
import re
from typing import List, Dict, Any

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)


class ICRCSearcher(BaseSearcher):
    slug = "icrc"
    label = "Cruz Roja — Restoring Family Links"
    url = "https://familylinks.icrc.org/"

    SEARCH_URL = "https://familylinks.icrc.org/es/look-for-missing-persons"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                await page.goto(self.SEARCH_URL, wait_until="domcontentloaded", timeout=15000)

                # TODO: validate selectors against the live site.
                input_handle = await page.query_selector(
                    "input[name='lastName'], input[name='surname'], "
                    "input[name='fullName'], input[type='search']"
                )
                if not input_handle:
                    logger.info("icrc: no search input found")
                    return matches

                await input_handle.fill(query)

                # ICRC form likely has a submit button rather than Enter-to-search.
                submit = await page.query_selector("button[type='submit'], input[type='submit']")
                if submit:
                    await submit.click()
                else:
                    await input_handle.press("Enter")

                try:
                    await page.wait_for_selector(
                        ".result, .person, .missing-person", timeout=10000
                    )
                except Exception:  # noqa: BLE001
                    return matches

                cards = await page.query_selector_all(".result, .person, .missing-person, article")
                for card in cards[:20]:
                    text = (await card.inner_text()).strip()
                    if not text or not re.search(re.escape(query[:3]), text, re.IGNORECASE):
                        continue
                    a = await card.query_selector("a[href]")
                    href = (await a.get_attribute("href")) if a else ""
                    if href and not href.startswith("http"):
                        href = f"https://familylinks.icrc.org{href}"
                    matches.append(
                        {
                            "name": text.splitlines()[0][:120],
                            "status": "missing",
                            "last_seen": "Ver en plataforma",
                            "age": None,
                            "source_url": href or self.SEARCH_URL,
                            "photo_url": None,
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            logger.exception("icrc search failed: %s", exc)
        return matches