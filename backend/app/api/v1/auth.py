# backend/app/api/v1/auth.py
# ─────────────────────────────────────────────────
#  Auth Endpoints
#  POST /v1/auth/keys  → generate a new API key
#  GET  /v1/auth/keys  → list all keys (authenticated)
#  DELETE /v1/auth/keys/{key_id} → revoke a key
# ─────────────────────────────────────────────────

import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, field_validator

from app.core.api_key_utils import generate_api_key
from app.core.auth_utils import create_access_token, hash_password, verify_password
from app.core.database import get_db
from app.dependencies.auth import get_current_api_key, get_current_user
from app.models.api_key import APIKey
from app.models.user import User
from app.api.v1.subscriptions import (
    SUBSCRIPTION_LIMITS,
    DEFAULT_SUB_LIMIT,
    count_active_user_subscriptions,
)

router = APIRouter()

# Lightweight email format check (avoids pulling in the email-validator dep).
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD_LENGTH = 8

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


# ── User auth (JWT) schemas ───────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def check_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Enter a valid email address.")
        return v

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        if len(v) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
            )
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UserPublic(BaseModel):
    id: str
    email: str
    tier: str

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserPublic


# ── User auth (JWT) endpoints ─────────────────────

@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account",
    description="Register with email + password. Returns a JWT session token.",
)
def signup(request: SignupRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == request.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    user = User(
        id=str(uuid.uuid4()),
        email=request.email,
        password_hash=hash_password(request.password),
        tier="free",
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=user)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in",
    description="Exchange email + password for a JWT session token.",
)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    # Generic 401 on any failure — never reveal whether the email exists
    # or which field was wrong.
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password.",
    )

    user = db.query(User).filter(User.email == request.email.strip().lower()).first()
    if not user or not user.is_active:
        raise invalid
    if not verify_password(request.password, user.password_hash):
        raise invalid

    token = create_access_token(user.id)
    return AuthResponse(access_token=token, user=user)


# ── API key endpoints ─────────────────────────────

@router.post(
    "/keys",
    response_model=CreateApiKeyResponse,
    status_code = status.HTTP_201_CREATED,
    summary='Generates a new API Key',
    description=(
            "Creates a new API key owned by the logged-in user. The full key is "
            "returned **once only** — store it immediately. It cannot be "
            "retrieved again."
    ),
)
def create_api_key(
    request: CreateApiKeyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a new CSPRNG API key for the authenticated USER.

    Requires a JWT session (dashboard auth). The key inherits the
    user's tier. The full key is returned in this response only.
    """

    if not request.name or not request.name.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Key name cannot be empty."
        )

    full_key, key_hash, key_prefix = generate_api_key()

    api_key = APIKey(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
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
    summary = "Lists your API Keys",
)
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List the active API keys belonging to the logged-in user.
    Scoped to current_user — never returns other users' keys.
    Full key values are never returned.
    """
    keys = db.query(APIKey).filter(
        APIKey.user_id == current_user.id,
        APIKey.is_active == True,  # noqa: E712
    ).all()
    return keys

@router.delete(
    "/keys/{key_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revokes an API Key",
)
def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Revoke one of the logged-in user's own API keys. Cannot be undone.
    The key is marked inactive — not deleted from the database.

    Scoped to current_user: a 404 is returned for keys that don't exist
    OR belong to another user (never reveals existence).
    """
    target = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == current_user.id,
    ).first()

    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    target.is_active = False
    target.revoked_at = datetime.now(timezone.utc)
    db.commit()
    

class MeResponse(BaseModel):
    id: str
    email: str
    tier: str
    subscription_count: int
    subscription_limit: int | None
    created_at: datetime

    class Config:
        from_attributes = True


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user identity + usage",
    description=(
        "Returns the logged-in user's identity, tier, and how many active "
        "subscriptions they have (pooled across all their keys) against the "
        "tier cap. `subscription_limit` is null for unlimited tiers."
    ),
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Identity + usage for the authenticated USER (JWT/dashboard auth).
    Powers the dashboard tier badge and the 'N of cap used' meter.
    Subscription count is pooled across every key the user owns.
    """
    active_count = count_active_user_subscriptions(db, current_user.id)
    limit = SUBSCRIPTION_LIMITS.get(current_user.tier, DEFAULT_SUB_LIMIT)

    return MeResponse(
        id=current_user.id,
        email=current_user.email,
        tier=current_user.tier,
        subscription_count=active_count,
        subscription_limit=limit,
        created_at=current_user.created_at,
    )