# ─────────────────────────────────────────────────
#  User model
#
#  A human account. Owns one or more API keys.
#  TIER lives here now (moved off api_keys) — every key
#  inherits its owner's tier, and all limits (rate +
#  subscription cap) are resolved + pooled per user.
# ─────────────────────────────────────────────────

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class User(Base):
    __tablename__ = "users"

    # primary key — UUID string
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # login identity — unique + indexed
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )

    # bcrypt hash — never store plaintext
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # Billing/limits tier — MOVED here from api_keys.
    #   "free" | "starter" | "pro" | "enterprise"
    # No billing integration yet — set manually via SQL:
    #   UPDATE users SET tier = 'pro' WHERE id = '...';
    tier: Mapped[str] = mapped_column(
        String(20), default="free", server_default="free", nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # A user owns many keys; deleting a user cascades to their keys.
    api_keys = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<User {self.email} tier={self.tier} active={self.is_active}>"
