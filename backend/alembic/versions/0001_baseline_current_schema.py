"""initial application schema

Revision ID: 0001_baseline_current_schema
Revises:
Create Date: 2026-03-08 10:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_baseline_current_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "businesses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("timezone", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("upload_frequency", sa.String(length=50), nullable=True),
        sa.Column("reference_period_days", sa.Integer(), nullable=True),
        sa.Column("allow_manual_reference_date", sa.Boolean(), nullable=True),
        sa.Column("recency_threshold_days", sa.Integer(), nullable=True),
        sa.Column("frequency_threshold", sa.Integer(), nullable=True),
        sa.Column("monetary_threshold", sa.Float(), nullable=True),
        sa.Column("column_mapping", sa.JSON(), nullable=True),
        sa.Column("date_format", sa.String(length=50), nullable=True),
        sa.UniqueConstraint("email", name="uq_businesses_email"),
    )

    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("last_purchase_date", sa.DateTime(), nullable=True),
        sa.Column("total_spent", sa.Float(), nullable=True),
        sa.Column("total_purchases", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index("idx_business_customer", "customers", ["business_id", "customer_id"], unique=False)

    op.create_table(
        "locations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("location_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("manager_name", sa.String(length=255), nullable=True),
        sa.Column("manager_email", sa.String(length=255), nullable=True),
        sa.Column("reference_period_days", sa.Integer(), nullable=True),
        sa.Column("recency_threshold_days", sa.Integer(), nullable=True),
        sa.Column("frequency_threshold", sa.Integer(), nullable=True),
        sa.Column("monetary_threshold", sa.Float(), nullable=True),
        sa.Column("column_mapping", sa.JSON(), nullable=True),
        sa.Column("date_format", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index("idx_business_location", "locations", ["business_id", "location_code"], unique=False)
    op.create_index("idx_location_active", "locations", ["business_id", "is_active"], unique=False)

    op.create_table(
        "model_evaluation",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("evaluation_date", sa.Date(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=False),
        sa.Column("precision", sa.Float(), nullable=True),
        sa.Column("recall", sa.Float(), nullable=True),
        sa.Column("f1_score", sa.Float(), nullable=True),
        sa.Column("num_predictions", sa.Integer(), nullable=False),
        sa.Column("num_actual_churned", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index("idx_business_eval_date", "model_evaluation", ["business_id", "evaluation_date"], unique=False)

    op.create_table(
        "model_metadata",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("model_path", sa.String(length=500), nullable=False),
        sa.Column("training_date", sa.DateTime(), nullable=False),
        sa.Column("accuracy", sa.Float(), nullable=True),
        sa.Column("num_samples", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.UniqueConstraint("business_id", name="uq_model_metadata_business_id"),
    )

    op.create_table(
        "monthly_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("month_year", sa.String(length=20), nullable=False),
        sa.Column("reference_date_start", sa.Date(), nullable=False),
        sa.Column("reference_date_end", sa.Date(), nullable=False),
        sa.Column("total_actions_taken", sa.Integer(), nullable=True),
        sa.Column("actions_by_type", sa.String(length=500), nullable=True),
        sa.Column("customers_returned", sa.Integer(), nullable=True),
        sa.Column("return_rate", sa.Float(), nullable=True),
        sa.Column("total_revenue_recovered", sa.Float(), nullable=True),
        sa.Column("average_recovery_value", sa.Float(), nullable=True),
        sa.Column("total_cost_of_actions", sa.Float(), nullable=True),
        sa.Column("net_roi", sa.Float(), nullable=True),
        sa.Column("roi_percent", sa.Float(), nullable=True),
        sa.Column("churned_count", sa.Integer(), nullable=True),
        sa.Column("at_risk_count", sa.Integer(), nullable=True),
        sa.Column("active_count", sa.Integer(), nullable=True),
        sa.Column("loyal_count", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
    )
    op.create_index("idx_business_month", "monthly_metrics", ["business_id", "month_year"], unique=False)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("assigned_location_ids", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("idx_business_role", "users", ["business_id", "role"], unique=False)
    op.create_index("idx_email", "users", ["email"], unique=False)

    op.create_table(
        "invite_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=255), nullable=False),
        sa.Column("is_used", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.UniqueConstraint("token", name="uq_invite_tokens_token"),
    )
    op.create_index("idx_email_location", "invite_tokens", ["email", "location_id"], unique=False)
    op.create_index("idx_token", "invite_tokens", ["token"], unique=False)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=True),
        sa.Column("purchase_date", sa.DateTime(), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
    )
    op.create_index("idx_business_date", "transactions", ["business_id", "purchase_date"], unique=False)
    op.create_index("idx_customer_date", "transactions", ["customer_id", "purchase_date"], unique=False)
    op.create_index("idx_location_date", "transactions", ["location_id", "purchase_date"], unique=False)

    op.create_table(
        "predictions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("segment", sa.String(length=50), nullable=False),
        sa.Column("churn_probability", sa.Float(), nullable=False),
        sa.Column("recency", sa.Integer(), nullable=False),
        sa.Column("frequency", sa.Integer(), nullable=False),
        sa.Column("monetary", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
    )
    op.create_index("idx_business_reference_date", "predictions", ["business_id", "reference_date"], unique=False)
    op.create_index("idx_location_reference_date", "predictions", ["location_id", "reference_date"], unique=False)
    op.create_index("idx_segment", "predictions", ["location_id", "segment"], unique=False)

    op.create_table(
        "business_actions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("segment_when_actioned", sa.String(length=50), nullable=False),
        sa.Column("action_type", sa.String(length=100), nullable=False),
        sa.Column("action_description", sa.Text(), nullable=True),
        sa.Column("action_date", sa.Date(), nullable=False),
        sa.Column("reference_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=True),
        sa.Column("outcome_recorded", sa.Boolean(), nullable=True),
        sa.Column("customer_returned", sa.Boolean(), nullable=True),
        sa.Column("days_to_return", sa.Integer(), nullable=True),
        sa.Column("revenue_recovered", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
    )
    op.create_index("idx_location_action_date", "business_actions", ["location_id", "action_date"], unique=False)
    op.create_index("idx_location_status", "business_actions", ["location_id", "status"], unique=False)

    op.create_table(
        "prediction_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("business_id", sa.Integer(), nullable=False),
        sa.Column("location_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("prediction_id", sa.Integer(), nullable=False),
        sa.Column("previous_segment", sa.String(length=50), nullable=True),
        sa.Column("current_segment", sa.String(length=50), nullable=False),
        sa.Column("previous_reference_date", sa.Date(), nullable=True),
        sa.Column("current_reference_date", sa.Date(), nullable=False),
        sa.Column("segment_improved", sa.Boolean(), nullable=True),
        sa.Column("days_in_previous_segment", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["business_id"], ["businesses.id"]),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"]),
        sa.ForeignKeyConstraint(["location_id"], ["locations.id"]),
        sa.ForeignKeyConstraint(["prediction_id"], ["predictions.id"]),
    )
    op.create_index("idx_location_history", "prediction_history", ["location_id", "current_reference_date"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_location_history", table_name="prediction_history")
    op.drop_table("prediction_history")

    op.drop_index("idx_location_status", table_name="business_actions")
    op.drop_index("idx_location_action_date", table_name="business_actions")
    op.drop_table("business_actions")

    op.drop_index("idx_segment", table_name="predictions")
    op.drop_index("idx_location_reference_date", table_name="predictions")
    op.drop_index("idx_business_reference_date", table_name="predictions")
    op.drop_table("predictions")

    op.drop_index("idx_location_date", table_name="transactions")
    op.drop_index("idx_customer_date", table_name="transactions")
    op.drop_index("idx_business_date", table_name="transactions")
    op.drop_table("transactions")

    op.drop_index("idx_token", table_name="invite_tokens")
    op.drop_index("idx_email_location", table_name="invite_tokens")
    op.drop_table("invite_tokens")

    op.drop_index("idx_email", table_name="users")
    op.drop_index("idx_business_role", table_name="users")
    op.drop_table("users")

    op.drop_index("idx_business_month", table_name="monthly_metrics")
    op.drop_table("monthly_metrics")

    op.drop_table("model_metadata")

    op.drop_index("idx_business_eval_date", table_name="model_evaluation")
    op.drop_table("model_evaluation")

    op.drop_index("idx_location_active", table_name="locations")
    op.drop_index("idx_business_location", table_name="locations")
    op.drop_table("locations")

    op.drop_index("idx_business_customer", table_name="customers")
    op.drop_table("customers")

    op.drop_table("businesses")