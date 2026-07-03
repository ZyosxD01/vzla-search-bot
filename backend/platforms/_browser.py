"""Shared Playwright browser pool.

A single Chromium instance is reused across all platform searches to keep
the memory footprint low on Render's free tier (512MB).

Each platform adapter borrows a context, runs its queries, and closes the
context — the browser stays alive for the lifetime of the process.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

logger = logging.getLogger(__name__)

# Whether to run Chromium headless. Override with PLAYWRIGHT_HEADFUL=1 for debugging.
HEADLESS = os.environ.get("PLAYWRIGHT_HEADFUL", "0") != "1"

# Path to a Chromium executable. On Render, Playwright installs it via the
# Dockerfile (see backend/Dockerfile). Locally, run:
#   playwright install chromium
PLAYWRIGHT_BROWSERS_PATH = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", None)

_browser_lock = asyncio.Lock()
_browser = None


async def get_browser():
    """Lazily launch a single Playwright Chromium browser."""
    global _browser
    if _browser is not None:
        return _browser
    async with _browser_lock:
        if _browser is not None:
            return _browser
        from playwright.async_api import async_playwright
        logger.info("Launching Playwright Chromium (headless=%s)...", HEADLESS)
        pw = await async_playwright().start()
        args = ["--disable-gpu"]
        if sys.platform.startswith("linux"):
            # Container-only flags: --single-process crashes Chromium on Windows.
            args += [
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",  # critical in low-memory containers
                "--no-zygote",
                "--single-process",
            ]
        _browser = await pw.chromium.launch(headless=HEADLESS, args=args)
        return _browser


@asynccontextmanager
async def new_page():
    """Borrow a fresh context+page from the shared browser.

    The context is closed on exit; the browser itself stays alive.
    """
    browser = await get_browser()
    context = await browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 "
            "(vzla-search-bot humanitarian)"
        ),
        locale="es-VE",
        timezone_id="America/Caracas",
        viewport={"width": 1280, "height": 800},
        ignore_https_errors=True,
    )
    page = await context.new_page()
    try:
        yield page
    finally:
        try:
            await context.close()
        except Exception:  # noqa: BLE001
            pass


async def shutdown() -> None:
    """Close the shared browser cleanly. Called from FastAPI shutdown."""
    global _browser
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:  # noqa: BLE001
            pass
        _browser = None