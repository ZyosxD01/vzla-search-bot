# Venezuela Earthquake Search — backend Dockerfile
# Built specifically for Render free-tier web services.
# Uses the slim Python image + Playwright's official Chromium build.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_HEADFUL=0

WORKDIR /app

# System deps for Chromium on Debian slim.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
    libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 \
    libxrandr2 libgbm1 libasound2 libpango-1.0-0 libcairo2 \
    fonts-liberation libappindicator3-1 \
    && rm -rf /var/lib/apt/lists/*

# Python deps first (better Docker layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium for Playwright (no-deps because we already installed them).
RUN playwright install chromium

# App code — copy each piece explicitly so the layout is deterministic
# regardless of how Render interprets `dockerContext` in render.yaml.
# This guarantees the frontend ends up at /app/frontend/ and the app at
# /app/backend/... which matches what app.py's _find_frontend_dir() expects.
COPY backend/app.py backend/ai_formatter.py backend/resources.py ./backend/
COPY backend/platforms/ ./backend/platforms/
COPY frontend/ ./frontend/

# Render sets $PORT; uvicorn must bind to 0.0.0.0.
ENV PORT=10000
EXPOSE 10000

# Run from /app so `platforms` is importable as a top-level package.
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "10000", "--workers", "1"]