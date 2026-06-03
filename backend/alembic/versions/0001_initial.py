"""initial tables
 
Revision ID: 0001_initial
Revises: 
Create Date: 2026-05-31
 
Creates all 4 core tables:
- api_keys
- subscriptions
- changes
- webhook_deliveries
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
     # 1. aPI keys
     
    op.create_table(
        'api_keys',
        sa.Column("id",           sa.String(36),  primary_key=True),
        sa.Column("name",         sa.String(150), nullable=False),
        sa.Column("key_hash",     sa.String(255), nullable=False, unique=True),
        sa.Column("key_prefix",   sa.String(20),  nullable=False),
        sa.Column("is_active",    sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at",   sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at",   sa.DateTime(timezone=True), nullable=True),
     )
     
        # 2. Subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id",            sa.String(36),  primary_key=True),
        sa.Column("api_key_id",    sa.String(36),  nullable=False),
        sa.Column("name",          sa.String(100), nullable=False),
        sa.Column("jurisdiction",  sa.String(10),  nullable=False),
        sa.Column("industry",      sa.String(50),  nullable=False),
        sa.Column("topics",        ARRAY(sa.Text), nullable=True),
        sa.Column("webhook_url",   sa.String(500), nullable=False),
        sa.Column("severity_min",  sa.String(20),  nullable=False, server_default="minor"),
        sa.Column("is_active",     sa.Boolean(),   nullable=False, server_default="true"),
        sa.Column("created_at",    sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at",    sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["api_key_id"], ["api_keys.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_subscriptions_api_key_id", "subscriptions", ["api_key_id"])
    op.create_index("ix_subscriptions_jurisdiction", "subscriptions", ["jurisdiction"])
    op.create_index("ix_subscriptions_industry",     "subscriptions", ["industry"])
    
    # 3. Changes
    
    op.create_table(
        "changes",
        sa.Column("id",                  sa.String(36),   primary_key=True),
        sa.Column("jurisdiction",        sa.String(10),   nullable=False),
        sa.Column("industry",            sa.String(50),   nullable=False),
        sa.Column("topic",               sa.String(100),  nullable=True),
        sa.Column("source_authority",    sa.String(200),  nullable=False),
        sa.Column("source_url",          sa.String(1000), nullable=False),
        sa.Column("source_snapshot",     sa.Text,         nullable=True),
        sa.Column("content_hash",        sa.String(64),   nullable=False),
        sa.Column("archived_at",         sa.DateTime(timezone=True), nullable=True),
        sa.Column("summary",             sa.Text,         nullable=True),
        sa.Column("severity",            sa.String(20),   nullable=True),
        sa.Column("diff",                sa.JSON,         nullable=True),
        sa.Column("effective_date",      sa.Date,         nullable=True),
        sa.Column("status",              sa.String(20),   nullable=False, server_default="raw"),
        sa.Column("processing_attempts", sa.Integer,      nullable=False, server_default="0"),
        sa.Column("processing_error",    sa.Text,         nullable=True),
        sa.Column("detected_at",         sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("processed_at",        sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_changes_jurisdiction",          "changes", ["jurisdiction"])
    op.create_index("ix_changes_industry",              "changes", ["industry"])
    op.create_index("ix_changes_topic",                 "changes", ["topic"])
    op.create_index("ix_changes_severity",              "changes", ["severity"])
    op.create_index("ix_changes_status",                "changes", ["status"])
    op.create_index("ix_changes_jurisdiction_industry", "changes", ["jurisdiction", "industry"])
    op.create_index("ix_changes_status_detected",       "changes", ["status", "detected_at"])
    
    # 4. Webhook deliveries
    
    op.create_table(
        "webhook_deliveries",
        sa.Column("id",                  sa.String(36),  primary_key=True),
        sa.Column("change_id",           sa.String(36),  nullable=False),
        sa.Column("subscription_id",     sa.String(36),  nullable=False),
        sa.Column("webhook_url",         sa.String(500), nullable=False),
        sa.Column("status",              sa.String(20),  nullable=False, server_default="pending"),
        sa.Column("attempt_count",       sa.Integer,     nullable=False, server_default="0"),
        sa.Column("max_attempts",        sa.Integer,     nullable=False, server_default="5"),
        sa.Column("last_http_status",    sa.Integer,     nullable=True),
        sa.Column("last_response_body",  sa.String(500), nullable=True),
        sa.Column("last_error",          sa.Text,        nullable=True),
        sa.Column("last_latency_ms",     sa.Integer,     nullable=True),
        sa.Column("next_retry_at",       sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_snapshot",    sa.Text,        nullable=True),
        sa.Column("signature",           sa.String(100), nullable=True),
        sa.Column("created_at",          sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.Column("first_attempted_at",  sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempted_at",   sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at",        sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["change_id"],       ["changes.id"],       ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_webhook_change_id",             "webhook_deliveries", ["change_id"])
    op.create_index("ix_webhook_subscription_id",       "webhook_deliveries", ["subscription_id"])
    op.create_index("ix_webhook_status",                "webhook_deliveries", ["status"])
    op.create_index("ix_webhook_status_retry",          "webhook_deliveries", ["status", "next_retry_at"])
    op.create_index("ix_webhook_subscription_created",  "webhook_deliveries", ["subscription_id", "created_at"])
    
def downgrade() -> None:
    """Drop all tables in reverse order (respects foreign keys)."""
    op.drop_table("webhook_deliveries")
    op.drop_table("changes")
    op.drop_table("subscriptions")
    op.drop_table("api_keys")   
 