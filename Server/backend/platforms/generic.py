"""Generic heuristic adapter for missing-person search sites.

Many community platforms follow the same shape: a search input on the
landing page and a list of result cards. This adapter navigates, tries a
set of common input selectors, submits the query, and extracts cards that
actually mention the queried name.

Each site is declared as a spec dict in `platforms/__init__.py` — no new
code needed to add a platform unless its DOM is unusual, in which case a
dedicated adapter file (like icrc.py) is the right tool.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List

from platforms.base import BaseSearcher
from platforms._browser import new_page

logger = logging.getLogger(__name__)

INPUT_SELECTORS = (
    "input[type='search'], input[name='q'], input[name='query'], "
    "input[name='nombre'], input[name='name'], input[name='search'], "
    "input[placeholder*='uscar' i], input[placeholder*='ombre' i], "
    "input[placeholder*='earch' i], input[type='text']"
)

CARD_SELECTORS = ".result, .card, article, li, tr, [class*='result'], [class*='card']"

# Venezuelan phone formats: 0412-1234567, +58 412..., 0212..., 0800-LOJUSTO.
PHONE_RE = re.compile(
    r"(\+58[\s.\-]?\d{3}[\s.\-]?\d{7}"
    r"|\b0(?:412|414|416|422|424|426|2\d{2})[\s.\-]?\d{7}\b"
    r"|\b0800[\s.\-]?[A-Z0-9]{4,10}\b)",
    re.IGNORECASE,
)


def _fold(s: str) -> str:
    """Lowercase + strip accents so 'María' matches 'maria'."""
    return "".join(
        c for c in unicodedata.normalize("NFD", s.lower())
        if unicodedata.category(c) != "Mn"
    )


class GenericSearcher(BaseSearcher):
    """Configurable heuristic searcher. See module docstring."""

    def __init__(self, spec: Dict[str, Any]) -> None:
        self.slug = spec["slug"]
        self.label = spec["label"]
        self.url = spec["url"]
        self.search_url = spec.get("search_url", spec["url"])
        self.default_status = spec.get("default_status", "missing")

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        # Longest token of the query drives matching — a surname beats "de".
        tokens = [t for t in re.findall(r"\w+", _fold(query)) if len(t) >= 3]
        needle = max(tokens, key=len) if tokens else _fold(query).strip()

        try:
            async with new_page() as page:
                await page.goto(self.search_url, wait_until="domcontentloaded", timeout=15000)

                input_handle = await page.query_selector(INPUT_SELECTORS)
                if not input_handle:
                    logger.info("%s: no search input found", self.slug)
                    return matches

                await input_handle.fill(query)
                await input_handle.press("Enter")
                # Give client-side apps a moment to render results.
                await page.wait_for_timeout(3500)

                cards = await page.query_selector_all(CARD_SELECTORS)
                seen: set = set()
                for card in cards[:60]:
                    text = (await card.inner_text()).strip()
                    # Match against the card head only — a container listing many
                    # records mentions the name somewhere inside, but a real
                    # record card carries it in its first lines.
                    head = "\n".join(text.splitlines()[:3])
                    if not text or needle not in _fold(head):
                        continue
                    first_line = text.splitlines()[0][:120]
                    key = _fold(first_line)  # dedupe accent/case variants
                    if key in seen:
                        continue
                    seen.add(key)

                    # Deep link to the record itself — never the site index.
                    href = ""
                    for a in await card.query_selector_all("a[href]"):
                        cand = (await a.get_attribute("href")) or ""
                        if cand in ("", "#", "/") or cand.startswith(("javascript:", "mailto:")):
                            continue
                        if not cand.startswith("http"):
                            base = self.url.rstrip("/")
                            cand = f"{base}{cand if cand.startswith('/') else '/' + cand}"
                        # A link back to the homepage is not a record link.
                        if cand.rstrip("/") == self.url.rstrip("/"):
                            continue
                        href = cand
                        break

                    phone_m = PHONE_RE.search(text)

                    matches.append(
                        {
                            "name": first_line,
                            "status": self.default_status,
                            "last_seen": " — ".join(text.splitlines()[1:3])[:200],
                            "age": None,
                            "source_url": href or self.url,  # "" → formatter falls back to platform URL
                            "photo_url": None,
                            "phone": phone_m.group(1).strip() if phone_m else None,
                        }
                    )
                    if len(matches) >= 10:
                        break
        except Exception as exc:  # noqa: BLE001
            logger.exception("%s search failed: %s", self.slug, exc)
        return matches
