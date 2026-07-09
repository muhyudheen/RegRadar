# Redis Access Pattern Report

Date: 2026-07-08
Project: Lawhook backend

## Executive Summary

There is no single centralized Redis client module currently shared across the backend. Redis access follows a context-specific pattern:

- API middleware creates and holds its own Redis client instance.
- Core rate-limit logic receives a Redis client via dependency injection.
- Workers access Redis through Celery's configured backend client.

For dispatcher work (including `last_scraped:<jurisdiction>` keys), worker code should match the existing worker pattern and use `celery_app.backend.client`.

## Findings

### 1) API Path (Middleware-Scoped Client)

The rate-limit middleware creates a Redis client in `__init__` and reuses it:

- `redis.from_url(...)` construction: `backend/app/middleware/rate_limit.py` (around line 83)
- Middleware registration and `REDIS_URL` injection: `backend/app/main.py` (line 35)

Implication: API requests do not use a global Redis helper module; they use middleware-owned client state.

### 2) Core Logic (Dependency Injection)

Core rate-limit functions do not create Redis connections. They require a caller-provided client:

- `check_rate_limit(redis_client: redis.Redis, ...)`: `backend/app/core/rate_limiter.py` (around line 107)

Implication: `core/` logic is intentionally Redis-client agnostic and reusable.

### 3) Worker Path (Celery-Backed Client)

Celery is configured to use Redis for both broker and backend:

- Celery setup using `REDIS_URL`: `backend/app/workers/celery_app.py` (lines 6-7)

Scraper tasks then access Redis through Celery's backend client:

- `redis_client = celery_app.backend.client`: `backend/app/workers/scraper_tasks.py` (around line 73)

Implication: worker tasks currently reuse Celery's Redis client rather than creating a separate `redis.from_url(...)` client.

## Existing Redis Key Patterns

Observed naming conventions in use:

- Rate-limit keys: `rl:<window>:<identity>`
- Principal cache keys: `princ:<key_hash>`
- Scraper lock keys: `scraper_lock:<scraper_class_name>`

This supports adding dispatcher keys in the same style, e.g. `last_scraped:<jurisdiction>`.

## Environment and URL Defaults

`REDIS_URL` is set in docker-compose:

- `docker-compose.yml`: `REDIS_URL=redis://redis:6379/0`

Fallback defaults differ by runtime context:

- API fallback: `redis://localhost:6379/0` in `backend/app/main.py`
- Worker/Celery fallback: `redis://redis:6379/0` in `backend/app/workers/celery_app.py`

In containerized runs, compose-provided `REDIS_URL` normalizes this.

## Recommendation for Dispatcher

If the dispatcher runs in worker context, match existing worker conventions:

1. Import `celery_app` from `backend/app/workers/celery_app.py`.
2. Use `redis_client = celery_app.backend.client`.
3. Read/write keys with namespace format `last_scraped:<jurisdiction>`.

This keeps connection behavior consistent with existing worker tasks and avoids introducing a second Redis client pattern in workers.

## Conclusion

Current architecture is not a single global Redis wrapper; it is pattern-based by execution context. For dispatcher persistence, the closest and most consistent existing approach is Celery backend client reuse in workers.
