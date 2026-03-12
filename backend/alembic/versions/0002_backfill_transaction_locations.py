"""backfill transaction location support

Revision ID: 0002_txn_location_fix
Revises: 0001_baseline_current_schema
Create Date: 2026-03-10 14:40:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_txn_location_fix"
down_revision: Union[str, None] = "0001_baseline_current_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}

    # Older databases were created before branch/location support was added.
    # We repair them by creating one default location per business and linking
    # every existing transaction to that default location.
    if "location_id" not in transaction_columns:
        op.add_column("transactions", sa.Column("location_id", sa.Integer(), nullable=True))

        op.execute(
            sa.text(
                """
                INSERT INTO locations (
                    business_id,
                    location_code,
                    name,
                    is_active,
                    created_at,
                    updated_at
                )
                SELECT DISTINCT
                    t.business_id,
                    'main',
                    'Main Business',
                    TRUE,
                    NOW(),
                    NOW()
                FROM transactions t
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM locations l
                    WHERE l.business_id = t.business_id
                      AND l.location_code = 'main'
                )
                """
            )
        )

        op.execute(
            sa.text(
                """
                UPDATE transactions t
                SET location_id = l.id
                FROM locations l
                WHERE l.business_id = t.business_id
                  AND l.location_code = 'main'
                  AND t.location_id IS NULL
                """
            )
        )

        op.alter_column("transactions", "location_id", nullable=False)
        op.create_foreign_key(
            "fk_transactions_location_id_locations",
            "transactions",
            "locations",
            ["location_id"],
            ["id"],
        )
        op.create_index("idx_location_date", "transactions", ["location_id", "purchase_date"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    transaction_columns = {column["name"] for column in inspector.get_columns("transactions")}
    indexes = {index["name"] for index in inspector.get_indexes("transactions")}
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys("transactions") if fk.get("name")}

    if "idx_location_date" in indexes:
        op.drop_index("idx_location_date", table_name="transactions")

    if "fk_transactions_location_id_locations" in foreign_keys:
        op.drop_constraint("fk_transactions_location_id_locations", "transactions", type_="foreignkey")

    if "location_id" in transaction_columns:
        op.drop_column("transactions", "location_id")