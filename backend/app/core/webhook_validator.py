#  Webhook URL SSRF Protection

#  Call validate_webhook_url() in:
#    - POST /subscriptions   (on create)
#    - PATCH /subscriptions  (on update)

#  TOCTOU (Time-of-Check to Time-of-Use) vulnerability:   //additional change
#  DNS records can change between when we validate here
#  and when webhook_delivery.py actually fires the request.

import ipaddress
import socket
from urllib.parse import urlparse
import os

from fastapi import HTTPException, status

# ── Blocked IP ranges (RFC 1918 + special purpose) ──
BLOCKED_NETWORKS = [
    # loopback
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    
    # private
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    
    # Link-local / AWS + GCP + Azure metadata endpoints
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
 
    # Docker default bridge network
    ipaddress.ip_network("172.17.0.0/16"),
 
    # Unspecified / broadcast
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("255.255.255.255/32"),
 
    # Shared address space (RFC 6598)
    ipaddress.ip_network("100.64.0.0/10"),
    
    ipaddress.ip_network("fc00::/7"),   # ← IPv6 ULA — NEW
]

# ── Blocked hostnames ─────────────────────────────

BLOCKED_HOSTNAMES = {
    # -- Standard Localhost --
    'localhost',
    'broadcasthost',
    'local',
    
    # -- Docker Compose Services --
    'db', 
    'redis',
    'worker',
    'beat',
    'api',
    
    # -- Docker Host Escapes --
    'host.docker.internal',
    'gateway.docker.internal',
    
    # -- Cloud Metadata --
    'metadata.google.internal', 
    'metadata.goog',
    
    # -- Kubernetes (Future-proofing) --
    'kubernetes.default',
    'kubernetes.default.svc',
    'kubernetes.default.svc.cluster.local'
}

# ── Blocked URL schemes ───────────────────────────
# Only https is allowed in production.
_IS_PROD = os.environ.get("ENVIRONMENT") == "production"
ALLOWED_SCHEMES = {"https"} if _IS_PROD else {"https", "http"}   

class WebHookURLError(Exception):
    """Raised when a webhook URL fails SSRF validation."""
    pass

def is_ip_blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)

        # Collapse IPv4-mapped IPv6 addresses
        # e.g. ::ffff:169.254.169.254 → 169.254.169.254
        # entries using the mapped IPv6 form
        if getattr(ip, "ipv4_mapped", None):
            ip = ip.ipv4_mapped

        # These are the IPv6 equivalent of RFC 1918 private ranges
        # Not in our original blocklist at all
        if isinstance(ip, ipaddress.IPv6Address):
            if ip in ipaddress.ip_network("fc00::/7"):
                return True

        if not ip.is_global:
            return True

        return False

    except ValueError:
        # Unparseable IP string — treat as blocked, not as safe
        return True
    
def resolve_and_check(hostname: str) -> None:
    """
    Resolve hostname to IP addresses and check each one.
    This prevents DNS rebinding attacks where a hostname
    resolves to a private IP after your initial check.
    
    repeat this at  delivery time (TOCTOU FIX)
    """
    
    try:
        results = socket.getaddrinfo(hostname, None)
        for result in results:
            ip_str = result[4][0]
            if is_ip_blocked(ip_str):
                raise WebHookURLError(f"Resolved IP {ip_str} for {hostname} is blocked.")
    except socket.gaierror:
        raise WebHookURLError(f"Unable to resolve hostname: {hostname}")
    
def validate_webhook_url(url: str) -> str:
    """
    Validate a webhook URL for SSRF safety.
 
    Checks performed (in order):
        1. URL is a non-empty string
        2. URL scheme is https only 
        3. URL has a valid hostname
        4. Hostname is not in the blocked hostnames list
        5. If hostname is a raw IP — check against blocked ranges
        6. If hostname is a domain — resolve it and check all IPs
        7. URL has no embedded credentials (user:pass@host)
 
    Args:
        url: The raw webhook URL string from the API request
 
    Returns:
        The validated URL string (normalised)
 
    Raises:
        WebhookURLError: with a human-readable reason if validation fails
        HTTPException 422: wraps WebhookURLError for FastAPI routes
    """
    
    if not url or not url.strip():
        raise WebHookURLError("Webhook URL cannot be empty.")
    
    url = url.strip()
    
    # parsing
    try:
        parsed = urlparse(url)
    except Exception:
        raise WebHookURLError("Invalid URL format.")
    
    # scheme check
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise WebHookURLError(
            f"Webhook URL scheme '{parsed.scheme}' is not allowed. "
            f"Only {', '.join(ALLOWED_SCHEMES)} are accepted." # change later only to https
        ) 
        
    # hostname check
    hostname = parsed.hostname
    if not hostname:
        raise WebHookURLError("Webhook URL must have a valid hostname.")
    
    # embedded credentials check
    if parsed.username or parsed.password:
        raise WebHookURLError(
            "Webhook URL must not contain embedded credentials (user:pass@host)."
        )
        
    # blocked hostname list
    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise WebHookURLError(f"Hostname '{hostname}' is not allowed.")
    
    # IP address check
    try:
        ipaddress.ip_address(hostname)
        if is_ip_blocked(hostname):
            raise WebHookURLError(
                f"Webhook URL points to a blocked IP address: {hostname}"
            )
            
        return url
    except ValueError:
        pass  # Not an IP, treat as domain, fall thru dns resolution
    
    # DNS resolution and IP checks
    resolve_and_check(hostname)
    
    return url

def validate_webhook_url_for_fastapi(url: str) -> str:
    try:
        return validate_webhook_url(url)
    except WebHookURLError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"field": "webhook_url", "error": str(e)}
        )