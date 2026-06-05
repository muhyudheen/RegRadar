# backend/app/api/v1/auth.py
# ─────────────────────────────────────────────────
#  Auth Endpoints
#  POST /v1/auth/keys  → generate a new API key
#  GET  /v1/auth/keys  → list all keys (authenticated)
#  DELETE /v1/auth/keys/{key_id} → revoke a key
# ─────────────────────────────────────────────────

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session  
from pydantic import BaseModel

from app.core.api_key_utils import generate_api_key
from app.core.database import get_db
from app.dependencies.auth import get_current_api_key
from app.models.api_key import APIKey

router = APIRouter()

# ── Request / Response Schemas ────────────────────

class CreateApiKeyRequest(BaseModel):
    name: str
    
class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None

    class Config:
        from_attributes = True    
        
class CreateApiKeyResponse(BaseModel):
    id: str
    name: str
    key: str          # Full key — shown ONCE, never again
    key_prefix: str
    created_at: datetime

    class Config:
        from_attributes = True
        
# ── Endpoints ─────────────────────────────────────

@router.post(
    "/keys",
    response_model=CreateApiKeyResponse,
    status_code = status.HTTP_201_CREATED,
    summary='Generates a new API Key',
    description=(
            "Creates a new API key. The full key is returned **once only** — "
            "store it immediately. It cannot be retrieved again."
    ),
)
def create_api_key(
    request: CreateApiKeyRequest,
    db: Session = Depends(get_db),
):
    """
    Generate a new CSPRNG API key.

    The full key is returned in this response only.
    After this, only the prefix is shown in the dashboard.
    """
    
    if not request.name or not request.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Key name cannot be empty."
        )
        
    full_key, key_hash, key_prefix = generate_api_key()
    
    api_key = APIKey(
        id=str(uuid.uuid4()),
        name=request.name.strip(),
        key_hash=key_hash, # never store full_key
        key_prefix=key_prefix,
        is_active=True,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return CreateApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=full_key, # show full key ONCE
        key_prefix=key_prefix,
        created_at=api_key.created_at,
    )
    
@router.get(
    "/keys",
    response_model = list[ApiKeyResponse],
    summary = "Lists all API Keys",
)
def list_api_keys(
    api_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db),
):
    """
    List all active API keys.
    Requires authentication — pass any valid key.
    Full key values are never returned.
    """
    
    keys = db.query(APIKey).filter(
        APIKey.is_active == True
    ).all()
    return keys

@router.delete(
    "/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revokes an API Key",
)
def revoke_api_key(
    key_id: str,
    api_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db),
):
    """
    Revoke an API key. This cannot be undone.
    The key is marked inactive — not deleted from the database.
    """
    target = db.query(APIKey).filter(APIKey.id == key_id).first()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    target.is_active = False
    target.revoked_at = datetime.now(timezone.utc)
    db.commit()
    
    