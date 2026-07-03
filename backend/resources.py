"""Emergency resource directory — Terremoto Venezuela 24 junio 2026.

Centralized, categorized directory appended to every chat response so a
desperate family member always leaves with concrete next steps, even when
the search returns no matches. Only entries with a verifiable URL or phone
number are listed — never invent a resource.
"""

from __future__ import annotations

EMERGENCY_PHONES = [
    ("911", "Protección Civil"),
    ("0800-LOJUSTO (0800-659-8786)", "CICPC — personas desaparecidas"),
    ("0212-532-5050", "Venemergencia"),
]

# (label, url) per category. Shown in responses and in the frontend directory.
RESOURCES = {
    "hospitalizados": [
        ("Pacientes Terremoto Vzla", "https://pacientesterremotovzla.lovable.app/"),
        ("Directorio de hospitales", "https://hospitalesenvenezuela.com/"),
        ("Pacientes Info", "https://osirisberbesia.com/pacientesinfo"),
    ],
    "refugios_ayuda": [
        ("Venezuela Ayuda (portal integral)", "https://venezuela-ayuda.org/"),
        ("Ayuda Venezuela 2026", "https://ayudavenezuela2026.com/"),
        ("Ayuda para Venezuela", "https://ayudaparavenezuela.com/"),
        ("Rescate", "https://ayudavenezuela.app/rescate"),
        ("Refugios Venezuela", "https://refugiosvenezuela.com/"),
        ("Red Ayuda Venezuela", "https://redayudavenezuela.com/"),
    ],
    "mascotas": [
        ("HuellaScan (reconocimiento de huellas)", "https://huellascan.com/terremoto"),
    ],
    "oficiales": [
        ("Protección Civil", "https://pcivil.gob.ve/"),
        ("Cruz Roja — Restoring Family Links", "https://familylinks.icrc.org/"),
        ("OCHA (ONU)", "https://unocha.org/"),
        ("OIM", "https://iom.int/venezuela-earthquake-response"),
        ("ACNUR", "https://unhcr.org/"),
    ],
}


def resources_block(lang: str) -> str:
    """Compact next-steps block appended to every response.

    Kept short on purpose — the chat must not drown the person in text.
    The full categorized directory lives in the frontend.
    """
    if lang == "es":
        return "\n".join([
            "QUÉ HACER AHORA:",
            "☎ 911 (Protección Civil) · 0800-659-8786 (CICPC desaparecidos) · 0212-532-5050 (Venemergencia)",
            "• Registra el reporte: https://desaparecidosterremotovenezuela.com/",
            "• ¿Puede estar herido? https://pacientesterremotovzla.lovable.app/",
            "• Cruz Roja internacional: https://familylinks.icrc.org/",
        ])
    return "\n".join([
        "WHAT TO DO NOW:",
        "☎ 911 (Civil Protection) · 0800-659-8786 (CICPC missing persons) · 0212-532-5050 (Venemergencia)",
        "• Register the report: https://desaparecidosterremotovenezuela.com/",
        "• Could they be injured? https://pacientesterremotovzla.lovable.app/",
        "• International Red Cross: https://familylinks.icrc.org/",
    ])
