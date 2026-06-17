# backend/app/core/webhook_signing.py
# ─────────────────────────────────────────────────
#  Webhook Authentication — Signing & Verification
#
#  Two responsibilities:
#
#  1. OUTBOUND (Lawhook → Developer)
#     Lawhook signs every outgoing webhook payload
#     with HMAC-SHA256 using WEBHOOK_SIGNING_SECRET.
#     The signature is sent in X-Lawhook-Signature header.
#
#  2. INBOUND verification helper (for SDK / docs)
#     Developers use verify_webhook_signature() in their
#     own servers to confirm the webhook came from Lawhook.
#     We include this so we can document it clearly.
#
#  This file is used by:
#    - app/workers/webhook.py     → signs before every delivery
#    - app/api/v1/subscriptions.py → includes signature in payload docs
# ─────────────────────────────────────────────────

import hashlib
import hmac
import json
import os
import time
from typing import Any

# Configuration

SIGNATURE_HEADER = "X-Lawhook-Signature"

TIMESTAMP_HEADER = "X-Lawhook-Timestamp"

TIMESTAMP_TOLERANCE_SECONDS = 300 # 5 minutes

class WebhookSigningError(Exception):
    pass

# ══════════════════════════════════════════════════
#  OUTBOUND — Lawhook signs the payload
# ══════════════════════════════════════════════════

def sign_webhook_payload(payload: dict[str, Any], secret: str | None = None) -> tuple[str, str, str]:
    """
    Sign an outgoing webhook payload with HMAC-SHA256.
 
    The signature is computed over:
        timestamp + "." + json_body
    Including the timestamp prevents replay attacks —
    an old captured webhook can't be replayed later.
 
    Args:
        payload: the webhook payload dict to sign
 
    Returns:
        tuple of (json_body, signature, timestamp)
        - json_body:  serialised JSON string to send as request body
        - signature:  "sha256=<hex_digest>" to send in header
        - timestamp:  Unix timestamp string to send in header
 
    Raises:
        WebhookSigningError: if WEBHOOK_SIGNING_SECRET is not set
 
    Usage in webhook worker:
        json_body, signature, timestamp = sign_webhook_payload(payload)
 
        headers = {
            SIGNATURE_HEADER:  signature,
            TIMESTAMP_HEADER:  timestamp,
            "Content-Type":    "application/json",
        }
        response = httpx.post(webhook_url, content=json_body, headers=headers)
    """
    
    

    if not secret:
        raise WebhookSigningError(
            "Webhook signing secret is missing for this delivery. "
            "This indicates an internal configuration error — "
            "check that the subscription has a valid signing_secret."
        )
    signing_secret = secret
        
    json_body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    
    timestamp = str(int(time.time()))
    
    signed_string = f"{timestamp}.{json_body}"
    
    signature_hex = hmac.new(
        signing_secret.encode('utf-8'),
        signed_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    signature = f"sha256={signature_hex}"
    
    return json_body, signature, timestamp

# ══════════════════════════════════════════════════
#  INBOUND — Developer verifies the signature
#  (used in our SDK and documentation)
# ══════════════════════════════════════════════════

def verify_webhook_signature(
    payload_body: bytes | str,
    signature_header: str,
    timestamp_header: str,
    secret: str,
    tolerance_seconds: int = TIMESTAMP_TOLERANCE_SECONDS
) -> bool:
    
    # ── 1. Validate timestamp format ─────────────
    
    try:
        webhook_timestamp = int(timestamp_header)
    except (ValueError, TypeError):
        return False
    
    # ── 2. Reject stale webhooks (replay attack protection) ──

    age_seconds = int(time.time()) - webhook_timestamp
    # Reject if too old (replay attack)
# Allow up to 30s future skew (clock sync tolerance)
    if age_seconds > tolerance_seconds or age_seconds < -30:
        return False
    
    # ── 3. Normalise payload to string ───────────
    if isinstance(payload_body, bytes):
        body_str = payload_body.decode('utf-8')
    else:
        body_str = payload_body
        
    # ── 4. Rebuild the signed string ─────────────
    signed_string = f"{timestamp_header}.{body_str}"
    
    # ── 5. Recompute expected signature ──────────
    
    expected_hex = hmac.new(
        secret.encode('utf-8'),
        signed_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    expected_signature = f"sha256={expected_hex}"
    
    # ── 6. Compare signatures securely ───────────
    return hmac.compare_digest(
        signature_header.encode('utf-8'),
        expected_signature.encode('utf-8')
    )
    