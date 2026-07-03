# ─────────────────────────────────────────────────
#  Cascade-delete webhook_deliveries with their subscription
#
#  Before: webhook_deliveries.subscription_id had no ON DELETE
#  rule, so deleting a Subscription made the ORM try to NULL
#  the children first → NotNullViolation → 500.
#
#  After: Postgres cascades the delete to child rows.
#
#  NOTE: model side also needs passive_deletes=True on the
#  relationship, or SQLAlchemy STILL emits the UPDATE...SET
#  subscription_id=NULL and you hit the same 500 despite this.
# ─────────────────────────────────────────────────

from alembic import op

revision = "0007_cascade_delete_deliveries"
down_revision = "0006_api_key_tier"
branch_labels = None
depends_on = None

# ⚠️ Confirm this matches your DB before running:
#   SELECT conname FROM pg_constraint
#   WHERE conrelid = 'webhook_deliveries'::regclass AND contype = 'f';
CONSTRAINT = "webhook_deliveries_subscription_id_fkey"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT, "webhook_deliveries", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT,
        "webhook_deliveries", "subscriptions",
        ["subscription_id"], ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT, "webhook_deliveries", type_="foreignkey")
    op.create_foreign_key(
        CONSTRAINT,
        "webhook_deliveries", "subscriptions",
        ["subscription_id"], ["id"],
    )