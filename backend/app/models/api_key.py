import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class APIKey(Base):
    __tablename__ = "api_keys"

    # primary key with UUID string
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4())
    )

    # Owning user — keys belong to a user; tier is inherited from the user.
    # ON DELETE CASCADE: deleting a user removes their keys.
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # human readable name for the API key
    name: Mapped[str] = mapped_column(String(150), nullable=False)

    # actual key value, stored as hash
    # format lh_live_xxxxxxxxxxxxxxxxxxxxxx
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)

    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)

    # NOTE: tier moved to the User model. A key's effective tier is
    # always self.user.tier — read that, never a per-key column.

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

    # Owner — exposes the inherited tier via self.user.tier
    user = relationship("User", back_populates="api_keys")

    def __repr__(self) -> str:
        return (
            f"<APIKey {self.key_prefix}... "
            f"name={self.name} user_id={self.user_id} active={self.is_active}>"
        )