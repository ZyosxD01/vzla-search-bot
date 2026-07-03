"""
Venezuela Earthquake Missing Persons Search — Backend API

A federated search engine that queries multiple Venezuelan disaster response
platforms in parallel, consolidates results, and returns bilingual
formatted responses via the MiniMax AI API.

Architecture:
- FastAPI for the HTTP layer
- Playwright for headless browser automation against JS-rendered sites
- MiniMax API for bilingual response formatting
- No persistent database — all queries are live federated searches

Ethics & legal guardrails (per PLAN v2 editorial policy):
- No personal data is stored permanently
- All results link back to original source platforms
- Rate limiting protects upstream services
- If a source asks us to stop, we remove its adapter
"""

import asyncio
import logging
import os
import re
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import Deque, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from ai_formatter import format_results
from platforms import get_searcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vzla-search")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Platforms enabled in the MVP. Add/remove here to control the federation.
# Each entry must have a matching adapter in `platforms/<name>.py`.
ENABLED_PLATFORMS = [
    # Personas desaparecidas / encontradas
    "desaparecidosterremotovenezuela",
    "venezuelatebusca",
    "statusvzla",
    "terremotoenvenezuela",
    "busquedavzla",
    "rescateve",
    "venapp",
    "reportevenezuela",
    # Hospitalizados / pacientes
    "pacientesterremoto",
    "pacientesinfo",
    # Portales integrales
    "venezuelaayuda",
    # Mascotas (búsqueda por descripción: especie, raza, color, zona)
    "huellascan",
    # Estándar internacional
    "icrc",
]

# Per-request timeout for a single platform search.
PLATFORM_TIMEOUT_SECONDS = 25

# --- Anti-abuse layers (no user registration, by design) ------------------
# 1. Required app header — blocks naive curl/script spam.
# 2. Cooldown between searches — blocks bursts.
# 3. 5 searches/hour per key.
# 4. 15 searches/day per key (catches hourly-limit cyclers).
# Every layer is applied per-IP AND per-device (client id header), so
# rotating one of the two is not enough to evade the limits.
REQUIRED_APP_HEADER = "vzla-search"
RATE_LIMIT_MAX = 5           # searches per hour
RATE_LIMIT_WINDOW = 3600
DAILY_LIMIT_MAX = 15         # searches per day
DAILY_WINDOW = 86400
COOLDOWN_SECONDS = 15        # min seconds between searches

_rate_log: Dict[str, Deque[float]] = defaultdict(deque)    # hourly, per key
_daily_log: Dict[str, Deque[float]] = defaultdict(deque)   # daily, per key
_last_search: Dict[str, float] = {}                        # cooldown, per key


def _client_ip(request: Request) -> str:
    """Client IP, honouring the proxy header Render puts in front of us."""
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_keys(request: Request) -> List[str]:
    """Keys the limits apply to: always the IP, plus the device id if sent."""
    keys = [f"ip:{_client_ip(request)}"]
    cid = request.headers.get("x-vzla-client", "").strip()[:64]
    if cid:
        keys.append(f"cid:{cid}")
    return keys


def _limited(retry_minutes: int, retry_seconds: int = 0) -> HTTPException:
    if retry_seconds:
        msg_es = f"Muy rápido — espera {retry_seconds}s entre búsquedas."
        msg_en = f"Too fast — wait {retry_seconds}s between searches."
    else:
        msg_es = (
            f"Alcanzaste el límite de {RATE_LIMIT_MAX} búsquedas por hora. "
            f"Podrás buscar de nuevo en ~{retry_minutes} min."
        )
        msg_en = (
            f"You reached the limit of {RATE_LIMIT_MAX} searches per hour. "
            f"You can search again in ~{retry_minutes} min."
        )
    return HTTPException(
        status_code=429,
        detail={
            "error": "rate_limited",
            "retry_minutes": retry_minutes,
            "retry_seconds": retry_seconds,
            "message_es": msg_es,
            "message_en": msg_en,
        },
    )


def check_rate_limit(request: Request) -> int:
    """Run every anti-abuse layer. Returns remaining hourly searches.

    Raises HTTPException 403 (missing app header) or 429 (limited).
    """
    if request.headers.get("x-requested-with", "") != REQUIRED_APP_HEADER:
        raise HTTPException(403, "Missing application header")

    now = time.time()
    keys = _rate_keys(request)

    # Cooldown between searches.
    for key in keys:
        last = _last_search.get(key, 0.0)
        wait = COOLDOWN_SECONDS - (now - last)
        if wait > 0:
            raise _limited(0, retry_seconds=int(wait) + 1)

    # Hourly + daily windows — check ALL keys before consuming ANY.
    for key in keys:
        hourly = _rate_log[key]
        while hourly and now - hourly[0] > RATE_LIMIT_WINDOW:
            hourly.popleft()
        if len(hourly) >= RATE_LIMIT_MAX:
            raise _limited(max(1, int((RATE_LIMIT_WINDOW - (now - hourly[0])) / 60) + 1))

        daily = _daily_log[key]
        while daily and now - daily[0] > DAILY_WINDOW:
            daily.popleft()
        if len(daily) >= DAILY_LIMIT_MAX:
            raise _limited(max(1, int((DAILY_WINDOW - (now - daily[0])) / 60) + 1))

    remaining = RATE_LIMIT_MAX
    for key in keys:
        _rate_log[key].append(now)
        _daily_log[key].append(now)
        _last_search[key] = now
        remaining = min(remaining, RATE_LIMIT_MAX - len(_rate_log[key]))
    return remaining

# Path where the static frontend lives (relative to backend/).
# Inside the Docker container the whole backend/ tree is copied to /app/,
# so the frontend sits at /app/frontend/ — same directory as this file.
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200, description="Name or partial name to search")
    language: Optional[str] = Field("auto", description="es | en | auto")


class PlatformResult(BaseModel):
    platform: str
    platform_label: str
    platform_url: str
    matches: List[dict] = []
    error: Optional[str] = None
    timing_ms: int = 0


class SearchResponse(BaseModel):
    query: str
    language: str
    total_matches: int
    platforms_queried: int
    results: List[PlatformResult]
    formatted_es: str
    formatted_en: str
    disclaimer: str
    searches_remaining: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def detect_language(text: str) -> str:
    """Cheap heuristic language detection — falls back to English."""
    if not text:
        return "en"
    lowered = text.lower()
    spanish_markers = {
        "busco", "buscar", "está", "estaba", "donde", "dónde", "hermana", "hermano",
        "madre", "padre", "hijo", "hija", "esposa", "esposo", "tío", "tía", "abuelo",
        "abuela", "primo", "prima", "amigo", "amiga", "desaparecio", "desapareció",
        "el", "la", "los", "las", "de", "en", "y", "con", "por", "para",
    }
    if any(c in lowered for c in "ñáéíóúü¿¡"):
        return "es"
    words = set(re.findall(r"\w+", lowered))
    if words & spanish_markers:
        return "es"
    return "en"


async def search_platform_safe(name: str, query: str) -> PlatformResult:
    """Run a single platform search with timeout + error isolation."""
    started = asyncio.get_event_loop().time()
    try:
        searcher = get_searcher(name)
        matches = await asyncio.wait_for(
            searcher.search(query), timeout=PLATFORM_TIMEOUT_SECONDS
        )
        elapsed_ms = int((asyncio.get_event_loop().time() - started) * 1000)
        return PlatformResult(
            platform=name,
            platform_label=searcher.label,
            platform_url=searcher.url,
            matches=matches or [],
            timing_ms=elapsed_ms,
        )
    except asyncio.TimeoutError:
        elapsed_ms = int((asyncio.get_event_loop().time() - started) * 1000)
        logger.warning("Platform %s timed out after %ds", name, PLATFORM_TIMEOUT_SECONDS)
        return PlatformResult(
            platform=name,
            platform_label=name,
            platform_url="",
            error=f"Timeout after {PLATFORM_TIMEOUT_SECONDS}s",
            timing_ms=elapsed_ms,
        )
    except Exception as exc:  # noqa: BLE001 — boundary
        elapsed_ms = int((asyncio.get_event_loop().time() - started) * 1000)
        logger.exception("Platform %s failed", name)
        return PlatformResult(
            platform=name,
            platform_label=name,
            platform_url="",
            error=f"{type(exc).__name__}: {exc}",
            timing_ms=elapsed_ms,
        )


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up — enabled platforms: %s", ENABLED_PLATFORMS)
    # Warm up the first browser lazily on first request; nothing to do here.
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Venezuela Earthquake Missing Persons Search",
    description=(
        "Federated search across multiple Venezuelan disaster response platforms. "
        "No personal data is stored. All results link to original sources."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "platforms": ENABLED_PLATFORMS}


@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request) -> SearchResponse:
    """Run a federated search across all enabled platforms in parallel."""
    query = req.query.strip()
    if len(query) < 2:
        raise HTTPException(400, "Query must be at least 2 characters")

    remaining = check_rate_limit(request)

    language = req.language if req.language in ("es", "en") else detect_language(query)

    logger.info("Search: %r (lang=%s)", query, language)

    # Fan out to all platforms in parallel — they are isolated from each other.
    tasks = [search_platform_safe(name, query) for name in ENABLED_PLATFORMS]
    results = await asyncio.gather(*tasks)

    total = sum(len(r.matches) for r in results)

    # Format with the MiniMax AI API (falls back to plain text if AI fails).
    formatted_es, formatted_en = await format_results(query, results, language)

    return SearchResponse(
        query=query,
        language=language,
        total_matches=total,
        platforms_queried=len(results),
        results=results,
        formatted_es=formatted_es,
        formatted_en=formatted_en,
        searches_remaining=remaining,
        disclaimer=(
            "Esta es una búsqueda agregada. Verifica siempre el estado en la fuente original "
            "antes de tomar decisiones. La información puede tardar minutos en sincronizarse."
            if language == "es" else
            "This is an aggregated search. Always verify the status on the original source "
            "before making decisions. Information may take minutes to sync."
        ),
    )


# ---------------------------------------------------------------------------
# Static frontend (served from /)
# ---------------------------------------------------------------------------

if os.path.isdir(FRONTEND_DIR):
    # Serve the SPA root explicitly so / loads index.html, not a 404.
    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    logger.warning("Frontend directory not found at %s", FRONTEND_DIR)