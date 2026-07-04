"""statusvzla.com adapter.

StatusVzla is a Base44-built app. Its "search" page (/buscar-persona) is
actually the intake FORM for reporting a missing person, not a query page —
filling and submitting it would have created a fake report on their live
database. The real data lives behind the app's own public read API, which
the site itself calls from the browser (no auth required):

    https://statusvzla.com/api/apps/<app_id>/entities/<Entity>

This adapter calls that API directly with httpx instead of driving a
browser, which is both more accurate (structured fields, no guessed CSS
selectors) and lighter (no Chromium context needed for this platform).

Entities queried:
  - PersonasBuscadas   — community "missing" reports
  - PersonaRegistrada  — people checked into a shelter/hospital by staff
  - PersonaCRIS        — the CRIS registry (people with no ID, injured, etc.)
  - PersonasEncontradas — community "found someone" reports
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List

import httpx

from platforms.base import BaseSearcher

logger = logging.getLogger(__name__)

APP_ID = "6a3ddf29c9e933d4c38e9646"
API_BASE = f"https://statusvzla.com/api/apps/{APP_ID}/entities"
HEADERS = {"User-Agent": "Mozilla/5.0 (vzla-search-bot humanitarian)"}
FETCH_LIMIT = 300

# entity -> (name field(s), location field(s), phone field(s), status field, status map)
_ENTITY_SPECS = {
    "PersonasBuscadas": {
        "name_fields": ["nombre_completo", "apodo"],
        "loc_fields": ["ultima_ubicacion_conocida", "ciudad", "estado_region"],
        "phone_fields": ["contacto_telefono", "telefono_persona"],
        "status_field": "estado_caso",
        "status_map": {"buscando": "missing", "encontrado": "found",
                       "fallecido_reportado": "deceased"},
    },
    "PersonaRegistrada": {
        "name_fields": ["nombre_completo"],
        "loc_fields": ["institucion_nombre", "ciudad", "estado_region"],
        "phone_fields": ["telefono_contacto", "telefono_destino"],
        "status_field": "condicion",
        "status_map": {"a_salvo": "found", "herido_leve": "hospitalized",
                       "herido_grave": "hospitalized",
                       "fallecido_reportado": "deceased", "no_sabe": "unknown"},
    },
    "PersonaCRIS": {
        "name_fields": ["nombre", "apellido", "apodo"],
        "loc_fields": ["ubicacion_texto", "centro_apoyo", "ciudad", "estado_region"],
        "phone_fields": ["avisar_telefono"],
        "status_field": "estado_actual",
        "status_map": {"a_salvo": "found", "estoy_aqui": "found",
                       "necesita_ayuda": "hospitalized"},
    },
    "PersonasEncontradas": {
        "name_fields": ["nombre_o_descripcion"],
        "loc_fields": ["ubicacion_actual", "nombre_lugar", "ciudad"],
        "phone_fields": ["telefono_contacto"],
        "status_field": None,
        "status_map": {},
    },
}


def _fold(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", (s or "").lower())
        if unicodedata.category(c) != "Mn"
    )


def _first_nonempty(record: Dict[str, Any], fields: List[str]) -> str:
    for f in fields:
        v = (record.get(f) or "").strip() if isinstance(record.get(f), str) else record.get(f)
        if v:
            return str(v).strip()
    return ""


class StatusVzlaSearcher(BaseSearcher):
    slug = "statusvzla"
    label = "StatusVzla"
    url = "https://statusvzla.com/"

    async def search(self, query: str) -> List[Dict[str, Any]]:
        matches: List[Dict[str, Any]] = []
        query_words = [w for w in re.findall(r"\w+", _fold(query)) if len(w) >= 3]
        if not query_words:
            return matches

        try:
            async with httpx.AsyncClient(timeout=15, headers=HEADERS) as client:
                for entity, spec in _ENTITY_SPECS.items():
                    try:
                        resp = await client.get(
                            f"{API_BASE}/{entity}",
                            params={"sort": "-updated_date", "limit": FETCH_LIMIT},
                        )
                        resp.raise_for_status()
                        records = resp.json()
                    except Exception as exc:  # noqa: BLE001
                        logger.warning("statusvzla: %s fetch failed: %s", entity, exc)
                        continue

                    for record in records:
                        name = _first_nonempty(record, spec["name_fields"])
                        if not name:
                            continue
                        name_folded = _fold(name)
                        hits = sum(1 for w in query_words if w in name_folded)
                        if hits / len(query_words) < 0.5:
                            continue

                        raw_status = record.get(spec["status_field"]) if spec["status_field"] else None
                        status = spec["status_map"].get(raw_status, "unknown")

                        last_seen = " — ".join(
                            v for v in (
                                _first_nonempty(record, [f]) for f in spec["loc_fields"]
                            ) if v
                        )
                        phone = _first_nonempty(record, spec["phone_fields"]) or None
                        record_id = record.get("id", "")

                        matches.append({
                            "name": name,
                            "status": status,
                            "last_seen": last_seen[:200],
                            "age": None,
                            "source_url": (
                                f"https://statusvzla.com/persona?id={record_id}"
                                if record_id else self.url
                            ),
                            "photo_url": record.get("foto_url") or None,
                            "phone": phone,
                        })
        except Exception as exc:  # noqa: BLE001
            logger.exception("statusvzla search failed: %s", exc)
        return matches
