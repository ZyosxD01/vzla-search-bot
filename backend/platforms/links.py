"""Direct deep-link generator for Venezuelan disaster response platforms.

Instead of scraping each platform (which is expensive, fragile, and slow),
this module builds pre-filled search URLs that take the user straight to
the platform's own search box with the query already typed in.

No databases, no scraping, no Playwright — just URL templates.

NOTE: URL patterns are best-guess and should be validated against each
platform. Open DevTools, search for a name, copy the resulting URL
format, and update the matching entry below.
"""

from typing import Any, Dict, List
from urllib.parse import quote_plus


PLATFORMS = [
    # --- Personas desaparecidas / encontradas ---
    {
        "slug": "desaparecidosterremotovenezuela",
        "label": "Desaparecidos Terremoto Venezuela",
        "url": "https://desaparecidosterremotovenezuela.com/",
        "search_url": "https://desaparecidosterremotovenezuela.com/?s={q}",
        "category": "personas",
        "description": "26,000+ reportes · reconocimiento facial",
    },
    {
        "slug": "venezuelatebusca",
        "label": "Venezuela Te Busca",
        "url": "https://venezuelatebusca.com/",
        "search_url": "https://venezuelatebusca.com/?s={q}",
        "category": "personas",
        "description": "10,000+ reportes · la más citada en prensa",
    },
    {
        "slug": "statusvzla",
        "label": "StatusVzla",
        "url": "https://statusvzla.com/",
        "search_url": "https://statusvzla.com/buscar-persona?q={q}",
        "category": "personas",
        "description": "Búsqueda cruzada + Directorio de Encontrados",
    },
    {
        "slug": "terremotoenvenezuela",
        "label": "Terremoto en Venezuela",
        "url": "https://terremotoenvenezuela.com/",
        "search_url": "https://terremotoenvenezuela.com/?s={q}",
        "category": "personas",
        "description": "Unifica desaparecidos + localizados + acopio",
    },
    {
        "slug": "busquedavzla",
        "label": "Búsqueda Vzla",
        "url": "https://busquedavzla.netlify.app/",
        "search_url": "https://busquedavzla.netlify.app/?q={q}",
        "category": "personas",
    },
    {
        "slug": "rescateve",
        "label": "Rescate VE",
        "url": "https://rescate-ve.vercel.app/",
        "search_url": "https://rescate-ve.vercel.app/?q={q}",
        "category": "personas",
    },
    {
        "slug": "venapp",
        "label": "VenApp",
        "url": "https://venapp.com/",
        "search_url": "https://venapp.com/?q={q}",
        "category": "personas",
    },
    {
        "slug": "reportevenezuela",
        "label": "Reporte Venezuela",
        "url": "https://reportevenezuela.com/",
        "search_url": "https://reportevenezuela.com/?s={q}",
        "category": "personas",
    },

    # --- Hospitalizados / pacientes ---
    {
        "slug": "pacientesterremoto",
        "label": "Pacientes Terremoto Vzla",
        "url": "https://pacientesterremotovzla.lovable.app/",
        "search_url": "https://pacientesterremotovzla.lovable.app/?q={q}",
        "category": "hospitalizados",
    },
    {
        "slug": "pacientesinfo",
        "label": "Pacientes Info",
        "url": "https://osirisberbesia.com/pacientesinfo/",
        "search_url": "https://osirisberbesia.com/pacientesinfo/?s={q}",
        "category": "hospitalizados",
    },
    {
        "slug": "hospitalesenvenezuela",
        "label": "Hospitales en Venezuela",
        "url": "https://hospitalesenvenezuela.com/",
        "search_url": "https://hospitalesenvenezuela.com/?s={q}",
        "category": "hospitalizados",
    },

    # --- Acopio / ayuda / refugios ---
    {
        "slug": "venezuelaayuda",
        "label": "Venezuela Ayuda",
        "url": "https://venezuela-ayuda.org/",
        "search_url": "https://venezuela-ayuda.org/?s={q}",
        "category": "acopio",
    },
    {
        "slug": "ayudavenezuela2026",
        "label": "Ayuda Venezuela 2026",
        "url": "https://ayudavenezuela2026.com/",
        "search_url": "https://ayudavenezuela2026.com/?s={q}",
        "category": "acopio",
    },
    {
        "slug": "ayudaparavenezuela",
        "label": "Ayuda para Venezuela",
        "url": "https://ayudaparavenezuela.com/",
        "search_url": "https://ayudaparavenezuela.com/?s={q}",
        "category": "acopio",
    },
    {
        "slug": "refugiosvenezuela",
        "label": "Refugios Venezuela",
        "url": "https://refugiosvenezuela.com/",
        "search_url": "https://refugiosvenezuela.com/?s={q}",
        "category": "acopio",
    },
    {
        "slug": "redayudavenezuela",
        "label": "Red Ayuda Venezuela",
        "url": "https://redayudavenezuela.com/",
        "search_url": "https://redayudavenezuela.com/?s={q}",
        "category": "acopio",
    },

    # --- Mascotas ---
    {
        "slug": "huellascan",
        "label": "Huellas (mascotas)",
        "url": "https://huellascan.com/terremoto",
        "search_url": "https://huellascan.com/terremoto?q={q}",
        "category": "mascotas",
    },

    # --- Estándar internacional ---
    {
        "slug": "icrc",
        "label": "Cruz Roja Internacional (ICRC)",
        "url": "https://familylinks.icrc.org/",
        "search_url": "https://familylinks.icrc.org/es/look-for-missing-persons",
        "category": "estandar",
        "description": "Restoring Family Links · estándar global",
    },
]


CATEGORY_LABELS = {
    "es": {
        "personas": "👤 PERSONAS DESAPARECIDAS / ENCONTRADAS",
        "hospitalizados": "🏥 HOSPITALIZADOS / PACIENTES",
        "acopio": "📦 ACOPIO / AYUDA / REFUGIOS",
        "mascotas": "🐾 MASCOTAS",
        "estandar": "📡 ESTÁNDAR INTERNACIONAL",
    },
    "en": {
        "personas": "👤 MISSING / FOUND PERSONS",
        "hospitalizados": "🏥 HOSPITALIZED / PATIENTS",
        "acopio": "📦 SUPPLIES / AID / SHELTERS",
        "mascotas": "🐾 PETS",
        "estandar": "📡 INTERNATIONAL STANDARD",
    },
}


def generate_search_links(query: str) -> List[Dict[str, Any]]:
    """Build the list of platforms with their pre-filled search URLs."""
    encoded = quote_plus(query)
    links = []
    for p in PLATFORMS:
        search_url = p["search_url"].format(q=encoded)
        links.append({
            "platform": p["slug"],
            "platform_label": p["label"],
            "platform_url": p["url"],
            "search_url": search_url,
            "category": p["category"],
            "description": p.get("description", ""),
        })
    return links


def group_by_category(links: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Group links by category, preserving the order from PLATFORMS."""
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for link in links:
        groups.setdefault(link["category"], []).append(link)
    return groups


def render_response(query: str, lang: str = "es") -> str:
    """Human-readable bilingual response with all the deep links."""
    links = generate_search_links(query)
    groups = group_by_category(links)
    labels = CATEGORY_LABELS.get(lang, CATEGORY_LABELS["es"])

    if lang == "en":
        intro = (
            f"I understand how hard this moment is.\n\n"
            f"🔍 To search for «{query}» across {len(links)} platforms — "
            f"click each link, your query is already typed in:\n"
        )
        steps = (
            "\n📝 RECOMMENDED STEPS\n"
            "1. Call the Red Cross (0800-659-8786) to file the report\n"
            "2. Open each link below — search in order: missing persons first, hospitals second\n"
            "3. If you find anything, note the record ID and contact the platform directly\n"
        )
        phones = (
            "\n📞 EMERGENCY PHONE LINES\n"
            "• 911 — Protección Civil (Civil Protection)\n"
            "• 0800-659-8786 — CICPC desaparecidos (missing persons)\n"
            "• 0212-532-5050 — Venemergencia\n"
        )
        closing = "\nAlways verify the status on the original source."
    else:
        intro = (
            f"Entiendo lo difícil que es este momento.\n\n"
            f"🔍 Para buscar a «{query}» en {len(links)} plataformas — "
            f"hacé clic en cada link, tu búsqueda ya está escrita:\n"
        )
        steps = (
            "\n📝 PASOS RECOMENDADOS\n"
            "1. Llamá al 0800-659-8786 para registrar el reporte\n"
            "2. Visitá cada link abajo — buscá en orden: primero desaparecidos, después hospitales\n"
            "3. Si encontrás algo, anotá el ID del registro y contactá directamente a la plataforma\n"
        )
        phones = (
            "\n📞 TELÉFONOS DE EMERGENCIA\n"
            "• 911 — Protección Civil\n"
            "• 0800-659-8786 (CICPC desaparecidos)\n"
            "• 0212-532-5050 (Venemergencia)\n"
        )
        closing = "\nVerifica siempre el estado en la fuente original."

    lines = [intro]
    for cat, items in groups.items():
        lines.append(labels.get(cat, cat))
        for item in items:
            desc = f"  · {item['description']}" if item.get("description") else ""
            lines.append(f"  • {item['platform_label']}{desc}")
            lines.append(f"    {item['search_url']}")
        lines.append("")
    lines.append(phones)
    lines.append(steps)
    lines.append(closing)

    return "\n".join(lines).strip()