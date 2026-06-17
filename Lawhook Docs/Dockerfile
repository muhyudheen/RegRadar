# ─────────────────────────────────────────────────
#  RegRadar Backend Dockerfile
#  Python 3.12 · FastAPI · Celery
# ─────────────────────────────────────────────────

FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Install system dependencies
# - libpq-dev: needed for psycopg2 (Postgres driver)
# - curl: useful for health checks and debugging
# - chromium + deps: needed by Playwright for scraping JS-rendered gov sites
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first
# (Docker caches this layer — only rebuilds if requirements.txt changes)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (for scraping JS-rendered pages)
RUN playwright install chromium --with-deps

# Copy the rest of the application code
COPY . .

# Expose port for FastAPI
EXPOSE 8000

# Default command (overridden per-service in docker-compose.yml)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
