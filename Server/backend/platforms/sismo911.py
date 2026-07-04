"""sismo911.com adapter.

The largest aggregator found (115k+ cases as of Jul 2026, itself pulling
from desaparecidosterremotovenezuela.com, venezuelareporta.org,
terremotovenezuela.app and hospital master lists). Its own frontend calls a
plain, unauthenticated JSON endpoint with server-side name filtering —
using it directly is both simpler and more accurate than scraping the
rendered page.

GET https://sismo911.com/api/persons/cases?q=<query>&limit=50&sort=recent

Because this aggregates sources we already query directly (e.g.
desaparecidosterremotovenezuela.com), expect some duplicate people to show
up under two platform names in the same search — that's a tradeoff of
using an aggregator, not a bug.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from platforms.base import BaseSearcher

logger = logging.getLogger(__name__)

API_URL = "https://sismo911.com/api/persons/cases"
HEADERS = {"User-Agent": "Mozilla/5.0 (vzla-search-bot humanitarian)"}

_STATUS_MAP = {
    "missing": "missing",
    "found_safe": "found",
    "aparecido": "found",
    "hospitalizado": "hospitalized",
    "found_deceased": "deceased",
    "unknown": "unknown",
}


class Sismo911Searcher(BaseSearcher):
    slug = "sismo911"
    label = "SISMO911"
    url = "https://sismo911.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
                resp = await client.get(
                    API_URL, params={"q": query, "limit": 50, "sort": "recent"}
                )
                resp.raise_for_status()
                data = resp.json()

            for c in data.get("cases", []):
                name = (c.get("full_name") or "").strip()
                if not name:
                    continue

                case_id = c.get("id", "")
                matches.append({
                    "name": name[:120],
                    "status": _STATUS_MAP.get(c.get("status"), "unknown"),
                    "last_seen": (c.get("last_seen") or "")[:200],
                    "age": c.get("age"),
                    "source_url": (
                        f"https://sismo911.com/casos#caso={case_id}"
                        if case_id else self.url
                    ),
                    "photo_url": c.get("photo_url") or None,
                })
        except Exception as exc:  # noqa: BLE001
            logger.exception("sismo911 search failed: %s", exc)
        return matches
