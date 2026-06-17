# backend/app/workers/webhook.py
# ─────────────────────────────────────────────────
#  Webhook Delivery Worker — Hardened v3
#
#  Security fixes applied in this version:
#
#  1. TOCTOU / DNS Rebinding fix
#     Re-resolves hostname at delivery time, verifies IP,
#     then rewrites the request URL to use the validated IP
#     directly — so no second DNS lookup is ever possible.
#
#  2. TLS SNI fix (v2 was broken — _PinnedResolver no-op)
#     v2 tried to swap httpcore's internal _resolver attribute.
#     On httpcore 1.0.9, hasattr(pool, '_resolver') == False,
#     so the injection silently did nothing.
#
#     v3 fix: rewrite URL to IP + custom SSL context that
#     pins server_hostname to the original domain for SNI.
#
#     How it works:
#       - URL rewritten to IP → httpcore connects to safe IP
#         (no DNS resolution possible — we give it an IP, not hostname)
#       - Custom SSL context → wrap_socket always gets original
#         domain as server_hostname → SNI correct → cert validates
#       - Host header set to original hostname → HTTP routing works
#
#     No private httpcore internals touched.
#
#  3. Redirect protection
#     follow_redirects=False — any 3xx is treated as an attack.
#
#  4. URL rebuilding via urllib.parse (not string replace)
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
from app.core.webhook_validator import BLOCKED_HOSTNAMES


# ── Config ────────────────────────────────────────
CONNECT_TIMEOUT_SECONDS = 10
READ_TIMEOUT_SECONDS    = 30

# Retry delays in seconds: 1m, 5m, 30m, 2h, 24h
RETRY_DELAYS = [60, 300, 1800, 7200, 86400]

# Default ports by scheme
_DEFAULT_PORTS = {"https": 443, "http": 80}


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

            # Collapse IPv4-mapped IPv6
            if getattr(ip, "ipv4_mapped", None):
                ip = ip.ipv4_mapped

            # Block IPv6 ULA ranges
            if isinstance(ip, ipaddress.IPv6Address):
                if ip in ipaddress.ip_network("fc00::/7"):
                    raise SSRFDeliveryError(
                        f"DNS rebinding detected: '{hostname}' resolved to "
                        f"IPv6 ULA address '{ip_str}' at delivery time."
                    )

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
#  PART 2: CUSTOM TRANSPORT (TLS SNI + IP pinning fix)
#
#  v2 PROBLEM:
#  _PinnedResolver was injected into httpcore's _pool._resolver
#  but on httpcore 1.0.9, ConnectionPool has no _resolver attribute.
#  The injection silently did nothing. Dead code.
#
#  v3 SOLUTION — two parts working together:
#
#  Part A — URL rewriting:
#    Rewrite request URL to use the pre-validated IP directly.
#    httpcore sees "https://1.2.3.4/..." and connects to that IP.
#    No hostname → no DNS lookup → TOCTOU closed permanently.
#
#  Part B — Pinned SSL context:
#    When URL uses an IP, httpcore passes the IP as server_hostname
#    to ssl.wrap_socket() → TLS SNI sends "1.2.3.4" → cert for
#    "example.com" fails validation.
#
#    Fix: Custom SSL context that wraps wrap_socket() and forces
#    server_hostname to always be the original domain, regardless
#    of what IP httpcore tries to pass.
#    → SNI sends "example.com" → cert validates correctly ✅
#
#  Part C — Host header:
#    HTTP/1.1 requires Host: header to contain the domain name,
#    not the IP. We explicitly set it to the original hostname.
# ══════════════════════════════════════════════════

def _make_pinned_ssl_context(original_hostname: str) -> ssl.SSLContext:
    """
    Create an SSL context that always uses original_hostname for
    SNI and certificate validation, regardless of what IP address
    is in the URL.

    This is the TLS fix: we connect to an IP (preventing DNS
    rebinding) but the TLS handshake still validates the certificate
    against the original domain name.

    Implementation: monkey-patches wrap_socket on the context
    instance (not the class) to intercept httpcore's SNI setting.
    """
    ctx = ssl.create_default_context()

    # Save the original wrap_socket method
    _real_wrap_socket = ctx.wrap_socket

    def _pinned_wrap_socket(sock: ssl.SSLSocket, server_hostname: str | None = None, **kwargs) -> ssl.SSLSocket:
        # Always use the original domain name for SNI + cert validation
        # Ignore whatever IP httpcore tries to pass as server_hostname
        return _real_wrap_socket(sock, server_hostname=original_hostname, **kwargs)

    # Patch only this context instance, not the class
    ctx.wrap_socket = _pinned_wrap_socket  # type: ignore[method-assign]
    return ctx


def _build_netloc_with_ip(safe_ip: str, port: int) -> str:
    """
    Build a netloc string with a raw IP and port.
    IPv6 addresses are wrapped in brackets per RFC 2732.

    Examples:
        "1.2.3.4", 443  → "1.2.3.4:443"
        "::1",     443  → "[::1]:443"
    """
    try:
        ip = ipaddress.ip_address(safe_ip)
        if isinstance(ip, ipaddress.IPv6Address):
            return f"[{safe_ip}]:{port}"
    except ValueError:
        pass
    return f"{safe_ip}:{port}"


class SafeIPTransport(httpx.HTTPTransport):
    """
    Custom httpx transport that:
      1. Rewrites the request URL to use a pre-validated IP directly
         → no DNS lookup possible → TOCTOU/DNS rebinding closed
      2. Uses a pinned SSL context to keep original hostname for SNI
         → TLS certificate validation still works correctly
      3. Preserves the Host header with the original hostname
         → HTTP routing works correctly on the server side

    Works on any version of httpcore — no private attributes accessed.
    """

    def __init__(self, hostname: str, safe_ip: str, scheme: str, port: int, **kwargs):
        self._hostname = hostname
        self._safe_ip  = safe_ip
        self._scheme   = scheme
        self._port     = port

        # Inject pinned SSL context for HTTPS connections
        if scheme == "https":
            kwargs.setdefault("verify", _make_pinned_ssl_context(hostname))

        super().__init__(**kwargs)

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        """
        Rewrite the request to connect directly to safe_ip.

        - URL netloc replaced with IP:port
          → httpcore connects to IP, no DNS resolution
        - Host header set to original hostname
          → HTTP/1.1 routing works correctly
        - SSL context (set in __init__) ensures SNI uses hostname
          → TLS cert validation passes
        """
        # Build new netloc using the pre-validated IP
        new_netloc = _build_netloc_with_ip(self._safe_ip, self._port)

        # Rebuild URL with IP netloc, keep everything else (path, query, fragment)
        parsed = urlparse(str(request.url))
        new_url = urlunparse(parsed._replace(netloc=new_netloc))

        # Build headers — preserve all original headers but force Host
        # to the original hostname (not the IP we just put in the URL)
        headers = dict(request.headers)
        headers["host"] = self._hostname

        new_request = httpx.Request(
            method=request.method,
            url=new_url,
            headers=headers,
            content=request.content,
        )

        return super().handle_request(new_request)


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
    - Connects to verified IP via URL rewriting (no private httpcore APIs)
    - TLS SNI pinned to original hostname via custom SSL context
    - URL rebuilt via urlparse, not string replace
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
        port     = parsed.port or _DEFAULT_PORTS.get(scheme, 443)
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
    # Re-resolve and re-verify on every delivery attempt.
    # DNS can change between attempts — each must be validated.
    try:
        safe_ip = _resolve_to_safe_ip(hostname)
    except SSRFDeliveryError as e:
        return _failure(start_time, str(e))

    # ── 4. Sign the payload ───────────────────────
    try:
        json_body, signature, timestamp = sign_webhook_payload(
            payload, secret=signing_secret
        )
    except Exception as e:
        return _failure(start_time, f"Payload signing failed: {e}")

    # ── 5. Build headers ──────────────────────────
    headers = {
        "Content-Type":       "application/json",
        "User-Agent":         "Lawhook-Webhook/1.0",
        SIGNATURE_HEADER:     signature,
        TIMESTAMP_HEADER:     timestamp,
        "X-Lawhook-Attempt":  str(attempt_number),
    }

    # ── 6. Deliver via SafeIPTransport ────────────
    #
    # SafeIPTransport v3:
    #   - Rewrites URL to IP → httpcore connects directly, no DNS
    #   - Pinned SSL context → SNI uses original hostname → cert validates
    #   - Host header → original hostname → server routing works
    #
    # follow_redirects=False:
    #   - Any 3xx is treated as a potential open redirect attack
    try:
        transport = SafeIPTransport(
            hostname=hostname,
            safe_ip=safe_ip,
            scheme=scheme,
            port=port,
        )

        with httpx.Client(
            transport=transport,
            timeout=httpx.Timeout(
                connect=CONNECT_TIMEOUT_SECONDS,
                read=READ_TIMEOUT_SECONDS,
                write=10.0,
                pool=5.0,
            ),
            follow_redirects=False,
        ) as client:
            response = client.post(
                webhook_url,
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
        success = 200 <= response.status_code < 300
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
        After attempt 1 → 60s    (1 min)
        After attempt 2 → 300s   (5 min)
        After attempt 3 → 1800s  (30 min)
        After attempt 4 → 7200s  (2 hrs)
        After attempt 5 → 86400s (24 hrs)
        After attempt 6 → None   (give up)
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