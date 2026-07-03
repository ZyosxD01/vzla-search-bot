"""Base interface every platform adapter must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseSearcher(ABC):
    """A federated search adapter for one missing-persons platform.

    Subclasses MUST set:
      - slug: internal id used in the API
      - label: human-readable platform name shown to users
      - url:  canonical homepage, shown as attribution in results

    Subclasses MUST implement `async search(query) -> list[dict]`.

    Returned match dicts should follow this shape (extra fields are allowed):
      {
        "name": str,            # full name as shown on the source platform
        "status": str,          # "missing" | "found" | "hospitalized" | "unknown"
        "last_seen": str,       # free-text location / context
        "age": Optional[int],
        "source_url": str,      # direct link to the record on the source platform
        "photo_url": Optional[str],
        "extra": Optional[Dict[str, Any]],
      }
    """

    slug: str = ""
    label: str = ""
    url: str = ""

    @abstractmethod
    async def search(self, query: str) -> List[Dict[str, Any]]:
        """Run a live search against the platform. Return [] on no match."""
        raise NotImplementedError