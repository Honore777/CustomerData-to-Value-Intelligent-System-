"""backfill prediction-related location support

Revision ID: 0003_pred_loc_fix
Revises: 0002_txn_location_fix
Create Date: 2026-03-10 16:30:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003_pred_loc_fix"
down_revision: Union[str, None] = "0002_txn_location_fix"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_location_id_column(table_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns(table_name)}

    if "location_id" not in columns:
        op.add_column(table_name, sa.Column("location_id", sa.Integer(), nullable=True))


def _create_index_if_missing(table_name: str, index_name: str, columns: list[str]) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    indexes = {index["name"] for index in inspector.get_indexes(table_name)}

    if index_name not in indexes:
        op.create_index(index_name, table_name, columns, unique=False)


def _create_fk_if_missing(table_name: str, fk_name: str) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}

    if fk_name not in foreign_keys:
        op.create_foreign_key(
            fk_name,
            table_name,
            "locations",
            ["location_id"],
            ["id"],
        )


def upgrade() -> None:
    bind = op.get_bind()

    # Older databases were migrated only part-way to location-aware scoring.
    # The application now stores predictions, history, and interventions per
    # location, so these three tables must all carry location_id.
    _ensure_location_id_column("predictions")
    _ensure_location_id_column("prediction_history")
    _ensure_location_id_column("business_actions")

    # Prefer the business' synthetic main location when it exists. If an older
    # database only has DEFAULT or another first-created location, fall back to
    # that so every legacy row still gets a deterministic branch assignment.
    op.execute(
        sa.text(
            """
            WITH preferred_locations AS (
                SELECT
                    business_id,
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY business_id
                        ORDER BY
                            CASE
                                WHEN location_code = 'main' THEN 0
                                WHEN location_code = 'DEFAULT' THEN 1
                                ELSE 2
                            END,
                            id
                    ) AS rn
                FROM locations
            )
            UPDATE predictions p
            SET location_id = preferred.id
            FROM preferred_locations preferred
            WHERE p.business_id = preferred.business_id
              AND preferred.rn = 1
              AND p.location_id IS NULL
            """
        )
    )

    # History and actions should follow the location already assigned to their
    # originating prediction when possible.
    op.execute(
        sa.text(
            """
            UPDATE prediction_history h
            SET location_id = p.location_id
            FROM predictions p
            WHERE h.prediction_id = p.id
              AND h.location_id IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            UPDATE business_actions a
            SET location_id = p.location_id
            FROM predictions p
            WHERE a.prediction_id = p.id
              AND a.location_id IS NULL
            """
        )
    )

    # Safety fallback for any legacy rows that still could not resolve through
    # prediction_id, such as partially-created data from earlier experiments.
    op.execute(
        sa.text(
            """
            WITH preferred_locations AS (
                SELECT
                    business_id,
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY business_id
                        ORDER BY
                            CASE
                                WHEN location_code = 'main' THEN 0
                                WHEN location_code = 'DEFAULT' THEN 1
                                ELSE 2
                            END,
                            id
                    ) AS rn
                FROM locations
            )
            UPDATE prediction_history h
            SET location_id = preferred.id
            FROM preferred_locations preferred
            WHERE h.business_id = preferred.business_id
              AND preferred.rn = 1
              AND h.location_id IS NULL
            """
        )
    )

    op.execute(
        sa.text(
            """
            WITH preferred_locations AS (
                SELECT
                    business_id,
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY business_id
                        ORDER BY
                            CASE
                                WHEN location_code = 'main' THEN 0
                                WHEN location_code = 'DEFAULT' THEN 1
                                ELSE 2
                            END,
                            id
                    ) AS rn
                FROM locations
            )
            UPDATE business_actions a
            SET location_id = preferred.id
            FROM preferred_locations preferred
            WHERE a.business_id = preferred.business_id
              AND preferred.rn = 1
              AND a.location_id IS NULL
            """
        )
    )

    op.alter_column("predictions", "location_id", nullable=False)
    op.alter_column("prediction_history", "location_id", nullable=False)
    op.alter_column("business_actions", "location_id", nullable=False)

    _create_fk_if_missing("predictions", "fk_predictions_location_id_locations")
    _create_fk_if_missing("prediction_history", "fk_prediction_history_location_id_locations")
    _create_fk_if_missing("business_actions", "fk_business_actions_location_id_locations")

    _create_index_if_missing("predictions", "idx_location_reference_date", ["location_id", "reference_date"])
    _create_index_if_missing("prediction_history", "idx_location_history", ["location_id", "current_reference_date"])
    _create_index_if_missing("business_actions", "idx_location_action_date", ["location_id", "action_date"])
    _create_index_if_missing("business_actions", "idx_location_status", ["location_id", "status"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    for table_name, index_name in [
        ("business_actions", "idx_location_status"),
        ("business_actions", "idx_location_action_date"),
        ("prediction_history", "idx_location_history"),
        ("predictions", "idx_location_reference_date"),
    ]:
        indexes = {index["name"] for index in inspector.get_indexes(table_name)}
        if index_name in indexes:
            op.drop_index(index_name, table_name=table_name)

    for table_name, fk_name in [
        ("business_actions", "fk_business_actions_location_id_locations"),
        ("prediction_history", "fk_prediction_history_location_id_locations"),
        ("predictions", "fk_predictions_location_id_locations"),
    ]:
        foreign_keys = {fk["name"] for fk in inspector.get_foreign_keys(table_name) if fk.get("name")}
        if fk_name in foreign_keys:
            op.drop_constraint(fk_name, table_name, type_="foreignkey")

    for table_name in ["business_actions", "prediction_history", "predictions"]:
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "location_id" in columns:
            op.drop_column(table_name, "location_id")