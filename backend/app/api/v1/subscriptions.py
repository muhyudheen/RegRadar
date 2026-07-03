# backend/app/api/v1/subscriptions.py
# ─────────────────────────────────────────────────
#  Subscription Endpoints
#  POST   /v1/subscriptions        → create
#  GET    /v1/subscriptions        → list all for this key
#  GET    /v1/subscriptions/{id}   → get one
#  PATCH  /v1/subscriptions/{id}   → pause / resume
#  DELETE /v1/subscriptions/{id}   → delete
# ─────────────────────────────────────────────────

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from app.core.api_key_utils import generate_subscription_secret
from app.core.database import get_db
from app.core.webhook_validator import validate_webhook_url_for_fastapi
from app.dependencies.auth import get_current_user_flexible
from app.models.api_key import APIKey
from app.models.subscription import Subscription
from app.models.user import User

router = APIRouter()


def _oldest_active_key(db: Session, user_id: str) -> APIKey | None:
    """
    The key a JWT-created subscription is attached to.

    Subscriptions still need an owning key (NOT NULL FK + webhook signing
    identity). When created via a JWT session there is no specific key in
    context, so we attach to the user's oldest active key.
    """
    return (
        db.query(APIKey)
        .filter(APIKey.user_id == user_id, APIKey.is_active == True)  # noqa: E712
        .order_by(APIKey.created_at.asc())
        .first()
    )

# ── Subscription count limits per tier ────────────
#  Mirrors the pricing page. None = unlimited.
#  Free=1, Starter=10, Pro/Enterprise=unlimited.
#  Unknown tiers fall back to the most restrictive (free)
#  so a bad tier value can never grant unlimited subs.
SUBSCRIPTION_LIMITS: dict[str, int | None] = {
    "free": 1,
    "starter": 10,
    "pro": None,
    "enterprise": None,
}
DEFAULT_SUB_LIMIT = SUBSCRIPTION_LIMITS["free"]


def count_active_user_subscriptions(db: Session, user_id: str) -> int:
    """
    Count a USER's active subscriptions pooled across ALL of their keys.

    The tier cap is enforced per user, not per key — this closes the
    multi-key quota exploit (spread subs across keys to exceed the plan).
    """
    return (
        db.query(Subscription)
        .join(APIKey, Subscription.api_key_id == APIKey.id)
        .filter(
            APIKey.user_id == user_id,
            Subscription.is_active == True,  # noqa: E712
        )
        .count()
    )

# ── Request / Response Schemas ────────────────────

class CreateSubscriptionRequest(BaseModel):
    name: str
    jurisdiction: str
    industry: str
    topics: list[str] | None = None
    webhook_url: str
    severity_min: str = 'minor'
    
    @field_validator('webhook_url')
    @classmethod
    def check_webhook_url(cls, v: str) -> str:
        return validate_webhook_url_for_fastapi(v)
    
    @field_validator('severity_min')
    @classmethod
    def check_severity(cls, v: str) -> str:
        allowed = {'minor', 'major', 'critical'}
        if v not in allowed:
            raise ValueError(f"severity_min must be one of: {', '.join(allowed)}")
        return v
    
    @field_validator('jurisdiction')
    @classmethod
    def check_jurisdiction(cls, v: str) -> str:
        if len(v) > 10:
            raise ValueError("jurisdiction must be a valid ISO code e.g. IN, US, EU")
        return v.upper().strip()
    
    @field_validator('industry')
    @classmethod
    def check_industry(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("industry cannot be empty")
        return v.lower().strip()
    
class PatchSubscriptionRequest(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    webhook_url: str | None = None
    severity_min: str | None = None
    
    @field_validator('webhook_url')
    @classmethod
    def check_webhook_url(cls, v: str | None) -> str | None:
        if v is not None:
            return validate_webhook_url_for_fastapi(v)
        return v
    
    
class SubscriptionResponse(BaseModel):
    id: str
    name: str
    jurisdiction: str
    industry: str
    topics: list[str] | None
    webhook_url: str
    severity_min: str
    is_active: bool
    # signing_secret shown ONCE on create only
    # not included in this base response
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        
class CreateSubscriptionResponse(SubscriptionResponse):
    signing_secret: str  # shown ONCE at creation only must store this
    
# ── Endpoint Implementations ─────────────────────

@router.post(
    "",
    response_model=CreateSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subscription",
    description=(
        "Creates a new webhook subscription. "
        "The **signing_secret** is returned once only — store it immediately. "
        "Use it to verify incoming webhooks are genuinely from Lawhook."
    ),
)
def create_subscription(
    request: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    # ── Enforce per-tier subscription cap (per USER, pooled) ──
    # Tier is inherited from the user; unknown tier → most restrictive
    # (free) limit, fail-safe.
    tier = current_user.tier
    limit = SUBSCRIPTION_LIMITS.get(tier, DEFAULT_SUB_LIMIT)

    if limit is not None:
        current_count = count_active_user_subscriptions(db, current_user.id)

        if current_count >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Subscription limit reached for the '{tier}' tier "
                    f"({limit} active). Upgrade your plan or pause/delete an "
                    f"existing subscription to add a new one."
                ),
            )

    # Subscriptions need an owning key. Use the one in context if this was an
    # API-key call; otherwise (JWT) attach to the user's oldest active key.
    owning_key = _oldest_active_key(db, current_user.id)
    if owning_key is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Create an API key first — subscriptions are attached to a key.",
        )

    subscription = Subscription(
        id=str(uuid.uuid4()),
        api_key_id=owning_key.id,
        name=request.name.strip(),
        jurisdiction=request.jurisdiction,
        industry=request.industry,
        topics=request.topics,
        webhook_url=request.webhook_url,
        severity_min=request.severity_min,
        signing_secret=generate_subscription_secret(),
        is_active=True,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)    
    return subscription

@router.get(
        "",
    response_model=list[SubscriptionResponse],
    summary="List all subscriptions",
)
def list_subscriptions(
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    """
    Returns all subscriptions belonging to the user (pooled across all
    their keys). Signing secrets are never returned in list responses.
    """
    return (
        db.query(Subscription)
        .join(APIKey, Subscription.api_key_id == APIKey.id)
        .filter(APIKey.user_id == current_user.id)
        .all()
    )

@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get subscription details",
)
def get_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    sub = _get_owned_subscription(subscription_id, current_user.id, db)
    return sub

@router.patch(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Update a subscription",
    description="Update webhook URL, severity level, topics, or pause/resume.",
)
def update_subscription(
    subscription_id: str,
    request: PatchSubscriptionRequest,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db)
):
    sub = _get_owned_subscription(subscription_id, current_user.id, db)

    if request.is_active is not None:
        # Re-activating a paused subscription must respect the tier cap,
        # otherwise a user could bypass the create-time limit by pausing
        # then resuming to accumulate active subs beyond their plan.
        if request.is_active and not sub.is_active:
            tier = current_user.tier
            limit = SUBSCRIPTION_LIMITS.get(tier, DEFAULT_SUB_LIMIT)
            if limit is not None:
                active_count = count_active_user_subscriptions(db, current_user.id)
                if active_count >= limit:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=(
                            f"Cannot resume: '{tier}' tier allows "
                            f"{limit} active subscription(s). Pause or delete "
                            f"another first."
                        ),
                    )
        sub.is_active = request.is_active
    if request.webhook_url is not None:
        sub.webhook_url = request.webhook_url
    if request.severity_min is not None:
        if request.severity_min not in {"minor", "major", "critical"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="severity_min must be minor, major, or critical",
            )
        sub.severity_min = request.severity_min
    if request.name is not None:
        if not request.name.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Name cannot be empty."
            )
        sub.name = request.name.strip()
        
    db.commit()
    db.refresh(sub)
    return sub

@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a subscription",
)
def delete_subscription(
    subscription_id: str,
    current_user: User = Depends(get_current_user_flexible),
    db: Session = Depends(get_db),
):
    sub = _get_owned_subscription(subscription_id, current_user.id, db)
    db.delete(sub)
    db.commit()


# ── Helper Functions ─────────────────────────────
def _get_owned_subscription(
    subscription_id: str,
    user_id: str,
    db: Session
) -> Subscription:
    """
    Fetch a subscription by ID and verify it belongs to the requesting
    USER (via the owning key). Raises 404 if not found or owned by
    someone else.

    Always returns 404 (never 403) to avoid revealing that a
    subscription exists but belongs to another user.
    """
    sub = (
        db.query(Subscription)
        .join(APIKey, Subscription.api_key_id == APIKey.id)
        .filter(
            Subscription.id == subscription_id,
            APIKey.user_id == user_id,
        )
        .first()
    )

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )
    return sub