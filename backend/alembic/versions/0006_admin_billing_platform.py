"""Add platform admin and business billing fields

Revision ID: 0006_admin_billing_platform
Revises: 0005_customer_contacts
Create Date: 2026-03-11
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_admin_billing_platform"
down_revision = "0005_customer_contacts"
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _column_exists(inspector, "users", "is_platform_admin"):
        op.add_column("users", sa.Column("is_platform_admin", sa.Boolean(), nullable=False, server_default=sa.false()))

    if not _column_exists(inspector, "businesses", "subscription_status"):
        op.add_column("businesses", sa.Column("subscription_status", sa.String(length=50), nullable=False, server_default="trial"))

    if not _column_exists(inspector, "businesses", "trial_started_at"):
        op.add_column("businesses", sa.Column("trial_started_at", sa.Date(), nullable=True))

    if not _column_exists(inspector, "businesses", "trial_ends_at"):
        op.add_column("businesses", sa.Column("trial_ends_at", sa.Date(), nullable=True))

    if not _column_exists(inspector, "businesses", "billing_due_date"):
        op.add_column("businesses", sa.Column("billing_due_date", sa.Date(), nullable=True))

    if not _column_exists(inspector, "businesses", "last_payment_reminder_sent_at"):
        op.add_column("businesses", sa.Column("last_payment_reminder_sent_at", sa.DateTime(), nullable=True))

    if not _column_exists(inspector, "businesses", "monthly_price"):
        op.add_column("businesses", sa.Column("monthly_price", sa.Float(), nullable=True))

    op.execute("UPDATE users SET is_platform_admin = FALSE WHERE is_platform_admin IS NULL")
    op.execute("UPDATE businesses SET subscription_status = 'trial' WHERE subscription_status IS NULL")

    op.alter_column("users", "is_platform_admin", server_default=None)
    op.alter_column("businesses", "subscription_status", server_default=None)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for column_name in [
        "monthly_price",
        "last_payment_reminder_sent_at",
        "billing_due_date",
        "trial_ends_at",
        "trial_started_at",
        "subscription_status",
    ]:
        if _column_exists(inspector, "businesses", column_name):
            op.drop_column("businesses", column_name)

    if _column_exists(inspector, "users", "is_platform_admin"):
        op.drop_column("users", "is_platform_admin")