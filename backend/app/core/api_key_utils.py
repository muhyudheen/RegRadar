#  API Key generation and verification utilities
#
#  Key format:  lh_live_<40 random hex chars>
#  Example:     lh_live_a3f8c2d1e9b4f7a2c8d3e1f0b5a9c2d4e7f1a3b8

import secrets 
import hashlib

KEY_PREFIX = "lh_live_"
KEY_RANDOM_BITS = 40
PREFIX_SHOWN_LENGTH = 14

def generate_api_key():
    """
    Generate a new CSPRNG API key.
    
    full_key   — shown to the developer ONCE at creation, never stored
        key_hash   — SHA-256 hash stored in DB, used for verification
        key_prefix — first 14 chars stored in DB, shown in dashboard
    """
    
    random_part = secrets.token_hex(20) # 20 bytes = 40 hex chars
    
    full_key = KEY_PREFIX + random_part
    
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    key_prefix = full_key[:PREFIX_SHOWN_LENGTH] #hash for storage and prefix for display
    
    return full_key, key_hash, key_prefix

def hash_api_key(full_key: str) -> str:
    """
    Hash an incoming API key for database lookup.
 
    Called on every authenticated request:
        1. Developer sends key in Authorization header
        2. hash here
        3. look up for the hash in the database
        4. found and is_active=True → request is authenticated
 
    Args:
        full_key: the raw key string from the request header
 
    Returns:
        SHA-256 hex digest of the key
    """
    
    return hashlib.sha256(full_key.encode()).hexdigest()

def verify_api_key(full_key: str, stored_hash: str) -> bool:
    """
    using secrets.compare_digest()"""
    
    computed_hash = hash_api_key(full_key)
    return secrets.compare_digest(computed_hash, stored_hash)

def extract_key_from_header(authorization: str) -> str | None:
    """
    Extract the API key from the Authorization header.
    
    Expected format: "Bearer <API_KEY>
    """
    
    if not authorization:
        return None
    
    parts = authorization.strip().split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None 
    return parts[1]

# ── Webhook signing secret generation ────────────
WEBHOOK_SECRET_PREFIX = "whsec_"
WEBHOOK_SECRET_BYTES  = 20   # 40 hex chars = 160 bits entropy


def generate_subscription_secret() -> str:
    """
    Generate a per-subscription webhook signing secret.

    Format: whsec_<40 random hex chars>
    Example: whsec_a3f8c2d1e9b4f7a2c8d3e1f0b5a9c2d4e7f1a3b8

    Called once at subscription creation.
    Stored in subscriptions.signing_secret.
    Shown to developer once in dashboard.
    Used to sign all webhooks for this subscription.
    """
    return f"{WEBHOOK_SECRET_PREFIX}{secrets.token_hex(WEBHOOK_SECRET_BYTES)}"
    