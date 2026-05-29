# RegRadar 🛰️
### Regulatory & Compliance Change Monitoring API

> **Never miss a regulatory change again.**
> RegRadar watches official government and regulatory sources 24/7 and delivers structured, AI-summarised change alerts to your app via webhook — in real time.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://docker.com)
[![Status](https://img.shields.io/badge/Status-Phase%201%20MVP-orange)]()

---

## What Is RegRadar?

RegRadar is a developer-first API platform that monitors regulatory and compliance changes across jurisdictions and industries. Subscribe to a **jurisdiction + industry** combination and receive structured webhook payloads whenever a law, regulation, or compliance requirement changes.

```json
{
  "event": "regulation.changed",
  "change_id": "chg_01HWXYZ9K2B3N",
  "jurisdiction": "IN",
  "industry": "fintech",
  "topic": "KYC",
  "severity": "critical",
  "summary": "RBI now requires video-KYC re-verification for all accounts dormant for more than 12 months. Effective 1 July 2026.",
  "effective_date": "2026-07-01",
  "source": {
    "authority": "Reserve Bank of India",
    "url": "https://rbi.org.in/circulars/2026/kyc-update.pdf"
  },
  "diff": {
    "added": [{ "clause": "Section 4.2b", "text": "Video KYC re-verification required..." }],
    "removed": [],
    "modified": []
  }
}
```

---

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Roadmap](#roadmap)
- [Contributing](#contributing)

---

## Features

### Core API
- **Subscription Management** — Subscribe to any jurisdiction + industry combination
- **Real-Time Webhooks** — Signed HMAC-SHA256 webhook delivery with retry logic
- **Change Feed** — Poll-based paginated change history as an alternative to webhooks
- **AI Summaries** — Every change is summarised in plain language via Claude API
- **Severity Scoring** — Automatic `critical / major / minor` classification
- **Structured Diff** — Machine-readable `added / removed / modified` clause diffs
- **Source Verification** — Every change traced to an official government source

### Developer Experience
- Interactive API playground at `/docs`
- Auto-generated OpenAPI / Swagger documentation
- Python SDK *(Phase 2)*
- TypeScript SDK *(Phase 2)*
- Usage dashboard *(Phase 2)*
- Webhook simulator *(Phase 2)*

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI (Python 3.12) |
| **Database** | PostgreSQL 16 |
| **Cache / Message Broker** | Redis |
| **Task Queue** | Celery |
| **Scraping Engine** | Playwright + httpx |
| **AI / NLP** | Claude API (Anthropic) |
| **Frontend Dashboard** | Next.js 15 + Tailwind CSS |
| **Containerisation** | Docker + Docker Compose |
| **Hosting (Production)** | AWS ECS Fargate + RDS Aurora |

---

## Getting Started

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/regradar.git
cd regradar
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and fill in your values (see Environment Variables below)
```

### 3. Start all services

```bash
docker compose up --build
```

This starts:
- **FastAPI** on `http://localhost:8000`
- **PostgreSQL** on `localhost:5432`
- **Redis** on `localhost:6379`
- **Celery Worker** (background jobs)
- **Celery Beat** (scraper scheduler)

### 4. Run database migrations

```bash
docker compose exec api alembic upgrade head
```

### 5. Create your first API key

```bash
curl -X POST http://localhost:8000/v1/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-test-key"}'
```

### 6. Create a subscription

```bash
curl -X POST http://localhost:8000/v1/subscriptions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "jurisdiction": "IN",
    "industry": "fintech",
    "topics": ["KYC", "AML"],
    "webhook_url": "https://your-app.com/webhooks/compliance",
    "severity_min": "major"
  }'
```

---

## API Reference

Interactive docs available at `http://localhost:8000/docs` when running locally.

### Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/v1/auth/keys` | Generate a new API key |
| `POST` | `/v1/subscriptions` | Create a new subscription |
| `GET` | `/v1/subscriptions` | List all subscriptions |
| `GET` | `/v1/subscriptions/:id` | Get a single subscription |
| `DELETE` | `/v1/subscriptions/:id` | Delete a subscription |
| `GET` | `/v1/changes` | Get paginated change feed |
| `GET` | `/v1/changes/:id` | Get a single change |
| `GET` | `/v1/search` | Full-text search across changes |
| `GET` | `/v1/health` | Health check |

### Webhook Payload

All webhooks are signed with `HMAC-SHA256`. Verify the signature using the `X-RegRadar-Signature` header:

```python
import hmac, hashlib

def verify_webhook(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Webhook Retry Policy

If your endpoint fails, RegRadar retries with exponential backoff:

| Attempt | Delay |
|---|---|
| 1st retry | 1 minute |
| 2nd retry | 5 minutes |
| 3rd retry | 30 minutes |
| 4th retry | 2 hours |
| 5th retry | 24 hours |
| After 5th | Marked as `failed` — check dashboard |

---

## Project Structure

```
regradar/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── auth.py          # API key management
│   │   │       ├── subscriptions.py # Subscription CRUD
│   │   │       ├── changes.py       # Change feed endpoints
│   │   │       └── search.py        # Full-text search
│   │   ├── core/
│   │   │   ├── config.py            # Settings & env vars
│   │   │   ├── database.py          # SQLAlchemy setup
│   │   │   └── security.py          # HMAC signing, auth
│   │   ├── models/
│   │   │   ├── api_key.py
│   │   │   ├── subscription.py
│   │   │   ├── change.py
│   │   │   └── webhook_delivery.py
│   │   ├── workers/
│   │   │   ├── scraper.py           # Scraping engine (Playwright + httpx)
│   │   │   ├── processor.py         # AI summarisation (Claude API)
│   │   │   └── webhook.py           # Webhook delivery + retry
│   │   └── main.py                  # FastAPI app entry point
│   ├── alembic/                     # Database migrations
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── app/
│   │   ├── dashboard/               # Usage dashboard
│   │   ├── subscriptions/           # Subscription management
│   │   ├── changes/                 # Change history viewer
│   │   └── settings/                # API keys, billing
│   ├── components/
│   ├── package.json
│   └── next.config.js
│
├── docker-compose.yml
├── docker-compose.prod.yml
├── .env.example
└── README.md
```

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# Database
DATABASE_URL=postgresql://postgres:password@db:5432/regradar

# Redis
REDIS_URL=redis://redis:6379/0

# Anthropic (Claude API)
ANTHROPIC_API_KEY=sk-ant-...

# Security
SECRET_KEY=your-random-secret-key-here
WEBHOOK_SIGNING_SECRET=another-random-secret

# App
ENVIRONMENT=development
LOG_LEVEL=INFO

# Scraper
SCRAPE_INTERVAL_MINUTES=15
```

---

## Roadmap

### Phase 1 — MVP (Current)
- [x] Project scaffold & Docker Compose setup
- [ ] Database schema & migrations
- [ ] `POST /subscriptions` endpoint
- [ ] `GET /subscriptions` endpoint
- [ ] RBI scraper (first source)
- [ ] Content hash-based change detection
- [ ] Claude API integration (summary + severity)
- [ ] Webhook delivery with retry logic
- [ ] Basic API key auth

### Phase 2 — Developer Ready
- [ ] Python SDK (PyPI)
- [ ] TypeScript SDK (npm)
- [ ] Interactive playground
- [ ] Webhook simulator
- [ ] Full-text search (PostgreSQL FTS)
- [ ] Usage dashboard (Next.js)
- [ ] Rate limiting
- [ ] Staging environment (AWS)

### Phase 3 — Production & Growth
- [ ] Production AWS deployment (ECS Fargate + Aurora)
- [ ] Stripe billing integration
- [ ] 50+ regulatory sources across 5 jurisdictions
- [ ] Prometheus + Grafana monitoring
- [ ] Sentry error tracking
- [ ] Public launch

---

## Contributing

This project is currently in active early development. If you're contributing:

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit with clear messages: `git commit -m "feat: add RBI scraper"`
4. Push and open a PR against `main`

Use [Conventional Commits](https://www.conventionalcommits.org/) for commit messages:
- `feat:` new feature
- `fix:` bug fix
- `chore:` tooling, deps
- `docs:` documentation only

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with 🛰️ by the RegRadar team</sub>
</div>
