#  Subscription model
#  Stores what a developer is monitoring —
#  which jurisdiction + industry + topics
#  and where to send webhook notifications

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func, Boolean, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
from sqlalchemy.dialects.postgresql import ARRAY


class Subscription(Base):
    __tablename__ = "subscriptions"
    
    # primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # Foreign key → api_keys table
    # Every subscription belongs to one API key
    api_key_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("api_keys.id"),
        nullable=False,
        index=True
    )
    
    # Human readable name for the subscription
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    # ISO 3166-1 alpha-2 country code — e.g. "IN", "US", "GB"
    # Or region code — e.g. "EU"
    jurisdiction: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        index=True
    )
    
    # industry vertical eg: 'fintech', 'healthcare', 'gaming'
    industry: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    
    # Optional list of specific topics within the industry
    # e.g. ["KYC", "AML", "payment_systems"]
    # Stored as a PostgreSQL text array
    topics: Mapped[list[str] | None] = mapped_column(ARRAY(Text), nullable=True)
    
    # URL where webhook payloads are sent when a change is detected
    webhook_url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # Per-subscription webhook signing secret
    # Generated with CSPRNG at subscription creation
    # Format: whsec_<40 random hex chars>
    # Shown to developer ONCE in dashboard — never again
    # Used to sign outbound webhooks for this subscription only
    signing_secret: Mapped[str] = mapped_column(
        String(60), nullable=False, unique=True
    )
    
    # Minimum severity level to trigger a webhook
    # "minor" = all changes, "major" = major+critical, "critical" = critical only
    severity_min: Mapped[str] = mapped_column(
        String(20), nullable=False, default="minor"
    )
    
    # Is this subscription active?
    # Developers can pause/resume without deleting
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
 
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(),
        onupdate=func.now(), nullable=False
    )
 
    # Relationships
    api_key = relationship("APIKey", backref="subscriptions")
 
    def __repr__(self) -> str:
        return (
            f"<Subscription {self.id[:8]} "
            f"jurisdiction={self.jurisdiction} "
            f"industry={self.industry} "
            f"active={self.is_active}>"
        )
 