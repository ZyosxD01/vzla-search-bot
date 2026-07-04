"""venezuelatebusca.com adapter.

The largest registry in the list (69k+ people as of Jul 2026). The site sits
behind a Cloudflare "Just a moment…" interstitial that resolves itself after
a few seconds of real JS execution — no CAPTCHA to solve, just needs a short
wait before querying the DOM (querying too early was the original bug: the
page was still showing the interstitial).

Result cards have no per-record permalink, so source_url points at the
site's own query URL (`/?query=...`), which lands the user on the same
filtered list.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List
from urllib.parse import quote_plus

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)

# Badge text the site renders above/around the name — not part of the name.
_BADGES = {
    "localizada", "localizado", "por localizar",
    "fallecida", "fallecido", "hospitalizada", "hospitalizado",
}

_STATUS_MAP = {
    "por localizar": "missing",
    "localizada": "found",
    "localizado": "found",
    "hospitalizada": "hospitalized",
    "hospitalizado": "hospitalized",
    "fallecida": "deceased",
    "fallecido": "deceased",
}

_DATE_RE = re.compile(r"^\d{1,2}\s+\w+\.?\s+\d{4}", re.IGNORECASE)


def _fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", (s or "").lower())
        if unicodedata.category(c) != "Mn"
    )


class VenezuelaBuscaSearcher(BaseSearcher):
    slug = "venezuelatebusca"
    label = "Venezuela Te Busca"
    url = "https://venezuelatebusca.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with new_page() as page:
                await page.goto(self.url, wait_until="domcontentloaded", timeout=20000)
                # Let the Cloudflare interstitial clear before touching the DOM.
                await page.wait_for_timeout(4000)

                input_handle = await page.query_selector(
                    "input[placeholder*='uscar' i], input[type='search']"
                )
                if not input_handle:
                    logger.info("venezuelatebusca: no search input found (site layout may have changed)")
                    return matches

                await input_handle.fill(query)
                await input_handle.press("Enter")
                await page.wait_for_timeout(2500)

                search_url = f"{self.url}?query={quote_plus(query)}"

                # Cards render as `group/card` containers (Tailwind "group/name"
                # syntax) with no dedicated CSS class — matched via substring.
                cards = await page.query_selector_all("[class*='group/card']:not([class*='group/card-'])")
                for card in cards[:20]:
                    text = (await card.inner_text()).strip()
                    if not text:
                        continue
                    lines = [l.strip() for l in text.split("\n") if l.strip()]

                    idx = 0
                    status = "unknown"
                    while idx < len(lines) and lines[idx].lower() in _BADGES:
                        status = _STATUS_MAP.get(lines[idx].lower(), status)
                        idx += 1
                    if idx >= len(lines):
                        continue

                    name = lines[idx][:120]
                    rest = lines[idx + 1:]
                    date_line = next((l for l in rest if _DATE_RE.match(l)), None)
                    detail_lines = [l for l in rest if l != date_line]
                    last_seen = " — ".join(detail_lines)[:200]

                    matches.append({
                        "name": name,
                        "status": status,
                        "last_seen": last_seen,
                        "age": None,
                        "source_url": search_url,
                        "photo_url": None,
                    })
        except Exception as exc:  # noqa: BLE001
            logger.exception("venezuelatebusca search failed: %s", exc)
        return matches
