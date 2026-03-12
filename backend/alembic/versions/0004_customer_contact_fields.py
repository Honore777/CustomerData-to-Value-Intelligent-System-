"""Add optional customer email column

Revision ID: 0005_customer_contacts
Revises: 0004_customer_phone
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0005_customer_contacts"
down_revision = "0004_customer_phone"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_column(inspector, "customers", "email"):
        op.add_column("customers", sa.Column("email", sa.String(length=255), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if _has_column(inspector, "customers", "email"):
        op.drop_column("customers", "email")