# RegRadar 🛰️
### Regulatory & Compliance Change Monitoring API

> **Never miss a regulatory change again.**
> RegRadar monitors official government and regulatory sources 24/7 and delivers structured, AI-summarised change alerts to your app via signed webhooks — in real time.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12-blue?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green?logo=fastapi)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-ready-blue?logo=docker)](https://docker.com)
[![Status](https://img.shields.io/badge/Status-Phase%201%20Complete-brightgreen)]()

---

## What Is RegRadar?

RegRadar is a **developer-first API platform** for regulatory and compliance monitoring. Subscribe to a jurisdiction + industry combination, and receive structured webhook payloads whenever a law, regulation, or compliance requirement changes — with AI-generated plain-language summaries and severity scores.

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

## Why RegRadar?

| | Thomson Reuters / Lexis | Manual Monitoring | RegRadar |
|---|---|---|---|
| **Price** | $50K+/yr | Staff cost $80K+/yr | $49–199/month |
| **Developer API** | None | None | First-class REST API |
| **Structured JSON** | No | No | Yes — typed schemas |
| **Webhook delivery** | No | No | Real-time, signed |
| **Setup time** | Months | Weeks | Under 30 minutes |
| **SMB friendly** | No | No | Yes |

---

## Features

### Core API
- **Subscription Management** — Subscribe to any jurisdiction + industry combination
- **Real-Time Webhooks** — HMAC-SHA256 signed delivery with automatic retry logic
- **Change Feed** — Poll-based paginated change history as an alternative to webhooks
- **AI Summaries** — Every change summarised in plain language via Claude API
- **Severity Scoring** — Automatic `critical / major / minor` classification
- **Structured Diff** — Machine-readable `added / removed / modified` clause diffs
- **Source Verification** — Every change traced to an official government source
- **Per-Subscription Secrets** — Each subscription gets its own signing secret

### Security
- SSRF protection with IPv6 bypass fix on all webhook URLs
- DNS rebinding protection at delivery time (TOCTOU fix)
- TLS SNI fix via custom httpcore transport
- Redis fencing tokens on scraper locks
- CSPRNG API key generation with SHA-256 hashing
- Per-subscription HMAC-SHA256 webhook signing
- Prompt injection protection on AI processing
- Redirect attack detection and blocking

### Infrastructure
- Docker Compose local development (5 services)
- Celery + Redis task queue for background scraping and delivery
- Celery Beat scheduler (scrapes every 15 minutes)
- PostgreSQL with Alembic migrations
- httpx + Playwright fallback scraper engine

---

## Tech Stack

| Layer | Technology |
|---|---|
| **API Framework** | FastAPI (Python 3.12) |
| **Database** | PostgreSQL 16 |
| **Cache / Broker** | Redis 7 |
| **Task Queue** | Celery 5 |
| **Scraping** | httpx + Playwright (fallback) |
| **HTML Parsing** | BeautifulSoup4 + lxml |
| **AI / NLP** | Claude API (Anthropic) |
| **Containerisation** | Docker + Docker Compose |

---

## Getting Started

### Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/)
- An [Anthropic API key](https://console.anthropic.com)

### 1. Clone the repo

```bash
git clone https://github.com/muhyudheen/RegRadar.git
cd RegRadar
```

### 2. Set up environment

```bash
cp .env.example .env
```

Open `.env` and fill in:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
SECRET_KEY=generate-with-python-secrets-token-hex-32
WEBHOOK_SIGNING_SECRET=another-random-secret
```

Generate secrets:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start all services

```bash
docker compose build
docker compose up -d
```

### 4. Run migrations

```bash
docker compose exec api alembic upgrade head
```

### 5. Generate your first API key

```bash
curl -X POST http://127.0.0.1:8000/v1/auth/keys \
  -H "Content-Type: application/json" \
  -d '{"name": "my-first-key"}'
```

Save the `key` from the response — it's shown once only.

### 6. Create a subscription

```bash
curl -X POST http://127.0.0.1:8000/v1/subscriptions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "India Fintech Monitor",
    "jurisdiction": "IN",
    "industry": "fintech",
    "topics": ["KYC", "AML"],
    "webhook_url": "https://your-app.com/webhooks/compliance",
    "severity_min": "major"
  }'
```

Save the `signing_secret` from the response — use it to verify incoming webhooks.

---

## API Reference

Interactive docs at `http://127.0.0.1:8000/docs` when running locally.

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/v1/auth/keys` | None | Generate a new API key |
| `GET` | `/v1/auth/keys` | ✅ | List all API keys |
| `DELETE` | `/v1/auth/keys/{id}` | ✅ | Revoke a key |
| `POST` | `/v1/subscriptions` | ✅ | Create a subscription |
| `GET` | `/v1/subscriptions` | ✅ | List subscriptions |
| `GET` | `/v1/subscriptions/{id}` | ✅ | Get one subscription |
| `PATCH` | `/v1/subscriptions/{id}` | ✅ | Update subscription |
| `DELETE` | `/v1/subscriptions/{id}` | ✅ | Delete subscription |
| `GET` | `/health` | None | Health check |

---

## Webhook Verification

Every webhook is signed with `HMAC-SHA256`. Verify using your subscription's `signing_secret`:

```python
import hmac, hashlib

def verify_webhook(
    payload_body: bytes,
    signature_header: str,
    timestamp_header: str,
    secret: str,
) -> bool:
    body_str = payload_body.decode("utf-8")
    signed_string = f"{timestamp_header}.{body_str}"
    expected = "sha256=" + hmac.new(
        secret.encode(), signed_string.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature_header, expected)
```

```javascript
// Express.js
const crypto = require('crypto');

app.post('/webhooks/compliance', express.raw({ type: 'application/json' }), (req, res) => {
  const sig = req.headers['x-regradar-signature'];
  const ts  = req.headers['x-regradar-timestamp'];
  const signed = `${ts}.${req.body.toString()}`;
  const expected = 'sha256=' + crypto
    .createHmac('sha256', process.env.REGRADAR_SECRET)
    .update(signed).digest('hex');

  if (!crypto.timingSafeEqual(Buffer.from(sig), Buffer.from(expected))) {
    return res.status(401).send('Invalid signature');
  }
  const payload = JSON.parse(req.body);
  // handle payload...
  res.json({ received: true });
});
```

### Webhook Retry Schedule

| Attempt | Delay |
|---|---|
| 1st retry | 1 minute |
| 2nd retry | 5 minutes |
| 3rd retry | 30 minutes |
| 4th retry | 2 hours |
| 5th retry | 24 hours |
| After 5th | Marked `failed` |

---

## Project Structure

```
RegRadar/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── auth.py              # Auth endpoints
│   │   │   ├── subscriptions.py     # Subscription CRUD
│   │   │   └── router.py            # Route registration
│   │   ├── core/
│   │   │   ├── ai_processor.py      # Claude API integration
│   │   │   ├── api_key_utils.py     # CSPRNG key generation
│   │   │   ├── database.py          # SQLAlchemy setup
│   │   │   ├── webhook_signing.py   # HMAC signing
│   │   │   └── webhook_validator.py # SSRF protection
│   │   ├── dependencies/
│   │   │   └── auth.py              # FastAPI auth dependency
│   │   ├── models/
│   │   │   ├── api_key.py
│   │   │   ├── change.py
│   │   │   ├── subscription.py
│   │   │   └── webhook_delivery.py
│   │   ├── scrapers/
│   │   │   ├── base.py              # Abstract scraper + httpx/Playwright
│   │   │   ├── rbi.py               # Reserve Bank of India scraper
│   │   │   └── registry.py          # Active scraper list
│   │   ├── workers/
│   │   │   ├── ai_tasks.py          # AI processing Celery task
│   │   │   ├── celery_app.py        # Celery configuration
│   │   │   ├── scraper_tasks.py     # Scraper Celery tasks
│   │   │   ├── webhook.py           # Secure HTTP delivery
│   │   │   └── webhook_tasks.py     # Webhook delivery tasks
│   │   └── main.py
│   ├── alembic/versions/            # 5 migrations
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Daily Development Commands

```bash
# Start everything
docker compose up -d

# View logs
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f beat

# Run migrations
docker compose exec api alembic upgrade head

# Trigger scraper manually
docker compose exec worker celery -A app.workers.celery_app \
  call scraper.run_all

# Open database shell
docker compose exec db psql -U regradar -d regradar

# Stop everything (data preserved)
docker compose down
```

---

## Roadmap

### Phase 1 — MVP ✅ Complete
- [x] Docker Compose stack (5 services)
- [x] PostgreSQL schema + 5 migrations
- [x] CSPRNG API key generation
- [x] SSRF webhook validator with IPv6 fix
- [x] HMAC-SHA256 webhook signing (per-subscription)
- [x] Scraper engine (httpx + Playwright fallback)
- [x] RBI regulatory source
- [x] Claude AI integration (summary + severity + diff)
- [x] Webhook delivery with DNS rebinding + TLS SNI fix
- [x] Retry logic with exponential backoff
- [x] `POST /v1/auth/keys` + `POST /v1/subscriptions`

### Phase 2 — Developer Ready
- [ ] Python SDK (PyPI)
- [ ] TypeScript SDK (npm)
- [ ] Interactive playground + webhook simulator
- [ ] Full-text search (PostgreSQL FTS)
- [ ] Usage dashboard (Angular)
- [ ] Rate limiting
- [ ] 10+ regulatory sources

### Phase 3 — Production
- [ ] AWS ECS Fargate + Aurora deployment
- [ ] Stripe billing integration
- [ ] 50+ sources across 5 jurisdictions
- [ ] Prometheus + Grafana monitoring
- [ ] Public launch

---

## Contributing

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit: `git commit -m "feat: your feature"`
4. Push and open a PR against `main`

Commit format: `feat:` `fix:` `chore:` `docs:`

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">
  <sub>Built with 🛰️ by the RegRadar team · Developer-first compliance monitoring</sub>
</div>
