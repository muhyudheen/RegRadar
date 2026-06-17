# backend/app/middleware/rate_limit.py
# ─────────────────────────────────────────────────
#  Rate Limit Middleware — Tiered, Dual-Window
#
#  Runs before every request.
#  Extracts API key from Authorization header,
#  looks up its tier, checks both minute and day
#  windows, returns 429 if either is exceeded.
#
#  Tier lookup:
#    1. Check Redis cache (tier:<key_hash>, 60s TTL)
#    2. On miss — query api_keys table, cache result
#    3. Unknown/revoked key → DEFAULT_TIER ("free")
#       (auth dependency handles the actual 401 —
#       rate limiter just needs *some* tier to check
#       against so it never throws on a bad key)
#
#  Tier changes (e.g. after a billing upgrade) take
#  effect within ~60s due to the cache TTL.
#
#  Routes excluded from rate limiting:
#    /health       ← health checks from load balancers
#    /docs         ← Swagger UI
#    /openapi.json ← OpenAPI schema
#    /redoc        ← ReDoc UI
#
#  Headers added to every response:
#    X-RateLimit-Tier              ← tier used for this request
#    X-RateLimit-Limit-Minute      ← minute window limit
#    X-RateLimit-Remaining-Minute  ← minute window remaining
#    X-RateLimit-Reset-Minute      ← unix ts when minute window resets
#    X-RateLimit-Limit-Day         ← day window limit
#    X-RateLimit-Remaining-Day     ← day window remaining
#    X-RateLimit-Reset-Day         ← unix ts when day window resets
#    Retry-After                   ← seconds to wait (on 429 only)
#
#  Both window pairs are present on EVERY response,
#  including 429s — even if the day window wasn't the
#  one that blocked, its current stats are still shown.
# ─────────────────────────────────────────────────

import hashlib
import json
import logging
import time

import redis
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.database import SessionLocal
from app.core.rate_limiter import DEFAULT_TIER, RateLimitCheck, check_rate_limit
from app.models.api_key import APIKey

logger = logging.getLogger(__name__)

# Routes that skip rate limiting entirely
EXCLUDED_PATHS = {
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
}

# How long to cache key_hash → tier in Redis
TIER_CACHE_TTL_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limit middleware with per-tier,
    dual-window (minute + day) limits.

    Extracts key_hash from Bearer token — never stores
    the raw token in Redis. Uses SHA-256 of the token
    as the Redis key so even if Redis is compromised,
    API keys cannot be recovered.
    """

    def __init__(self, app, redis_url: str):
        super().__init__(app)
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )

    async def dispatch(self, request: Request, call_next):

        # ── Skip excluded paths ───────────────────
        if request.url.path in EXCLUDED_PATHS:
            return await call_next(request)

        # ── Extract Bearer token ──────────────────
        auth_header = request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            # No token — let auth middleware handle it
            # (it will return 401)
            return await call_next(request)

        raw_token = auth_header[len("Bearer "):].strip()

        if not raw_token:
            return await call_next(request)

        # Hash the token — never store raw keys in Redis
        key_hash = hashlib.sha256(raw_token.encode()).hexdigest()

        # ── Resolve tier ───────────────────────────
        tier = self._get_tier(key_hash)

        # ── Check rate limit (both windows) ───────
        check = check_rate_limit(
            redis_client=self.redis_client,
            key_hash=key_hash,
            tier=tier,
        )

        # ── Rate limit exceeded → 429 ─────────────
        if not check.allowed:
            blocking = check.blocking
            reset_seconds = max(
                0, (blocking.reset_at_ms - int(time.time() * 1000)) // 1000
            )

            logger.warning(
                f"Rate limit exceeded for key {key_hash[:16]}... "
                f"tier={check.tier} window={blocking.window} limit={blocking.limit}"
            )

            body = json.dumps({
                "detail": (
                    f"Rate limit exceeded. "
                    f"Your '{check.tier}' plan allows "
                    f"{blocking.limit} requests per {blocking.window}. "
                    f"Try again in {reset_seconds} seconds."
                )
            })

            response = Response(
                content=body,
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": str(reset_seconds)},
            )
            self._add_rate_limit_headers(response, check)
            return response

        # ── Allowed — process request ─────────────
        response = await call_next(request)
        self._add_rate_limit_headers(response, check)
        return response

    # ── Helpers ────────────────────────────────────

    @staticmethod
    def _add_rate_limit_headers(response: Response, check: RateLimitCheck) -> None:
        """Attach full dual-window rate limit headers to a response."""
        response.headers["X-RateLimit-Tier"] = check.tier

        # Reset timestamps are absolute unix seconds (not relative)
        response.headers["X-RateLimit-Limit-Minute"]     = str(check.minute.limit)
        response.headers["X-RateLimit-Remaining-Minute"] = str(check.minute.remaining)
        response.headers["X-RateLimit-Reset-Minute"]     = str(check.minute.reset_at_ms // 1000)

        response.headers["X-RateLimit-Limit-Day"]     = str(check.day.limit)
        response.headers["X-RateLimit-Remaining-Day"] = str(check.day.remaining)
        response.headers["X-RateLimit-Reset-Day"]     = str(check.day.reset_at_ms // 1000)

    # ── Tier lookup ────────────────────────────────

    def _get_tier(self, key_hash: str) -> str:
        """
        Resolve the rate-limit tier for a key hash.

        Checks Redis cache first (fast path, no DB hit on
        most requests). On cache miss, queries api_keys
        and caches the result for TIER_CACHE_TTL_SECONDS.

        Returns DEFAULT_TIER if the key doesn't exist —
        the rate limiter still needs a value to check
        against; the actual 401 for invalid keys is
        handled by the auth dependency, not here.
        """
        cache_key = f"tier:{key_hash}"

        try:
            cached = self.redis_client.get(cache_key)
            if cached:
                return cached
        except Exception as e:
            logger.error(f"Tier cache read error: {e}")

        tier = DEFAULT_TIER

        db = SessionLocal()
        try:
            api_key = (
                db.query(APIKey)
                .filter(APIKey.key_hash == key_hash)
                .first()
            )
            if api_key is not None:
                tier = api_key.tier
        except Exception as e:
            logger.error(f"Tier DB lookup error: {e} — using default tier")
        finally:
            db.close()

        try:
            self.redis_client.set(cache_key, tier, ex=TIER_CACHE_TTL_SECONDS)
        except Exception as e:
            logger.error(f"Tier cache write error: {e}")

        return tier