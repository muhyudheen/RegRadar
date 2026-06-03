"""add missing unique constraints

Revision ID: 0004_unique_constraints
Revises: 0003_fix_key_hash_length
Create Date: 2026-06-01
"""

from alembic import op

revision = '0004_unique_constraints'
down_revision = '0003_fix_key_hash_length'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # api_keys.key_hash — must be unique
    # two keys with same hash = authentication collision
    op.create_unique_constraint(
        "uq_api_keys_key_hash",
        "api_keys",
        ["key_hash"]
    )

    # subscriptions.signing_secret — must be unique
    # each subscription needs its own secret
    op.create_unique_constraint(
        "uq_subscriptions_signing_secret",
        "subscriptions",
        ["signing_secret"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_subscriptions_signing_secret",
        "subscriptions",
        type_="unique"
    )
    op.drop_constraint(
        "uq_api_keys_key_hash",
        "api_keys",
        type_="unique"
    )