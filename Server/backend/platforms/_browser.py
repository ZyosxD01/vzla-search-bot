"""Shared Playwright browser pool.

A single Chromium instance is reused across all platform searches to keep
the memory footprint low. Each platform adapter borrows a context, runs
its queries, and closes the context — the browser stays alive for the
lifetime of the process.

Auto-recovers from browser crashes: if the cached browser dies between
requests, the next get_browser() call launches a fresh one.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# Whether to run Chromium headless. Override with PLAYWRIGHT_HEADFUL=1 for debugging.
HEADLESS = os.environ.get("PLAYWRIGHT_HEADFUL", "0") != "1"

# Path to a Chromium executable. On Render/most Linux installs, Playwright
# installs it under ~/.cache/ms-playwright/.
PLAYWRIGHT_BROWSERS_PATH = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", None)

_browser = None
_browser_lock = asyncio.Lock()


async def get_browser():
    """Lazily launch a Playwright Chromium browser. Auto-recovers from crashes.

    Returns the cached browser if it is still alive. If the cached browser
    has died (e.g., from an OOM kill or a SIGKILL on the host), this
    launches a fresh one transparently.
    """
    global _browser
    # Fast path: cached browser is alive
    if _browser is not None:
        try:
            if _browser.is_connected():
                return _browser
        except Exception:
            pass
        # Dead browser — clean up before relaunching
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None

    # Slow path: serialised launch inside the lock
    async with _browser_lock:
        # Double-check inside the lock — another coroutine may have launched it
        if _browser is not None:
            try:
                if _browser.is_connected():
                    return _browser
            except Exception:
                pass
            try:
                await _browser.close()
            except Exception:
                pass
            _browser = None

        logger.info("Launching fresh Chromium browser...")
        from playwright.async_api import async_playwright
        pw = await async_playwright().start()
        _browser = await pw.chromium.launch(
            headless=HEADLESS,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
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
        except Exception:
            pass


async def shutdown() -> None:
    """Close the shared browser cleanly. Called from FastAPI shutdown."""
    global _browser
    if _browser is not None:
        try:
            await _browser.close()
        except Exception:
            pass
        _browser = None
