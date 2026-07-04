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

ENABLED_PLATFORMS = [
    "desaparecidosterremotovenezuela",
    "venezuelatebusca",
    "statusvzla",
    "terremotoenvenezuela",
    "busquedavzla",
    "reportevenezuela",
    "pacientesterremoto",
    "pacientesinfo",
    "venezuelaayuda",
    "hospitalesenvenezuela",
    "redayudavenezuela",
    "venezuelareporta",
    "sismo911",
    "desaparecidosvenezuela",
    "crisisve",
    "huellascan",
    "icrc",
]

PLATFORM_TIMEOUT_SECONDS = 25

# Concurrency cap for Playwright browser contexts.
# Render free tier has 512MB RAM; Chromium needs ~300-500MB. Spawning
# all Playwright-backed adapters in parallel OOM-kills the browser process
# (statusvzla and icrc don't count — they don't use a browser at all).
# 3 concurrent contexts keeps peak memory well under the cap.
PLAYWRIGHT_CONCURRENCY = 3
_search_semaphore: Optional[asyncio.Semaphore] = None


def _get_search_semaphore() -> asyncio.Semaphore:
    global _search_semaphore
    if _search_semaphore is None:
        _search_semaphore = asyncio.Semaphore(PLAYWRIGHT_CONCURRENCY)
    return _search_semaphore

# --- Anti-abuse layers (no user registration, by design) ------------------
REQUIRED_APP_HEADER = "vzla-search"
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 3600
DAILY_LIMIT_MAX = 15
DAILY_WINDOW = 86400
COOLDOWN_SECONDS = 5

_rate_log: Dict[str, Deque[float]] = defaultdict(deque)
_daily_log: Dict[str, Deque[float]] = defaultdict(deque)
_last_search: Dict[str, float] = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _rate_keys(request: Request) -> List[str]:
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
    if request.headers.get("x-requested-with", "") != REQUIRED_APP_HEADER:
        raise HTTPException(403, "Missing application header")

    now = time.time()
    keys = _rate_keys(request)

    for key in keys:
        last = _last_search.get(key, 0.0)
        wait = COOLDOWN_SECONDS - (now - last)
        if wait > 0:
            raise _limited(0, retry_seconds=int(wait) + 1)

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

# ---------------------------------------------------------------------------
# Frontend path resolution
# ---------------------------------------------------------------------------

def _find_frontend_dir() -> Optional[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "frontend"),
        os.path.join(here, "..", "frontend"),
        os.path.join(here, "..", "..", "frontend"),
        "/app/frontend",
        "/frontend",
        os.path.join(os.getcwd(), "frontend"),
    ]
    logger.info("Resolving frontend dir. __file__=%s, cwd=%s", __file__, os.getcwd())
    for p in candidates:
        try:
            exists = os.path.isdir(p)
            has_index = os.path.isfile(os.path.join(p, "index.html")) if exists else False
            logger.info("  candidate %-50s exists=%s has_index=%s", p, exists, has_index)
            if exists and has_index:
                logger.info("Frontend dir resolved to: %s", os.path.abspath(p))
                return p
        except OSError:
            continue
    logger.error(
        "Frontend dir not found. Looked in: %s. "
        "If the SPA fails to load, check that the Dockerfile copies frontend/ "
        "into the image and that __file__ resolves to the expected location.",
        candidates,
    )
    return None


FRONTEND_DIR = _find_frontend_dir()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=200)
    language: Optional[str] = Field("auto")


class PlatformResult(BaseModel):
    platform: str
    platform_label: str
    platform_url: str
    matches: List[dict] = []
    error: Optional[str] = None
    timing_ms: int = 0
    filtered_count: int = 0
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

def _filter_weak_matches(result, query):
    """Drop records where fewer than 50% of query words appear in the name field.

    Prevents the bot from returning people whose name only partially matches
    the query while the rest of the match is from a hospital or facility
    name in the last_seen field.
    """
    if not result.matches or not query:
        return result
    query_words = [w for w in query.lower().split() if len(w) >= 3]
    if not query_words:
        return result
    kept = []
    dropped = 0
    for m in result.matches:
        name_blob = str(m.get("name") or "").lower()
        matches_in_name = sum(1 for w in query_words if w in name_blob)
        if (matches_in_name / len(query_words)) >= 0.5:
            kept.append(m)
        else:
            dropped += 1
    return PlatformResult(
        platform=result.platform,
        platform_label=result.platform_label,
        platform_url=result.platform_url,
        matches=kept,
        error=result.error,
        timing_ms=result.timing_ms,
        filtered_count=dropped,
    )


def detect_language(text: str) -> str:
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
    """Run a single platform search with timeout + error isolation + semaphore.

    The semaphore caps simultaneous Chromium contexts so the browser
    process isn't OOM-killed on Render's 512MB free tier.
    """
    started = asyncio.get_event_loop().time()
    try:
        async with _get_search_semaphore():
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
            platform=name, platform_label=name, platform_url="",
            error=f"Timeout after {PLATFORM_TIMEOUT_SECONDS}s", timing_ms=elapsed_ms,
        )
    except Exception as exc:
        elapsed_ms = int((asyncio.get_event_loop().time() - started) * 1000)
        logger.exception("Platform %s failed", name)
        return PlatformResult(
            platform=name, platform_label=name, platform_url="",
            error=f"{type(exc).__name__}: {exc}", timing_ms=elapsed_ms,
        )

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up — enabled platforms: %s", ENABLED_PLATFORMS)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Venezuela Earthquake Missing Persons Search",
    description="Federated search across Venezuelan disaster response platforms.",
    version="0.2.0",
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
    query = req.query.strip()
    if len(query) < 2:
        raise HTTPException(400, "Query must be at least 2 characters")

    remaining = check_rate_limit(request)

    language = req.language if req.language in ("es", "en") else detect_language(query)

    logger.info("Search: %r (lang=%s)", query, language)

    tasks = [search_platform_safe(name, query) for name in ENABLED_PLATFORMS]
    results = await asyncio.gather(*tasks)
    results = [_filter_weak_matches(r, query) for r in results]

    total = sum(len(r.matches) for r in results)

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
            "Esta es una búsqueda agregada. Verifica siempre el estado en la fuente original."
            if language == "es" else
            "This is an aggregated search. Always verify the status on the original source."
        ),
    )


# ---------------------------------------------------------------------------
# Static frontend (served from /)
# ---------------------------------------------------------------------------

if FRONTEND_DIR and os.path.isdir(FRONTEND_DIR):
    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))

    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
else:
    logger.warning(
        "Frontend directory not resolved; SPA will return 404 on GET /. "
        "API endpoints still work."
    )
