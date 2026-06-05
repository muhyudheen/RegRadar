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
    # format rr_live_xxxxxxxxxxxxxxxxxxxxxx
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    
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
        return f"<ApiKey {self.key_prefix}... name={self.name} active={self.is_active}>"