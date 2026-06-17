# ─────────────────────────────────────────────────
#  Add tier column to api_keys
#
#  Tiers control rate limits (see rate_limiter.py):
#    free       — 60 req/min,   1,000 req/day  (default)
#    pro        — 600 req/min,  50,000 req/day
#    enterprise — 6,000 req/min, 1,000,000 req/day
#
#  No billing/upgrade endpoint yet — tier is set manually
#  via SQL until Stripe integration exists:
#
#    UPDATE api_keys SET tier = 'pro' WHERE id = '...';
# ─────────────────────────────────────────────────

from alembic import op
import sqlalchemy as sa

revision = "0006_api_key_tier"
down_revision = "0005_change_dedup"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "api_keys",
        sa.Column(
            "tier",
            sa.String(),
            nullable=False,
            server_default="free"
        )
    )
    
def downgrade() -> None:
    op.drop_column("api_keys", "tier")