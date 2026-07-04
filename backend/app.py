"""
Venezuela Earthquake Missing Persons Search — Backend API

V2: Deep-link aggregator. Instead of scraping 13 platforms (expensive,
fragile, slow), this version builds pre-filled search URLs that take the
user straight to each platform's own search box with the query already
typed in. No databases, no scraping, no Playwright — just URL templates.

Ethics & legal guardrails (per PLAN v2 editorial policy):
- No personal data is stored
- All results are links to original source platforms
- Sends real traffic to community-built platforms (helps them monetize)
- Rate limiting prevents abuse

Architecture:
- FastAPI for the HTTP layer
- No scraping (removed Playwright — was OOM-killing the 512MB free tier)
- Deep-link generator for 18 Venezuelan disaster response platforms
- No persistent database
"""

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

from platforms.links import PLATFORMS, render_response, generate_search_links, group_by_category

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vzla-search")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ENABLED_PLATFORMS = [p["slug"] for p in PLATFORMS]

# --- Anti-abuse layers (no user registration, by design) ------------------
REQUIRED_APP_HEADER = "vzla-search"
RATE_LIMIT_MAX = 5
RATE_LIMIT_WINDOW = 3600
DAILY_LIMIT_MAX = 15
DAILY_WINDOW = 86400
COOLDOWN_SECONDS = 15

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
        msg_es = f"Muy rápido — esperá {retry_seconds}s entre búsquedas."
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


class SearchResult(BaseModel):
    """Each result is a deep-link to a platform's search page."""
    platform: str
    platform_label: str
    platform_url: str
    search_url: str
    category: str
    description: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    language: str
    platforms_queried: int
    results: List[SearchResult]
    formatted_es: str
    formatted_en: str
    disclaimer: str
    searches_remaining: int = 0

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info("Starting up — %d platforms enabled (deep-link mode)", len(ENABLED_PLATFORMS))
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Venezuela Earthquake Missing Persons Search",
    description="Federated deep-link aggregator for Venezuelan disaster response platforms.",
    version="2.0.0",
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
    return {"status": "ok", "mode": "deep-link", "platforms": ENABLED_PLATFORMS}


@app.post("/api/search", response_model=SearchResponse)
async def search(req: SearchRequest, request: Request) -> SearchResponse:
    """Return deep links to all platforms with the query pre-filled."""
    query = req.query.strip()
    if len(query) < 2:
        raise HTTPException(400, "Query must be at least 2 characters")

    remaining = check_rate_limit(request)

    language = req.language if req.language in ("es", "en") else detect_language(query)

    logger.info("Search: %r (lang=%s)", query, language)

    # Generate deep links for every enabled platform.
    links = generate_search_links(query)

    # Group by category for nicer presentation.
    _ = group_by_category(links)  # sanity check; render_response regroups

    # Render bilingual responses.
    formatted_es = render_response(query, lang="es")
    formatted_en = render_response(query, lang="en")

    results = [
        SearchResult(
            platform=link["platform"],
            platform_label=link["platform_label"],
            platform_url=link["platform_url"],
            search_url=link["search_url"],
            category=link["category"],
            description=link.get("description"),
        )
        for link in links
    ]

    return SearchResponse(
        query=query,
        language=language,
        platforms_queried=len(results),
        results=results,
        formatted_es=formatted_es,
        formatted_en=formatted_en,
        searches_remaining=remaining,
        disclaimer=(
            "Esta es una guía de búsqueda. Cada link abre la plataforma oficial con tu consulta pre-cargada. Verifica siempre el estado en la fuente original."
            if language == "es" else
            "This is a search guide. Each link opens the official platform with your query pre-filled. Always verify the status on the original source."
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