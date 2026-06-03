"""
fixing key hash length

Revision ID: 0003_fix_key_hash_length
Revises: 0002_add_signing_secret
Create Date: 2024-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = '0003_fix_key_hash_length'
down_revision = '0002_add_signing_secret'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.alter_column(
        "api_keys",
        "key_hash",
        existing_type=sa.String(length=20),
        type_=sa.String(length=64),
        existing_nullable=False
    )
    
def downgrade() -> None:
    op.alter_column(
        "api_keys",
        "key_hash",
        existing_type=sa.String(length=64),
        type_=sa.String(length=20),
        existing_nullable=False
    )