# Lawhook — Project Structure

Lawhook (originally "RegRadar") is a developer-first regulatory-change monitoring API. It scrapes official regulator sources on a schedule, AI-diffs detected changes, and fires signed webhooks to subscribers. The repo holds four pieces: a FastAPI + Celery **backend**, a React/Vite marketing-site-plus-dashboard **frontend**, and **Python** and **TypeScript** client SDKs.

## File Tree

```
lawhook/
├── README.md
├── SDK_REVIEW.md
├── LICENSE
├── docker-compose.yml
├── .env / .env.example / .gitignore
│
├── Lawhook Docs/                      # project briefs & design specs (PDFs, docker guide)
│
├── backend/                          # FastAPI API + Celery workers + scrapers
│   ├── Dockerfile
│   ├── alembic.ini
│   ├── requirements.txt
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │       ├── 0001_initial.py
│   │       ├── 0002_add_signing_secret.py
│   │       ├── 0003_fix_key_hash_length.py
│   │       ├── 0004_unique_constraints.py
│   │       ├── 0005_change_dedup_constraint.py
│   │       ├── 0006_api_key_tier.py
│   │       └── 0007_cascade_delete_deliveries.py
│   └── app/
│       ├── main.py
│       ├── api/v1/
│       │   ├── router.py
│       │   ├── auth.py
│       │   ├── subscriptions.py
│       │   └── changes.py
│       ├── core/
│       │   ├── database.py
│       │   ├── api_key_utils.py
│       │   ├── ai_processor.py
│       │   ├── rate_limiter.py
│       │   ├── webhook_signing.py
│       │   └── webhook_validator.py
│       ├── dependencies/
│       │   └── auth.py
│       ├── middleware/
│       │   └── rate_limit.py
│       ├── models/
│       │   ├── base.py
│       │   ├── api_key.py
│       │   ├── subscription.py
│       │   ├── change.py
│       │   └── webhook_delivery.py
│       ├── scrapers/
│       │   ├── base.py
│       │   ├── registry.py
│       │   ├── rbi.py
│       │   ├── sebi.py
│       │   ├── sec.py
│       │   ├── fca.py
│       │   ├── mas.py
│       │   └── asic.py
│       └── workers/
│           ├── celery_app.py
│           ├── scraper_tasks.py
│           ├── ai_tasks.py
│           ├── webhook_tasks.py
│           └── webhook.py
│
├── frontend_antigravity/            # React 19 + Vite + CSS Modules
│   ├── index.html / package.json / vite.config.ts / tsconfig*.json / eslint.config.js
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── pages/Home/Home.tsx
│       ├── styles/
│       │   ├── variables.css
│       │   └── index.css
│       ├── lib/
│       │   ├── apiClient.ts
│       │   └── ApiKeyContext.tsx
│       └── components/
│           ├── Navbar/            (Navbar.tsx + .module.css)
│           ├── Hero/
│           ├── FeatureHighlights/
│           ├── SocialProof/
│           ├── Pricing/
│           ├── CTABanner/
│           ├── Footer/
│           └── Dashboard/
│               ├── Dashboard.tsx + .module.css
│               ├── AuthGate.tsx + .module.css
│               ├── ErrorBoundary.tsx + .module.css
│               ├── Overview/
│               ├── Subscriptions/
│               ├── ChangeFeed/
│               └── ApiKeys/
│
├── lawhook-python/                  # Python client SDK
│   ├── pyproject.toml
│   ├── lawhook/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── models.py
│   │   └── exceptions.py
│   └── tests/test_client.py
│
└── lawhook-typescript/              # TypeScript client SDK
    ├── package.json / tsconfig.json
    ├── src/
    │   ├── index.ts
    │   ├── client.ts
    │   ├── models.ts
    │   └── exceptions.ts
    └── tests/client.test.ts
```

---

## File Descriptions

### Root

| File | Description |
|------|-------------|
| `README.md` | Project overview / landing doc (uses the original "RegRadar" name) describing the 24/7 monitoring + signed-webhook product. |
| `SDK_REVIEW.md` | A written parity review comparing the Python and TypeScript SDKs for purpose, tone, public API shape, and functionality. |
| `Lawhook Docs/` | Project brief and UI design-spec PDFs plus a Docker guide — reference material, not code. |

### Backend — Migrations (`backend/alembic/`)

| File | Description |
|------|-------------|
| `env.py` | Alembic runtime config that wires migrations to the app's SQLAlchemy metadata and database URL. |
| `versions/0001_initial.py` | Initial schema: api_keys, subscriptions, changes, webhook_deliveries tables. |
| `versions/0002_add_signing_secret.py` | Adds the per-subscription `signing_secret` column (shown once at creation). |
| `versions/0003_fix_key_hash_length.py` | Widens the API-key hash column to fit the full SHA-256 hex digest. |
| `versions/0004_unique_constraints.py` | Adds uniqueness constraints (e.g. on key hash / subscription identity). |
| `versions/0005_change_dedup_constraint.py` | Adds a constraint to de-duplicate detected changes. |
| `versions/0006_api_key_tier.py` | Adds the `tier` column to api_keys (free/starter/pro/enterprise) driving rate + sub limits. |
| `versions/0007_cascade_delete_deliveries.py` | Makes webhook_deliveries cascade-delete with their parent change/subscription. |

### Backend — App entry & API (`backend/app/`)

| File | Description |
|------|-------------|
| `main.py` | FastAPI app factory: CORS, rate-limit middleware, mounts the `/v1` router, exposes a service-info root endpoint. |
| `api/v1/router.py` | Aggregates the v1 sub-routers (auth, subscriptions, changes) under their path prefixes. |
| `api/v1/auth.py` | API-key endpoints: create a key (full key shown once), list, and delete/revoke keys. |
| `api/v1/subscriptions.py` | CRUD for subscriptions with per-tier subscription caps, SSRF webhook-URL validation, and one-time signing-secret return. |
| `api/v1/changes.py` | Change-feed endpoints: paginated list, full-text search, and single-change detail — all scoped to the key's active subscriptions. |

### Backend — Core logic (`backend/app/core/`)

| File | Description |
|------|-------------|
| `database.py` | SQLAlchemy engine/session setup and the `get_db` dependency. |
| `api_key_utils.py` | Generates CSPRNG `lh_live_…` keys and hashes incoming keys (SHA-256) for lookup; stores only hash + display prefix. |
| `ai_processor.py` | Calls the Claude API to turn raw regulatory text into a plain-language summary, severity, and structured `{added, removed, modified}` diff. |
| `rate_limiter.py` | Redis sliding-window rate limiter with dual minute/day windows, tiered per API key. |
| `webhook_signing.py` | HMAC-SHA256 signing of outbound webhook payloads plus an inbound verification helper for SDK/docs. |
| `webhook_validator.py` | SSRF guard for subscriber webhook URLs — blocks loopback/private/metadata IP ranges at create/update time. |

### Backend — Auth, middleware, models

| File | Description |
|------|-------------|
| `dependencies/auth.py` | FastAPI dependency that authenticates every protected request by hashing the Bearer key and loading the active `APIKey`. |
| `middleware/rate_limit.py` | Pre-request middleware that resolves the key's tier (Redis-cached), enforces minute/day limits, and adds `X-RateLimit-*` headers (429 on breach). |
| `models/base.py` | SQLAlchemy `DeclarativeBase` that all ORM models inherit from. |
| `models/api_key.py` | `APIKey` model — name, key hash, display prefix, tier, active flag. |
| `models/subscription.py` | `Subscription` model — owning key, jurisdiction/industry/topics, webhook URL, severity threshold, active flag. |
| `models/change.py` | `Change` model — source metadata, AI summary/severity/diff, processing status, and detection timestamps. |
| `models/webhook_delivery.py` | `WebhookDelivery` model — per-attempt delivery history (status, retries, failure reasons) for each change × subscription. |

### Backend — Scrapers (`backend/app/scrapers/`)

| File | Description |
|------|-------------|
| `base.py` | Abstract `BaseScraper`: hardened HTTP fetch (size cap, redirect limit, timeouts), HTML→text stripping, and content hashing. |
| `registry.py` | Central `ACTIVE_SCRAPERS` list iterated by the Celery beat job every 15 minutes. |
| `rbi.py` | Reserve Bank of India "What's New" scraper (IN / fintech). |
| `sebi.py` | SEBI circulars scraper (India securities regulator). |
| `sec.py` | US SEC rulemaking scraper. |
| `fca.py` | UK FCA publications scraper (currently disabled in the registry). |
| `mas.py` | Monetary Authority of Singapore news scraper (SG). |
| `asic.py` | Australian Securities & Investments Commission news scraper (AU). |

### Backend — Workers (`backend/app/workers/`)

| File | Description |
|------|-------------|
| `celery_app.py` | Celery app config: Redis broker/backend and the 15-minute beat schedule that triggers all scrapers. |
| `scraper_tasks.py` | Tasks that fan out to each scraper (with per-scraper Redis locks), compare hashes, and store new raw changes. |
| `ai_tasks.py` | Task that loads a raw change, runs it through `ai_processor`, writes back summary/severity/diff, marks it `ready` (with retries). |
| `webhook_tasks.py` | On a `ready` change, finds matching active subscriptions and creates + fires one signed `WebhookDelivery` each, with a retry schedule. |
| `webhook.py` | Hardened delivery worker that re-resolves DNS at send time and pins it to a validated IP (TOCTOU / DNS-rebinding protection) while keeping SNI/cert valid. |

### Frontend (`frontend_antigravity/src/`)

| File | Description |
|------|-------------|
| `main.tsx` | React entry point — mounts `<App>` inside `BrowserRouter` and imports global styles. |
| `App.tsx` | Route table: marketing `/` and `/pricing`, plus the nested authenticated `/dashboard/*` routes (wrapped in an error boundary). |
| `pages/Home/Home.tsx` | Marketing landing page composing Navbar, Hero, FeatureHighlights, CTABanner, and Footer. |
| `styles/variables.css` | The design-token system — CSS custom properties for colors, type weights, spacing, radius, and transition timing. |
| `styles/index.css` | Global reset, font import, base element styles, the SVG grain overlay, and shared `.btn` classes. |
| `lib/apiClient.ts` | Typed fetch wrapper for the backend (subscriptions + changes), Bearer-header injection, 401 bounce, and `{field, error}`-aware error normalization. |
| `lib/ApiKeyContext.tsx` | React context holding the API key **in memory only** and exposing a memoized API client that self-clears on 401. |
| `components/Navbar/` | Top marketing navigation bar with mobile menu. |
| `components/Hero/` | Landing hero section with animated headline and a sample webhook-payload code card. |
| `components/FeatureHighlights/` | Alternating two-column scroll-reveal sections (webhooks, AI analysis, coverage). |
| `components/SocialProof/` | Marketing social-proof / logos strip. |
| `components/Pricing/` | Four-tier pricing page with monthly/annual toggle and a full feature comparison table. |
| `components/CTABanner/` | Reusable bottom call-to-action banner (free-tier copy + "Get API Key"). |
| `components/Footer/` | Site-wide footer with link columns and legal row. |
| `components/Dashboard/Dashboard.tsx` | Authenticated shell — sidebar nav, tier badge, disconnect button, and the nested-route `<Outlet>`. |
| `components/Dashboard/AuthGate.tsx` | Full-screen gate that validates a pasted API key (by probing the API) before granting dashboard access. |
| `components/Dashboard/ErrorBoundary.tsx` | Class error boundary wrapping the dashboard so a bad response shows a reload fallback instead of a blank screen. |
| `components/Dashboard/Overview/` | Stub "Overview" page (coming-soon placeholder). |
| `components/Dashboard/Subscriptions/` | Full subscriptions manager — table, create/edit slide-over, one-time signing-secret callout, pause/resume toggle, delete confirm. |
| `components/Dashboard/ChangeFeed/` | Change feed — filterable/searchable list with a side-panel detail view rendering the added/removed/modified diff. |
| `components/Dashboard/ApiKeys/` | Stub "API Keys" page (coming-soon placeholder). |

### Python SDK (`lawhook-python/`)

| File | Description |
|------|-------------|
| `lawhook/client.py` | `LawhookClient` with `subscriptions` and `changes` resource groups wrapping the REST API. |
| `lawhook/models.py` | Lightweight (non-Pydantic) dataclass response models with forward-compatible `from_dict()` parsing. |
| `lawhook/exceptions.py` | `LawhookError` exception hierarchy (e.g. `NotFoundError`) for broad or specific error handling. |
| `tests/test_client.py` | Unit tests for the Python client. |

### TypeScript SDK (`lawhook-typescript/`)

| File | Description |
|------|-------------|
| `src/index.ts` | Public entry point re-exporting the client, option types, and error classes. |
| `src/client.ts` | `LawhookClient` (camelCase API) with `subscriptions` and `changes` methods over `fetch`. |
| `src/models.ts` | TypeScript interfaces for subscriptions, changes, and paginated responses. |
| `src/exceptions.ts` | Error-class hierarchy mirroring the Python SDK. |
| `tests/client.test.ts` | Unit tests for the TypeScript client. |
