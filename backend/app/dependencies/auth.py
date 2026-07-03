# backend/app/dependencies/auth.py
# ─────────────────────────────────────────────────
#  Auth Dependency
#  Called on every protected endpoint.
#  Reads API key from Authorization header,
#  validates it against the database,
#  returns the ApiKey model instance.
#
#  Usage in any endpoint:
#    from app.dependencies.auth import get_current_api_key
#
#    @router.get("/subscriptions")
#    def list_subscriptions(
#        api_key: ApiKey = Depends(get_current_api_key),
#        db: Session = Depends(get_db),
#    ):
#        ...
# ─────────────────────────────────────────────────

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.api_key_utils import hash_api_key
from app.core.auth_utils import decode_access_token
from app.models.api_key import APIKey
from app.models.user import User
from app.core.database import get_db

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency for HUMAN / dashboard callers.

    Validates a JWT session token from `Authorization: Bearer <jwt>`,
    loads the User, and ensures the account is active.

    This is the management-plane auth (signup, API keys, identity).
    Machine API callers use get_current_api_key instead.
    """
    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise auth_error

    token = credentials.credentials
    if not token or not token.strip():
        raise auth_error

    user_id = decode_access_token(token)
    if not user_id:
        raise auth_error

    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise auth_error

    return user

def get_current_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: Session = Depends(get_db)
) -> APIKey:
    """
    FastAPI dependency — validates the API key on every request.

    Flow:
        1. Read Bearer token from Authorization header
        2. Hash it
        3. Look up hash in database
        4. Check key is active (not revoked)
        5. Return ApiKey model — available in route as api_key

    Raises HTTP 401 for any failure — missing, invalid, or revoked.
    Always returns the same generic message to prevent
    key existence enumeration.
    """
    
    auth_error = HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail = "Invalid or missing API key.",
        headers = {"WWW-Authenticate": "Bearer"}
    )
    
    if not credentials:
        raise auth_error
    
    raw_key = credentials.credentials
    
    if not raw_key or not raw_key.strip():
        raise auth_error
    
    key_hash = hash_api_key(raw_key)
    
    api_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash
    ).first()
    
    if not api_key:
        raise auth_error

    if not api_key.is_active:
        raise auth_error

    # The owning user must exist and be active — a deactivated account's
    # keys stop working. Tier is read downstream via api_key.user.tier.
    if not api_key.user or not api_key.user.is_active:
        raise auth_error

    from datetime import datetime, timezone
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    return api_key


def get_current_user_flexible(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Accept EITHER auth method and resolve the USER either way:

      • a JWT session token (humans / dashboard)         → the token's user
      • an lh_live_ API key  (customer machines)          → key.user

    JWT is tried first; an API key isn't a valid JWT so it falls through
    to the key path. Used by the product endpoints (/subscriptions,
    /changes) so both the dashboard and customer machines can call them.

    Still 401s if neither a valid JWT nor a valid, active API key (owned
    by an active user) is presented — security is not weakened.
    """
    from datetime import datetime, timezone

    auth_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise auth_error

    token = credentials.credentials
    if not token or not token.strip():
        raise auth_error

    # 1) JWT session token?
    user_id = decode_access_token(token)
    if user_id:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.is_active:
            raise auth_error
        return user

    # 2) API key fallback.
    key_hash = hash_api_key(token)
    api_key = db.query(APIKey).filter(APIKey.key_hash == key_hash).first()
    if (
        not api_key
        or not api_key.is_active
        or not api_key.user
        or not api_key.user.is_active
    ):
        raise auth_error

    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    return api_key.user