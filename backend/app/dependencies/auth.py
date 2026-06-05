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
from app.models.api_key import APIKey
from app.core.database import get_db

bearer_scheme = HTTPBearer(auto_error=False)

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
    
    from datetime import datetime, timezone
    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()
    
    return api_key