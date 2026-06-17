# ─────────────────────────────────────────────────
#  Sliding Window Rate Limiter — Tiered, Dual-Window
#
#  Algorithm: sliding window log using Redis sorted sets
#  - Each API key has a sorted set in Redis, per window
#  - Score = timestamp in milliseconds
#  - Member = unique request ID (uuid)
#
#  Two windows are checked on EVERY request:
#    - minute  (burst protection)
#    - day     (quota protection)
#
#  Both windows' stats are always returned so the
#  middleware can expose full visibility via headers,
#  even on requests that get blocked.
#
#  Increment behavior:
#  - minute window: check + increment atomically
#  - If minute blocks → day window is PEEKED (read-only,
#    no increment) — a blocked request doesn't consume
#    a day-quota slot
#  - If minute allows → day window: check + increment
#
#  Tiers (set on api_keys.tier, default "free"):
#    free       —    60 req/min,     1,000 req/day
#    pro        —   600 req/min,    50,000 req/day
#    enterprise — 6,000 req/min, 1,000,000 req/day
#
#  No billing/upgrade endpoint yet — tier is set manually:
#    UPDATE api_keys SET tier = 'pro' WHERE id = '...';
# ─────────────────────────────────────────────────

import time
import uuid
import logging
import os
from dataclasses import dataclass

import redis

logger = logging.getLogger(__name__)

# ── Tier limits (override defaults via env if needed) ─
TIER_LIMITS: dict[str, dict[str, int]] = {
    "free": {
        "minute": int(os.getenv("RATE_LIMIT_FREE_PER_MINUTE", "60")),
        "day":    int(os.getenv("RATE_LIMIT_FREE_PER_DAY", "1000")),
    },
    "pro": {
        "minute": int(os.getenv("RATE_LIMIT_PRO_PER_MINUTE", "600")),
        "day":    int(os.getenv("RATE_LIMIT_PRO_PER_DAY", "50000")),
    },
    "enterprise": {
        "minute": int(os.getenv("RATE_LIMIT_ENTERPRISE_PER_MINUTE", "6000")),
        "day":    int(os.getenv("RATE_LIMIT_ENTERPRISE_PER_DAY", "1000000")),
    },
}
 
DEFAULT_TIER = "free"
 
# ── Window sizes in milliseconds ──────────────────
WINDOW_MINUTE_MS = 60 * 1000
WINDOW_DAY_MS    = 24 * 60 * 60 * 1000


@dataclass
class RateLimitResult:
    allowed:      bool
    limit:        int
    remaining:    int
    reset_at_ms:  int
    window:       str   
    
    
@dataclass
class RateLimitCheck:
    """
    Combined result of both windows for a single request.
 
    `allowed` is the overall decision — False if EITHER
    window is over limit. `minute` and `day` are always
    populated so the middleware can expose full headers
    regardless of which window (if any) blocked.
    """
    allowed: bool
    minute: RateLimitResult
    day: RateLimitResult
    tier: str
    
    @property
    def blocking(self) -> RateLimitResult:
        """The window that caused the block. Only meaningful if allowed=False."""
        return self.minute if not self.minute.allowed else self.day
    
    
def check_rate_limit(
    redis_client: redis.Redis,
    key_hash: str,
    tier: str = DEFAULT_TIER,
) -> RateLimitCheck:
    """
    Check and record a request against rate limits for the
    given tier. Always checks BOTH the minute and day windows
    so callers have full visibility regardless of outcome.
 
    Unknown tiers fall back to DEFAULT_TIER limits — this
    fails safe (most restrictive) rather than failing open
    if a bad tier value ever ends up on an api_key row.
 
    Uses Lua scripts for atomicity — check + increment
    happens in one Redis round trip with no race conditions.
    """
    limits = TIER_LIMITS.get(tier)
    if limits is None:
        logger.warning(f"Unknown tier '{tier}' — falling back to '{DEFAULT_TIER}'")
        tier = DEFAULT_TIER
        limits = TIER_LIMITS[DEFAULT_TIER]
        
    now_ms = int(time.time() * 1000)
    
    # Checking minute window first
    minute_result = _check_window(
        redis_client=redis_client,
        key_hash=key_hash,
        window_ms=WINDOW_MINUTE_MS,
        limit=limits["minute"],
        window_name="minute",
        now_ms=now_ms,
    )
    
    if not minute_result.allowed:
        # Blocked by minute window — PEEK day window for
        # reporting only. Do not increment: a blocked
        # request shouldn't consume a day-quota slot.
        day_result = _peek_window(
            redis_client=redis_client,
            key_hash=key_hash,
            window_ms=WINDOW_DAY_MS,
            limit=limits["day"],
            window_name="day",
            now_ms=now_ms,
        )
        
        return RateLimitCheck(
            allowed=False,
            minute=minute_result,
            day=day_result,
            tier=tier,
        )
        
    # Minute allowed - check + increment day window
    day_result = _check_window(
        redis_client=redis_client,
        key_hash=key_hash,
        window_ms=WINDOW_DAY_MS,
        limit=limits["day"],
        window_name="day",
        now_ms=now_ms,   
    )
    
    return RateLimitCheck(
        allowed=day_result.allowed,
        minute=minute_result,
        day=day_result,
        tier=tier,
    )
    

def _check_window(
    redis_client: redis.Redis,
    key_hash:    str,
    window_ms:   int,
    limit:       int,
    window_name: str,
    now_ms:      int,
) -> RateLimitResult:
    """
    Check a single time window using a Redis sorted set.
    Atomic via Lua script — check + increment, no race
    conditions. If over limit, does NOT add an entry.
    """
    redis_key     = f"rl:{window_name}:{key_hash}"
    window_start  = now_ms - window_ms
    request_id    = str(uuid.uuid4())
    
    # KEYS[1] = redis_key
    # ARGV[1] = window_start (remove older than this)
    # ARGV[2] = limit
    # ARGV[3] = now_ms (score for new entry)
    # ARGV[4] = request_id (member for new entry)
    # ARGV[5] = ttl_seconds (key expiry)
    lua_script = """
    local key           = KEYS[1]
    local window_start  = tonumber(ARGV[1])
    local limit         = tonumber(ARGV[2])
    local now_ms        = tonumber(ARGV[3])
    local request_id    = ARGV[4]
    local ttl_seconds   = tonumber(ARGV[5])
 
    -- Remove entries outside the window
    redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
 
    -- Count current entries
    local count = redis.call('ZCARD', key)
 
    if count >= limit then
        -- Over limit — get oldest entry to compute reset time
        local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
        return {0, count, oldest[2] or now_ms}
    end
 
    -- Under limit — record this request
    redis.call('ZADD', key, now_ms, request_id)
    redis.call('EXPIRE', key, ttl_seconds)
 
    local remaining = limit - count - 1
    return {1, remaining, now_ms}
    """
    
    ttl_seconds = (window_ms // 1000) + 60   # window + buffer
    
    try:
        result = redis_client.eval(
            lua_script,
            1,
            redis_key,
            str(window_start),
            str(limit),
            str(now_ms),
            request_id,
            str(ttl_seconds),
        )
        
        allowed = bool(result[0])
        remaining = int(result[1])
        oldest_ms = int(result[2])
        
        reset_at_ms = oldest_ms + window_ms
        
        return RateLimitResult(
            allowed     = allowed,
            limit       = limit,
            remaining   = remaining if allowed else 0,
            reset_at_ms = reset_at_ms,
            window      = window_name,
        )
        
    except Exception as e:
        # Redis Failure - Fail Open (allow request)
        logger.error(f"Rate limiter Redis error ({window_name}): {e} — failing open")
        return RateLimitResult(
            allowed     = True,
            limit       = limit,
            remaining   = limit,
            reset_at_ms = now_ms + window_ms,
            window      = window_name,
        )
        
        
def _peek_window(
    redis_client: redis.Redis,
    key_hash:    str,
    window_ms:   int,
    limit:       int,
    window_name: str,
    now_ms:      int,
) -> RateLimitResult:
    """
    Read-only check of a window's current state — does NOT
    record a new entry. Used for header reporting on the
    window that did not cause a block (e.g. reporting day
    stats when the request was blocked by the minute window).
 
    Trims expired entries (cheap maintenance, same as
    _check_window) but never calls ZADD.
    """
    redis_key = f"rl:{window_name}:{key_hash}"
    window_start = now_ms - window_ms
    
    # KEYS[1] = redis_key
    # ARGV[1] = window_start
    lua_script = """
    local key          = KEYS[1]
    local window_start = tonumber(ARGV[1])
 
    redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)
 
    local count  = redis.call('ZCARD', key)
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
 
    return {count, oldest[2] or 0}
    """
    
    try:
        result = redis_client.eval(
            lua_script,
            1,
            redis_key,
            str(window_start)
        )
        
        count = int(result[0])
        oldest_ms = int(result[1])
        
        allowed = count < limit
        remaining = remaining = max(0, limit - count)
        reset_at_ms = (oldest_ms + window_ms) if oldest_ms else (now_ms + window_ms)
        
        return RateLimitResult(
            allowed     = allowed,
            limit       = limit,
            remaining   = remaining,
            reset_at_ms = reset_at_ms,
            window      = window_name,
        )
        
    except Exception as e:
        logger.error(f"Rate limiter Redis error (peek {window_name}): {e} — failing open")
        return RateLimitResult(
            allowed     = True,
            limit       = limit,
            remaining   = limit,
            reset_at_ms = now_ms + window_ms,
            window      = window_name,
        )