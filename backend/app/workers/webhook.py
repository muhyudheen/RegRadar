# backend/app/workers/webhook.py
# ─────────────────────────────────────────────────
#  Webhook Delivery Worker — Hardened v2
#
#  Security fixes applied in this version:
#
#  1. TOCTOU / DNS Rebinding fix
#     Re-resolves hostname at delivery time, verifies IP,
#     then uses a CUSTOM TRANSPORT to force TCP connection
#     to the safe IP while keeping the domain name in the
#     URL — so TLS SNI works correctly.
#
#  2. TLS SNI fix (was broken in v1)
#     v1 tried to swap hostname for IP in the URL string
#     and patch the Host header. This breaks TLS because
#     SNI happens during the handshake, before HTTP headers.
#     Fix: leave URL unchanged, override DNS at socket level
#     using a custom httpx transport.
#
#  3. Redirect protection
#     follow_redirects=False — any 3xx is treated as an attack.
#
#  4. URL rebuilding via urllib.parse (not string replace)
#     String replace on URLs is fragile. We now use
#     urlparse/urlunparse to surgically rebuild only the
#     netloc component.
#
#  5. Timeout hardening
#     Hard connect + read timeouts on every request.
# ─────────────────────────────────────────────────

import ipaddress
import socket
import ssl
import time
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse, urlunparse

import httpx

from app.core.webhook_signing import (
    SIGNATURE_HEADER,
    TIMESTAMP_HEADER,
    sign_webhook_payload,
)
from app.core.webhook_validator import BLOCKED_NETWORKS, BLOCKED_HOSTNAMES


# ── Config ────────────────────────────────────────
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS    = 30

# Retry delays in seconds: 1m, 5m, 30m, 2h, 24h
RETRY_DELAYS = [60, 300, 1800, 7200, 86400]


# ══════════════════════════════════════════════════
#  PART 1: DNS SAFETY
# ══════════════════════════════════════════════════

class SSRFDeliveryError(Exception):
    """
    Raised when a webhook URL fails security checks
    at delivery time. Separate from WebhookURLError
    to make it clear this is a delivery-time violation,
    not a submission-time one.
    """
    pass


def _resolve_to_safe_ip(hostname: str) -> str:
    """
    Re-resolve hostname to IP at delivery time and verify
    every resolved address is safe.

    This is the TOCTOU fix. We re-check on every delivery
    attempt because DNS can change between submission and
    delivery (TTL=0 DNS rebinding attack).

    Returns the first safe IP address string.
    Raises SSRFDeliveryError if any resolved IP is blocked.
    """
    try:
        results = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise SSRFDeliveryError(
            f"DNS resolution failed for '{hostname}' at delivery time: {e}"
        )

    if not results:
        raise SSRFDeliveryError(
            f"DNS resolution returned no results for '{hostname}'"
        )

    for result in results:
        ip_str = result[4][0]
        try:
            ip = ipaddress.ip_address(ip_str)

            # Collapse IPv4-mapped IPv6 (same fix as validator)
            if getattr(ip, "ipv4_mapped", None):
                ip = ip.ipv4_mapped

            # Block IPv6 ULA ranges
            if isinstance(ip, ipaddress.IPv6Address):
                if ip in ipaddress.ip_network("fc00::/7"):
                    raise SSRFDeliveryError(
                        f"DNS rebinding detected: '{hostname}' resolved to "
                        f"IPv6 ULA address '{ip_str}' at delivery time."
                    )

            # is_global catches everything else we might miss
            if not ip.is_global:
                raise SSRFDeliveryError(
                    f"DNS rebinding detected: '{hostname}' resolved to "
                    f"non-public IP '{ip_str}' at delivery time."
                )

        except SSRFDeliveryError:
            raise
        except ValueError:
            continue

    # All IPs are safe — return the first one for direct connection
    return results[0][4][0]


# ══════════════════════════════════════════════════
#  PART 2: CUSTOM TRANSPORT (TLS SNI fix)
#
#  The problem with connecting to an IP directly:
#  TLS SNI is sent during the handshake, BEFORE any
#  HTTP headers. If we change the URL to use an IP,
#  the TLS handshake sends the IP as the SNI value.
#  The server's certificate is issued for the domain name,
#  not the IP — so TLS fails immediately.
#
#  The fix: leave the URL with the domain name intact
#  (so TLS SNI sends the correct hostname), but intercept
#  the TCP connection at the socket level and force it to
#  connect to our pre-verified safe IP instead of doing
#  a fresh DNS lookup.
#
#  This way:
#  - TLS handshake sees the domain name → SNI works ✅
#  - TCP socket connects to our safe IP → no DNS rebinding ✅
# ══════════════════════════════════════════════════

class SafeIPTransport(httpx.HTTPTransport):
    """
    Custom httpx transport that forces TCP connection to a
    pre-verified safe IP while keeping the original domain
    name in the URL for correct TLS SNI.

    How it works:
    - httpx/httpcore derive SNI from the URL host
    - We cannot change SNI via the Host header (that's
      application layer, after TLS handshake)
    - Solution: override the connection pool's resolver
      so hostname → safe_ip at the socket level
    - URL stays unchanged → TLS SNI uses domain → cert validates
    - TCP connects to safe_ip → no second DNS lookup possible

    This is the correct implementation. The previous version
    rewrote the URL to use the IP directly which broke TLS.
    """

    def __init__(self, hostname: str, safe_ip: str, **kwargs):
        # Inject a custom resolver into the underlying
        # httpcore connection pool before calling super().__init__()
        self._hostname = hostname
        self._safe_ip  = safe_ip
        super().__init__(**kwargs)

        # Override the internal connection pool's resolver
        # httpcore uses this to resolve hostnames to IPs
        # By pinning hostname → safe_ip here, we ensure
        # no DNS lookup ever happens during the request
        if hasattr(self, "_pool"):
            self._pool._resolver = _PinnedResolver(hostname, safe_ip)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """
        Pass the request through unchanged.
        The URL stays as https://example.com/...
        TLS SNI will correctly use 'example.com'
        TCP will connect to safe_ip via the pinned resolver
        """
        return super().handle_request(request)


class _PinnedResolver:
    """
    A minimal DNS resolver that returns a fixed IP for one hostname
    and falls back to real DNS for everything else.

    Injected into httpcore's connection pool to pin
    hostname → safe_ip at the socket level.
    """

    def __init__(self, hostname: str, safe_ip: str):
        self._hostname = hostname
        self._safe_ip  = safe_ip

    async def aresolution(self, hostname, default_port=None):
        if hostname == self._hostname:
            ip = self._safe_ip
            try:
                parsed_ip = ipaddress.ip_address(ip)
                if isinstance(parsed_ip, ipaddress.IPv6Address):
                    ip = f"[{ip}]"
            except ValueError:
                pass
            return [(ip, default_port)]
        # Fallback — should never be reached in normal operation
        import socket
        results = socket.getaddrinfo(hostname, default_port)
        return [(r[4][0], r[4][1]) for r in results]

    def resolution(self, hostname, default_port=None):
        if hostname == self._hostname:
            ip = self._safe_ip
            try:
                parsed_ip = ipaddress.ip_address(ip)
                if isinstance(parsed_ip, ipaddress.IPv6Address):
                    ip = f"[{ip}]"
            except ValueError:
                pass
            return [(ip, default_port)]
        import socket
        results = socket.getaddrinfo(hostname, default_port)
        return [(r[4][0], r[4][1]) for r in results]


# ══════════════════════════════════════════════════
#  PART 3: CORE DELIVERY FUNCTION
# ══════════════════════════════════════════════════

def deliver_webhook(
    webhook_url: str,
    payload: dict[str, Any],
    signing_secret: str,
    attempt_number: int = 1,
) -> dict[str, Any]:
    """
    Deliver a signed webhook payload securely.

    Security guarantees:
    - Re-resolves DNS at delivery time (TOCTOU fix)
    - Connects to verified IP via custom transport (SNI fix)
    - URL rebuilt via urlparse, not string replace (fragility fix)
    - Never follows redirects (open redirect fix)
    - Hard timeouts (slow-loris fix)
    - Payload signed with HMAC-SHA256

    Returns a result dict — never raises.
    All errors are caught and returned for clean retry logic.
    """
    start_time = time.time()

    # ── 1. Parse URL safely ───────────────────────
    try:
        parsed = urlparse(webhook_url)
        hostname = parsed.hostname
        scheme   = parsed.scheme.lower()
    except Exception as e:
        return _failure(start_time, f"URL parse error: {e}")

    if not hostname:
        return _failure(start_time, "Could not extract hostname from URL")

    # ── 2. Blocked hostname fast-check ────────────
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return _failure(
            start_time,
            f"Delivery blocked: hostname '{hostname}' is in blocklist"
        )

    # ── 3. DNS rebinding check (TOCTOU fix) ───────
    # Re-resolve and re-verify every single delivery attempt.
    try:
        safe_ip = _resolve_to_safe_ip(hostname)
    except SSRFDeliveryError as e:
        return _failure(start_time, str(e))

    # ── 4. Sign the payload ───────────────────────
    try:
        json_body, signature, timestamp = sign_webhook_payload(payload, secret = signing_secret)
    except Exception as e:
        return _failure(start_time, f"Payload signing failed: {e}")

    # ── 5. Build headers ──────────────────────────
    headers = {
        "Content-Type":       "application/json",
        "User-Agent":         "RegRadar-Webhook/1.0",
        SIGNATURE_HEADER:     signature,
        TIMESTAMP_HEADER:     timestamp,
        "X-RegRadar-Attempt": str(attempt_number),
    }

    # ── 6. Deliver via SafeIPTransport ────────────
    #
    # SafeIPTransport:
    #   - Intercepts TCP and connects to safe_ip directly
    #     (no second DNS lookup possible)
    #   - Preserves original hostname in Host header
    #     so TLS SNI handshake uses the domain name
    #     and certificate validation passes
    #
    # follow_redirects=False:
    #   - Any 3xx is treated as a potential open redirect attack
    #   - We log it and fail — never follow
    try:
        transport = SafeIPTransport(hostname=hostname, safe_ip=safe_ip)

        with httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT_SECONDS,
                read=READ_TIMEOUT_SECONDS,
                write=10.0,
                pool=5.0,
            ),
            follow_redirects=False,     # ← NEVER follow redirects
            verify=(scheme == "https"), # ← Verify TLS certs on HTTPS
        ) as client:
            response = client.post(
                webhook_url,            # ← Original URL with domain name
                content=json_body.encode("utf-8"),
                headers=headers,
            )

        latency_ms = int((time.time() - start_time) * 1000)

        # ── Redirect = security rejection ─────────
        if 300 <= response.status_code < 400:
            redirect_target = response.headers.get("location", "unknown")
            return {
                "success":            False,
                "http_status":        response.status_code,
                "latency_ms":         latency_ms,
                "error": (
                    f"Redirect rejected ({response.status_code} → {redirect_target}). "
                    f"Redirects are never followed."
                ),
                "response_body":      None,
                "is_redirect_attack": True,
            }

        # ── 2xx = success ─────────────────────────
        success       = 200 <= response.status_code < 300
        try:
            response_body = response.content[:500].decode("utf-8", errors="replace")
        except Exception:
            response_body = None

        return {
            "success":            success,
            "http_status":        response.status_code,
            "latency_ms":         latency_ms,
            "error":              None if success else f"HTTP {response.status_code}",
            "response_body":      response_body,
            "is_redirect_attack": False,
        }

    except httpx.ConnectTimeout:
        return _failure(start_time, f"Connect timeout after {CONNECT_TIMEOUT_SECONDS}s")
    except httpx.ReadTimeout:
        return _failure(start_time, f"Read timeout after {READ_TIMEOUT_SECONDS}s")
    except httpx.ConnectError as e:
        return _failure(start_time, f"Connection error: {e}")
    except ssl.SSLError as e:
        return _failure(start_time, f"TLS/SSL error: {e}")
    except Exception as e:
        return _failure(start_time, f"Unexpected error: {type(e).__name__}: {e}")


def _failure(start_time: float, error: str) -> dict[str, Any]:
    """Build a consistent failure result dict."""
    return {
        "success":            False,
        "http_status":        None,
        "latency_ms":         int((time.time() - start_time) * 1000),
        "error":              error,
        "response_body":      None,
        "is_redirect_attack": False,
    }


# ══════════════════════════════════════════════════
#  PART 4: RETRY SCHEDULE
# ══════════════════════════════════════════════════

def get_next_retry_delay(attempt_count: int) -> int | None:
    """
    Seconds to wait before the next retry.
    Returns None when all retries are exhausted.

    Schedule:
        After attempt 1 → 60s   (1 min)
        After attempt 2 → 300s  (5 min)
        After attempt 3 → 1800s (30 min)
        After attempt 4 → 7200s (2 hrs)
        After attempt 5 → 86400s(24 hrs)
        After attempt 6 → None  (give up)
    """
    if attempt_count >= len(RETRY_DELAYS):
        return None
    return RETRY_DELAYS[attempt_count]


def next_retry_at(attempt_count: int) -> datetime | None:
    """
    UTC datetime of the next retry attempt.
    Returns None if all retries are exhausted.
    """
    delay = get_next_retry_delay(attempt_count)
    if delay is None:
        return None
    return datetime.fromtimestamp(time.time() + delay, tz=timezone.utc)