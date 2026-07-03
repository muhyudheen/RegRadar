# ─────────────────────────────────────────────────
#  Auth utilities — password hashing + JWT sessions
#
#  Password hashing: bcrypt via passlib. Plaintext is
#  never stored or logged.
#
#  Sessions: short-lived signed JWTs (HS256). The token
#  subject (`sub`) is the user id. Used by human/dashboard
#  callers via `Authorization: Bearer <jwt>`.
#
#  This is DIFFERENT from the lh_live_ API key auth used by
#  machine callers — see dependencies/auth.py.
#
#  SECRET: JWT_SECRET_KEY must be set in the environment.
#  We fail loudly if it is missing — never sign with a
#  default/guessable key.
# ─────────────────────────────────────────────────

import base64
import hashlib
import os
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "7"))


def _prepare_password(password: str) -> bytes:
    """
    Normalise a password for bcrypt.

    bcrypt only considers the first 72 bytes and the 4.x backend RAISES
    on longer inputs. Pre-hashing to a fixed 44-byte base64 token lets
    passwords of any length be used at full strength without ever
    hitting the 72-byte limit.

    NOTE: we call the bcrypt library directly rather than through
    passlib — passlib 1.7.4's backend probe is itself incompatible with
    bcrypt 4.x (it feeds bcrypt a 72-byte secret and crashes).
    """
    digest = hashlib.sha256(password.encode("utf-8")).digest()
    return base64.b64encode(digest)


def _secret_key() -> str:
    """
    Read the JWT signing secret from the environment.

    Fails loudly if unset — we must never fall back to a
    hardcoded/guessable key, which would let anyone forge
    a session for any user.
    """
    key = os.getenv("JWT_SECRET_KEY")
    if not key or not key.strip():
        raise RuntimeError(
            "JWT_SECRET_KEY is not set. Refusing to sign/verify tokens with a "
            "default key. Set JWT_SECRET_KEY in your environment / .env."
        )
    return key


# ── Passwords ─────────────────────────────────────

def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt (over a SHA-256 pre-hash)."""
    hashed = bcrypt.hashpw(_prepare_password(password), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verify of a plaintext password against a stored hash."""
    try:
        return bcrypt.checkpw(
            _prepare_password(password),
            password_hash.encode("utf-8"),
        )
    except Exception:
        # Malformed hash or backend error → treat as a failed login,
        # never raise into the request flow.
        return False


# ── JWT access tokens ─────────────────────────────

def create_access_token(user_id: str, expires_days: int | None = None) -> str:
    """
    Mint a signed JWT for the given user id (used as `sub`).
    Expiry defaults to ACCESS_TOKEN_EXPIRE_DAYS (7 days).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(days=expires_days or ACCESS_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, _secret_key(), algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> str | None:
    """
    Validate a JWT and return its subject (user id), or None if the
    token is invalid/expired/tampered.
    """
    try:
        payload = jwt.decode(token, _secret_key(), algorithms=[JWT_ALGORITHM])
    except JWTError:
        return None
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        return None
    return sub
