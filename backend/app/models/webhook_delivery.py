# ─────────────────────────────────────────────────
#  WebhookDelivery model
#  Tracks every webhook delivery attempt.
#  One Change can trigger many WebhookDeliveries
#  (one per active matching subscription).
#  Stores the full delivery history including
#  retries and failure reasons.
# ─────────────────────────────────────────────────


import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, Integer, Boolean, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
 
    # Primary key
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
 
    # ── Foreign keys ──────────────────────────────
 
    # Which change triggered this delivery
    change_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("changes.id"), nullable=False, index=True
    )
    
    # Which subscription this is being delivered to
    subscription_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("subscriptions.id"), nullable=False, index=True
    )
 
    # ── Delivery target ───────────────────────────
 
    # The URL we're posting to (snapshot — in case subscription URL changes later)
    webhook_url: Mapped[str] = mapped_column(String(500), nullable=False)
    
    # ── Delivery state ───────────────────────────
    
    # Current delivery status:
    # "pending"   → queued, not yet attempted
    # "success"   → delivered successfully (2xx response)
    # "failed"    → all retries exhausted
    # "retrying"  → failed once, waiting for next retry
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", index=True
    )
    
    # ── Attempt tracking ──────────────────────────
 
    # How many delivery attempts have been made
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
 
    # Maximum attempts before marking as permanently failed
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    
    # HTTP status code from the last delivery attempt
    # e.g. 200, 404, 500, None if never attempted
    last_http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
 
    # Response body from the developer's server (first 500 chars)
    # Useful for debugging why a webhook is failing
    last_response_body: Mapped[str | None] = mapped_column(String(500), nullable=True)
 
    # Error message if the request itself failed (network error, timeout, etc.)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
 
    # Latency of the last delivery attempt in milliseconds
    last_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # ── Retry scheduling ──────────────────────────
 
    # When the next retry should be attempted
    # Null if status is "success" or "failed"
    # Retry schedule: 1m → 5m → 30m → 2h → 24h
    next_retry_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
 
    # ── Payload ───────────────────────────────────
 
    # The exact JSON payload that was (or will be) sent
    # Stored so retries send identical payloads
    payload_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
 
    # HMAC-SHA256 signature sent in X-Lawhook-Signature header
    signature: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    # ── Timestamps ───────────────────────────────
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    first_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    
    # ── Relationships ─────────────────────────────
    
    change = relationship("Change", backref="webhook_deliveries")
    subscription = relationship("Subscription", backref="webhook_deliveries")
 
    # ── Indexes ───────────────────────────────────
    __table_args__ = (
        # For the retry worker: find all pending/retrying deliveries due now
        Index("ix_webhook_status_retry", "status", "next_retry_at"),
        # For the dashboard: all deliveries for a subscription
        Index("ix_webhook_subscription_created", "subscription_id", "created_at"),
    )
 
    def __repr__(self) -> str:
        return (
            f"<WebhookDelivery {self.id[:8]} "
            f"change={self.change_id[:8]} "
            f"status={self.status} "
            f"attempts={self.attempt_count}>"
        )