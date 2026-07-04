"""venezuelareporta.org adapter.

This platform runs a documented, open, no-auth, CORS-open public API
(https://venezuelareporta.org/api-abierta) that itself aggregates several
sibling platforms (venezuelatebusca, hospital lists parsed with AI, etc.).
Calling the API directly is both the platform's own recommended integration
path and far more accurate than scraping its Next.js frontend, which
renders results inside a shadow root that plain CSS selectors can't reach.

GET https://venezuelareporta.org/api/v1/personas?q=<query>&limit=100
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from platforms.base import BaseSearcher

logger = logging.getLogger(__name__)

API_URL = "https://venezuelareporta.org/api/v1/personas"
HEADERS = {"User-Agent": "Mozilla/5.0 (vzla-search-bot humanitarian)"}

_STATUS_MAP = {
    "buscando": "missing",
    "a_salvo": "found",
    "encontrado": "found",
    "fallecido": "deceased",
}


class VenezuelaReportaSearcher(BaseSearcher):
    slug = "venezuelareporta"
    label = "Venezuela Reporta"
    url = "https://venezuelareporta.org/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
                resp = await client.get(API_URL, params={"q": query, "limit": 50})
                resp.raise_for_status()
                data = resp.json()

            for p in data.get("personas", []):
                name = (p.get("nombre") or "").strip()
                if not name:
                    continue

                last_seen = " — ".join(
                    v for v in (p.get("ciudad"), p.get("zona"), p.get("ultima_vez")) if v
                )

                matches.append({
                    "name": name[:120],
                    "status": _STATUS_MAP.get(p.get("status"), "unknown"),
                    "last_seen": last_seen[:200],
                    "age": p.get("edad"),
                    "source_url": p.get("ficha_url") or self.url,
                    "photo_url": p.get("foto_url") or None,
                })
        except Exception as exc:  # noqa: BLE001
            logger.exception("venezuelareporta search failed: %s", exc)
        return matches
