"""Bilingual response formatting via the MiniMax AI API.

Wraps the user query + raw platform results in a humanitarian-tone system
prompt and asks MiniMax to produce a concise, attribution-respecting answer
in both Spanish and English. If the AI call fails (rate limit, network,
missing key), we fall back to a deterministic template so the bot still
returns something useful.
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, List, Tuple

import httpx

from resources import resources_block

if TYPE_CHECKING:
    from app import PlatformResult

logger = logging.getLogger(__name__)

MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_BASE_URL = os.environ.get("MINIMAX_BASE_URL", "https://api.minimaxi.chat/v1")
MINIMAX_MODEL = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")

SYSTEM_PROMPT = """Eres un asistente humanitario que ayuda a buscar personas desaparecidas
tras el terremoto de Venezuela del 24 de junio de 2026. Tu tono es empático,
claro, breve y respetuoso.

La persona que escribe está desesperada buscando a un familiar. Empieza SIEMPRE
con una línea breve de empatía y calma (sin dramatismo), y termina SIEMPRE con
pasos concretos: registrar el reporte, llamar al 911, al 0800-LOJUSTO
(0800-659-8786, CICPC desaparecidos) y al 0212-532-5050 (Venemergencia), y
revisar hospitalizados si puede estar herido.

Reglas estrictas que SIEMPRE debes cumplir:
1. NUNCA inventes datos. Solo reporta lo que aparece textualmente en los resultados.
2. Menciona SOLO las plataformas que tuvieron coincidencias — NO llenes el chat
   listando las que no encontraron nada; resúmelas en una línea
   ("También busqué en otras N plataformas sin coincidencias").
3. Para cada coincidencia usa el enlace DIRECTO a la publicación (source_url);
   solo usa la portada de la plataforma si no hay enlace directo.
4. Si la coincidencia trae un teléfono de información (campo "phone"),
   inclúyelo visible en la respuesta.
5. Si no hay coincidencias, dilo claramente en 2-3 líneas y sugiere dónde más
   buscar (usa los recursos del campo "resources" del JSON de entrada).
6. NO uses formato markdown pesado — solo texto plano con líneas cortas.
7. Si una plataforma dio error, mencionalo brevemente y sigue con las otras.
8. NO des falsas esperanzas. Si una persona aparece como "missing" en la fuente,
   repite ese estado literalmente.
9. Incluye siempre una línea final recordando verificar en la fuente original.

Vas a recibir resultados en JSON con esta forma:
{
  "query": "...",
  "language_hint": "es" | "en",
  "results": [
    {
      "platform": "...", "platform_label": "...", "platform_url": "...",
      "matches": [{"name": "...", "status": "...", "last_seen": "...", "source_url": "...", "phone": null | "..."}],
      "error": null | "..."
    }
  ]
}

Devuelve EXCLUSIVAMENTE un JSON con esta forma exacta (sin comentarios, sin markdown):
{
  "es": "texto en español, máximo 400 palabras",
  "en": "text in English, max 400 words"
}
"""


async def format_results(
    query: str,
    results: List[PlatformResult],
    language_hint: str,
) -> Tuple[str, str]:
    """Return (formatted_es, formatted_en) text for the chat response."""
    if not MINIMAX_API_KEY:
        logger.warning("MINIMAX_API_KEY not set — using deterministic template")
        return _deterministic_template(query, results)

    payload_results = []
    for r in results:
        payload_results.append(
            {
                "platform": r.platform,
                "platform_label": r.platform_label,
                "platform_url": r.platform_url,
                "matches": r.matches,
                "error": r.error,
            }
        )

    user_payload = json.dumps(
        {
            "query": query,
            "language_hint": language_hint,
            "results": payload_results,
            "resources": {
                "es": resources_block("es"),
                "en": resources_block("en"),
            },
        },
        ensure_ascii=False,
    )

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{MINIMAX_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {MINIMAX_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MINIMAX_MODEL,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_payload},
                    ],
                    "temperature": 0.2,
                    "max_tokens": 1200,
                    "response_format": {"type": "json_object"},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
        )
        parsed = json.loads(content)
        return (
            str(parsed.get("es", "")).strip(),
            str(parsed.get("en", "")).strip(),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("MiniMax API call failed: %s — falling back to template", exc)
        return _deterministic_template(query, results)


def _deterministic_template(query: str, results: List[PlatformResult]) -> Tuple[str, str]:
    """Fallback formatter — works without any AI API."""
    total = sum(len(r.matches) for r in results)
    with_matches = [r for r in results if r.matches]
    others = len(results) - len(with_matches)

    STATUS_LABELS = {
        "es": {"missing": "desaparecido/a", "found": "encontrado/a",
               "hospitalized": "hospitalizado/a", "pet": "mascota reportada",
               "unknown": "estado desconocido"},
        "en": {"missing": "missing", "found": "found",
               "hospitalized": "hospitalized", "pet": "reported pet",
               "unknown": "unknown status"},
    }

    def _build(lang: str) -> str:
        es = lang == "es"
        lines: List[str] = []

        if total > 0:
            lines.append(
                f"Entiendo lo difícil que es este momento. Encontré {total} "
                f"coincidencia(s) para «{query}»:"
                if es else
                f"I understand how hard this moment is. I found {total} "
                f"match(es) for «{query}»:"
            )
            lines.append("")
            for r in with_matches:
                label = r.platform_label or r.platform
                lines.append(f"📍 {label}")
                for m in r.matches[:5]:
                    name = m.get("name") or "?"
                    status = STATUS_LABELS[lang].get(m.get("status") or "unknown",
                                                     m.get("status") or "?")
                    seen = (m.get("last_seen") or "").strip(" —·")
                    phone = m.get("phone")
                    link = m.get("source_url") or r.platform_url
                    lines.append(f"  • {name} — {status}")
                    if seen:
                        lines.append(f"    {seen}")
                    if phone:
                        lines.append(f"    ☎ {'Teléfono de información' if es else 'Info phone'}: {phone}")
                    lines.append(f"    🔗 {link}")
                lines.append("")
            if others > 0:
                lines.append(
                    f"También busqué en otras {others} plataformas sin coincidencias por ahora."
                    if es else
                    f"I also searched {others} more platforms with no matches yet."
                )
        else:
            lines.append(
                f"Entiendo lo difícil que es este momento. Busqué «{query}» en las "
                f"{len(results)} plataformas y por ahora no hay coincidencias — eso NO "
                "significa lo peor: los registros se actualizan a cada hora. "
                "Intenta de nuevo más tarde o con otra forma del nombre."
                if es else
                f"I understand how hard this moment is. I searched «{query}» across "
                f"all {len(results)} platforms and there are no matches yet — that does "
                "NOT mean the worst: records are updated every hour. "
                "Try again later or with another form of the name."
            )

        lines.append("")
        lines.append(resources_block(lang))
        lines.append(
            "\nVerifica siempre el estado en la fuente original antes de tomar decisiones."
            if es else
            "\nAlways verify the status on the original source before making decisions."
        )
        return "\n".join(lines).strip()

    return _build("es"), _build("en")