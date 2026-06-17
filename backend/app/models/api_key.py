import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base

class APIKey(Base):
    __tablename__ = "api_keys"
    
    # primary key with UUID string
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )
    
    # human readable name for the API key
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    
    # actual key value, stored as hash
    # format lh_live_xxxxxxxxxxxxxxxxxxxxxx
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Rate limit tier — controls request limits in rate_limiter.py
    # "free" | "pro" | "enterprise"
    # No billing integration yet — set manually via SQL:
    #   UPDATE api_keys SET tier = 'pro' WHERE id = '...';
    tier: Mapped[str] = mapped_column(
        String(20), default="free", server_default="free", nullable=False
    )
    
    #is_active
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    def __repr__(self) -> str:
        return (
            f"<APIKey {self.key_prefix}... "
            f"name={self.name} tier={self.tier} active={self.is_active}>"
        )