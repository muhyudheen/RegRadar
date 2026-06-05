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
from app.dependencies.auth import get_current_api_key
from app.models.api_key import APIKey
from app.models.subscription import Subscription

router = APIRouter()

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
        "Use it to verify incoming webhooks are genuinely from RegRadar."
    ),
)
def create_subscription(
    request: CreateSubscriptionRequest,
    api_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db)
):
    subscription = Subscription(
        id=str(uuid.uuid4()),
        api_key_id=api_key.id,
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
    api_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db),
):
    """
    Returns all subscriptions belonging to this API key.
    Signing secrets are never returned in list responses.
    """
    return db.query(Subscription).filter(
        Subscription.api_key_id == api_key.id
    ).all()
    
@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Get subscription details",
)
def get_subscription(
    subscription_id: str,
    api_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db),
):
    sub = _get_owned_subscription(subscription_id, api_key.id, db)
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
    api_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db)
):
    sub = _get_owned_subscription(subscription_id, api_key.id, db)
    
    if request.is_active is not None:
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
    api_key: APIKey = Depends(get_current_api_key),
    db: Session = Depends(get_db),
):
    sub = _get_owned_subscription(subscription_id, api_key.id, db)
    db.delete(sub)
    db.commit()
    
    
# ── Helper Functions ─────────────────────────────
def _get_owned_subscription(
    subscription_id: str,
    api_key_id: str,
    db: Session
) -> Subscription:
    """
    Fetch a subscription by ID and verify it belongs
    to the requesting API key. Raises 404 if not found
    or if it belongs to a different key.

    Always returns 404 (never 403) to avoid revealing
    that a subscription exists but belongs to someone else.
    """
    sub = db.query(Subscription).filter(
        Subscription.id == subscription_id,
        Subscription.api_key_id == api_key_id,
    ).first()

    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subscription not found.",
        )
    return sub

    