"""Platform registry — selects the right adapter by name."""

from __future__ import annotations

import logging
from typing import Any, Dict, Type

from platforms.base import BaseSearcher

logger = logging.getLogger(__name__)

# Lazy registry: import adapters on first use so missing optional deps don't
# block the whole app from booting.
_REGISTRY: Dict[str, Type[BaseSearcher]] = {}

# Sites that follow the common "input + result cards" shape are declared
# here and served by platforms.generic.GenericSearcher — no dedicated file.
GENERIC_SPECS: Dict[str, Dict[str, Any]] = {
    "terremotoenvenezuela": {
        "slug": "terremotoenvenezuela",
        "label": "Terremoto en Venezuela",
        "url": "https://terremotoenvenezuela.com/",
    },
    "busquedavzla": {
        "slug": "busquedavzla",
        "label": "Búsqueda Vzla",
        "url": "https://busquedavzla.netlify.app/",
    },
    "reportevenezuela": {
        "slug": "reportevenezuela",
        "label": "Reporte Venezuela",
        "url": "https://reportevenezuela.com/",
        "search_url": "https://reportevenezuela.com/buscar",
    },
    "pacientesterremoto": {
        "slug": "pacientesterremoto",
        "label": "Pacientes Terremoto Vzla",
        "url": "https://pacientesterremotovzla.lovable.app/",
        "default_status": "hospitalized",
    },
    "pacientesinfo": {
        "slug": "pacientesinfo",
        "label": "Pacientes Info (Osiris Berbesía)",
        "url": "https://osirisberbesia.com/pacientesinfo",
        "default_status": "hospitalized",
    },
    "venezuelaayuda": {
        "slug": "venezuelaayuda",
        "label": "Venezuela Ayuda",
        "url": "https://venezuela-ayuda.org/",
    },
    "huellascan": {
        "slug": "huellascan",
        "label": "HuellaScan (Mascotas)",
        "url": "https://huellascan.com/terremoto",
        "default_status": "pet",
    },
    "crisisve": {
        "slug": "crisisve",
        "label": "CrisisVE",
        "url": "https://crisisve.org/",
        "search_url": "https://crisisve.org/buscar",
    },
}


def _load(name: str) -> Type[BaseSearcher]:
    if name in _REGISTRY:
        return _REGISTRY[name]

    if name == "desaparecidosterremotovenezuela":
        from platforms.desaparecidos import DesaparecidosSearcher
        cls = DesaparecidosSearcher
    elif name == "venezuelatebusca":
        from platforms.venezuelatebusca import VenezuelaBuscaSearcher
        cls = VenezuelaBuscaSearcher
    elif name == "statusvzla":
        from platforms.statusvzla import StatusVzlaSearcher
        cls = StatusVzlaSearcher
    elif name == "icrc":
        from platforms.icrc import ICRCSearcher
        cls = ICRCSearcher
    elif name == "hospitalesenvenezuela":
        from platforms.hospitalesenvenezuela import HospitalesEnVenezuelaSearcher
        cls = HospitalesEnVenezuelaSearcher
    elif name == "redayudavenezuela":
        from platforms.redayudavenezuela import RedAyudaVenezuelaSearcher
        cls = RedAyudaVenezuelaSearcher
    elif name == "venezuelareporta":
        from platforms.venezuelareporta import VenezuelaReportaSearcher
        cls = VenezuelaReportaSearcher
    elif name == "sismo911":
        from platforms.sismo911 import Sismo911Searcher
        cls = Sismo911Searcher
    elif name == "desaparecidosvenezuela":
        from platforms.desaparecidosvenezuela import DesaparecidosVenezuelaSearcher
        cls = DesaparecidosVenezuelaSearcher
    else:
        raise ValueError(f"Unknown platform adapter: {name}")

    _REGISTRY[name] = cls
    return cls


def get_searcher(name: str) -> BaseSearcher:
    """Instantiate a searcher by adapter name."""
    if name in GENERIC_SPECS:
        from platforms.generic import GenericSearcher
        return GenericSearcher(GENERIC_SPECS[name])
    cls = _load(name)
    return cls()
