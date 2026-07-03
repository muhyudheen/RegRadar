# ─────────────────────────────────────────────────
#  Change Feed Endpoints
#
#  GET /v1/changes         — paginated change feed
#  GET /v1/changes/{id}    — single change detail
#  GET /v1/search          — full-text search
#
#  All endpoints require API key auth.
#  Only returns changes with status="ready" by default.
#  Filters by the API key's subscriptions — a developer
#  can only see changes matching their own subscriptions.
# ─────────────────────────────────────────────────

from datetime import datetime
from typing import Any
 
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import or_
from sqlalchemy.orm import Session
 
from app.core.database import get_db
from app.dependencies.auth import get_current_user_flexible
from app.models.api_key import APIKey
from app.models.change import Change
from app.models.subscription import Subscription
from app.models.user import User
 
router = APIRouter()


# ───────────────Response Scehmas──────────────────────

class ChangeResponse(BaseModel):
    id:               str
    jurisdiction:     str
    industry:         str
    topic:            str | None
    source_authority: str
    source_url:       str
    summary:          str | None
    severity:         str | None
    diff:             dict | None
    status:           str
    effective_date:   Any | None
    detected_at:      datetime
    processed_at:     datetime | None
 
    class Config:
        from_attributes = True
        
        
class PaginatedChangesResponse(BaseModel):
    items:   list[ChangeResponse]
    total:   int
    page:    int
    limit:   int
    has_more: bool
    
# ─────────────── Helper Functions ───────────────────────

def _get_subscribed_pairs(
    user: User,
    db: Session,
) -> list[tuple[str, str]]:
    """
    Returns the list of (jurisdiction, industry) pairs the USER is
    subscribed to, pooled across all of their keys. A user only sees
    changes matching their own subscriptions.
    """
    subs = (
        db.query(Subscription)
        .join(APIKey, Subscription.api_key_id == APIKey.id)
        .filter(
            APIKey.user_id == user.id,
            Subscription.is_active == True,  # noqa: E712
        )
        .all()
    )
    return [(sub.jurisdiction, sub.industry) for sub in subs]

def base_changes_query(
    db: Session,
    pairs: list[tuple[str, str]],
):
    """Base query — only ready changes, only subscribed pairs."""
    if  not pairs:
        return db.query(Change).filter(False)  # No subscriptions, return empty query
    
    filters = [
        (Change.jurisdiction == j) & (Change.industry == i)
        for j, i in pairs
    ]
    
    return db.query(Change).filter(
        Change.status == "ready",
        or_(*filters)
    )
    
    
# ─────────────── Endpoints ───────────────────────

@router.get(
    "",
    response_model=PaginatedChangesResponse,
    summary="List Changes",
    description=(
        "Returns a paginated feed of ready regulatory changes "
        "matching your active subscriptions."
    )
)
def list_changes(
    page:         int    = Query(default=1, ge=1, description="Page number"),
    limit:        int    = Query(default=20, ge=1, le=100, description="Results per page"),
    jurisdiction: str    | None = Query(default=None, description="Filter by jurisdiction e.g. IN"),
    industry:     str    | None = Query(default=None, description="Filter by industry e.g. fintech"),
    severity:     str    | None = Query(default=None, description="Filter by severity: critical, major, minor"),
    current_user: User   = Depends(get_current_user_flexible),
    db: Session          = Depends(get_db),
):
    pairs = _get_subscribed_pairs(current_user, db)
    query = base_changes_query(db, pairs)

    if jurisdiction:
        query = query.filter(Change.jurisdiction == jurisdiction.upper().strip())
    if industry:
        query = query.filter(Change.industry == industry.lower().strip())
    if severity:
        if severity not in ("critical", "major", "minor"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="severity must be critical, major, or minor",
            )
        query = query.filter(Change.severity == severity)
        
    total = query.count()
    
    offset = (page - 1) * limit
    items = query.order_by(Change.detected_at.desc()).offset(offset).limit(limit).all()
    
    return PaginatedChangesResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        has_more=(offset + len(items)) < total,
    )
    
@router.get(
    "/search",
    response_model=PaginatedChangesResponse,
    summary="Search Changes",
    description=(
        "Full-text search across change summaries and source authority names. "
        "Only searches within your active subscriptions."
    )
)
def search_changes(
    q:      str  = Query(..., min_length=2, max_length=200, description="Search query"),
    page:   int  = Query(default=1, ge=1),
    limit:  int  = Query(default=20, ge=1, le=100),
    current_user: User  = Depends(get_current_user_flexible),
    db: Session      = Depends(get_db),
):
    pairs = _get_subscribed_pairs(current_user, db)
    query = base_changes_query(db, pairs)

    search_term = f"%{q.strip()}%"
    query = query.filter(
        or_(
            Change.summary.ilike(search_term),
            Change.source_authority.ilike(search_term),
            Change.topic.ilike(search_term),
        )
    )
    
    total = query.count()
    offset = (page - 1) * limit
    items = query.order_by(Change.detected_at.desc()).offset(offset).limit(limit).all()
    
    return PaginatedChangesResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        has_more=(offset + len(items)) < total,
    )
    
@router.get(
    "/{change_id}",
    response_model=ChangeResponse,
    summary="Get Change Detail",
    description=(
        "Returns detailed information about a specific change by ID. "
        "You can only access changes that match your active subscriptions."
    )
)
def get_change(
    change_id: str,
    current_user: User  = Depends(get_current_user_flexible),
    db: Session      = Depends(get_db),
):
    """
    Returns full detail for a single change including
    AI-generated summary, severity, and structured diff.

    Returns 404 if the change does not exist or does not
    match any of the user's active subscriptions — never reveals
    whether a change exists for a different user.
    """
    pairs = _get_subscribed_pairs(current_user, db)
    
    if not pairs:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change not found",
        )
        
    filters = [
        (Change.jurisdiction == j) & (Change.industry == i)
        for j, i in pairs
    ]
    
    
    change = db.query(Change).filter(
        Change.id == change_id,
        Change.status == "ready",
        or_(*filters)
    ).first()
    
    if not change:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Change not found",
        )
        
    return change