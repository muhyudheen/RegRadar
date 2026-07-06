# ─────────────────────────────────────────────────
#  Lawhook Backend Dockerfile
#  Python 3.12 · FastAPI · Celery
#  Chromium removed — active scrapers are HTTP-only
#  (Playwright lib kept for the RBI/SEBI fallback code;
#   browser not installed. If a scraper ever needs JS
#   rendering, re-add: RUN playwright install chromium)
# ─────────────────────────────────────────────────

FROM python:3.12-slim

WORKDIR /app

# System deps:
# - libpq-dev: psycopg2 (Postgres driver)
# - gcc: builds native wheels
# - curl: health checks / debugging
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer cached until requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code
COPY . .

EXPOSE 8000

# Default command — overridden per-service (worker/beat) on both
# docker-compose and Railway. On Railway, the API service command
# uses $PORT instead of 8000 (Railway assigns the port dynamically).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]