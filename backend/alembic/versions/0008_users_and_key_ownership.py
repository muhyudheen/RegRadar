# ─────────────────────────────────────────────────
#  Users + API-key ownership; tier moves to the user
#
#  - Creates the `users` table (email/password account).
#  - Adds `api_keys.user_id` FK → users.id (ON DELETE CASCADE),
#    NOT NULL — every key now belongs to a user.
#  - Drops `api_keys.tier` — tier lives on the user; keys inherit it.
#
#  ⚠️ DESTRUCTIVE — FRESH START (intentional, per Pass 1 spec):
#  Because user_id is NOT NULL and there is no owner to backfill for
#  pre-existing keys, this migration WIPES all existing api_keys (and
#  their subscriptions + webhook_deliveries) before adding the FK.
#  There is no data migration — existing keys/subs are discarded.
#  Take a backup first if any of that data matters.
# ─────────────────────────────────────────────────

from alembic import op
import sqlalchemy as sa

revision = "0008_users_and_key_ownership"
down_revision = "0007_cascade_delete_deliveries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Wipe existing rows that can't satisfy the new NOT NULL user_id.
    #    Order respects FKs: deliveries → subscriptions → keys.
    op.execute("DELETE FROM webhook_deliveries")
    op.execute("DELETE FROM subscriptions")
    op.execute("DELETE FROM api_keys")

    # 2. Create the users table.
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "tier",
            sa.String(length=20),
            nullable=False,
            server_default="free",
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 3. Add api_keys.user_id FK (NOT NULL — table is now empty).
    op.add_column(
        "api_keys",
        sa.Column("user_id", sa.String(length=36), nullable=False),
    )
    op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
    op.create_foreign_key(
        "api_keys_user_id_fkey",
        "api_keys",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # 4. Drop the per-key tier column (now lives on users).
    op.drop_column("api_keys", "tier")


def downgrade() -> None:
    # Re-add the per-key tier column.
    op.add_column(
        "api_keys",
        sa.Column(
            "tier",
            sa.String(length=20),
            nullable=False,
            server_default="free",
        ),
    )

    # Drop the ownership FK/column.
    op.drop_constraint("api_keys_user_id_fkey", "api_keys", type_="foreignkey")
    op.drop_index("ix_api_keys_user_id", table_name="api_keys")
    op.drop_column("api_keys", "user_id")

    # Drop users.
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
