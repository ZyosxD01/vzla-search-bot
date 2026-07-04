"""ICRC Restoring Family Links adapter.

Verified live (Jul 2026): familylinks.icrc.org does NOT expose a public,
queryable database of missing persons. `/es/look-for-missing-persons` 404s,
and the site's real "Online Tracing" page (`/index.php/online-tracing`) is
an informational FAQ/accordion with no search form — by design, ICRC
gates tracing requests through National Red Cross societies for the
protection of the people being searched for.

So there is nothing to scrape here. This adapter is kept in the platform
list (and in resources.py) purely as the official humanitarian channel:
it always returns no matches, and the bot points people to the site
directly as a next step rather than pretending to search it.
"""

from __future__ import annotations

from typing import Any, Dict, List

from platforms.base import BaseSearcher


class ICRCSearcher(BaseSearcher):
    slug = "icrc"
    label = "Cruz Roja — Restoring Family Links"
    url = "https://familylinks.icrc.org/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        return []
