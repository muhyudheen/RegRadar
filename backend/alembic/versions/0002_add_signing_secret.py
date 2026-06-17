"""
add signing secret to subscriptions

Revision ID: 0002_add_signing_secret
Revises: 0001_initial
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = '0002_add_signing_secret'
down_revision = '0001_initial'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column(
            "signing_secret",
            sa.String(60),
            nullable=False,
            server_default="pending_secret"
        )
    )
    
def downgrade() -> None:
    op.drop_column("subscriptions", "signing_secret")
