"""Add customer phone column

Revision ID: 0004_customer_phone
Revises: 0003_pred_loc_fix
Create Date: 2026-03-10
"""

from alembic import op
import sqlalchemy as sa


revision = "0004_customer_phone"
down_revision = "0003_pred_loc_fix"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def upgrade() -> None:
    if not _column_exists("customers", "phone"):
        op.add_column("customers", sa.Column("phone", sa.String(length=50), nullable=True))


def downgrade() -> None:
    if _column_exists("customers", "phone"):
        op.drop_column("customers", "phone")