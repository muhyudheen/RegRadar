"""add dedup constraint to changes

Revision ID: 0005_change_dedup
Revises: 0004_unique_constraints
Create Date: 2026-06-06
"""

from alembic import op

revision = '0005_change_dedup'
down_revision = '0004_unique_constraints'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Prevents duplicate Change rows if Redis lock fails.
    # Same source_url + content_hash = same change, reject it.
    op.create_unique_constraint(
        "uq_changes_source_url_hash",
        "changes",
        ["source_url", "content_hash"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_changes_source_url_hash",
        "changes",
        type_="unique"
    )