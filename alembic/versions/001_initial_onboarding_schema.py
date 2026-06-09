"""Initial onboarding schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "restaurant_users" in inspector.get_table_names():
        return

    # ── restaurant_users ──────────────────────────────────────────────────────
    op.create_table(
        "restaurant_users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="owner"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("refresh_token_hash", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_restaurant_users_email", "restaurant_users", ["email"], unique=True)
    op.create_index("ix_restaurant_users_id", "restaurant_users", ["id"])
    op.create_index("ix_restaurant_users_restaurant_id", "restaurant_users", ["restaurant_id"])

    # ── restaurant_onboarding_progress ────────────────────────────────────────
    op.create_table(
        "restaurant_onboarding_progress",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("current_step", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("completion_percentage", sa.Float(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(50), nullable=False, server_default="draft"),
        sa.Column("steps_data", postgresql.JSONB(), nullable=True),
        sa.Column("last_saved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_restaurant_onboarding_progress_id", "restaurant_onboarding_progress", ["id"])
    op.create_index(
        "ix_restaurant_onboarding_progress_restaurant_id",
        "restaurant_onboarding_progress",
        ["restaurant_id"],
        unique=True,
    )

    # ── onboarding_step_data ──────────────────────────────────────────────────
    op.create_table(
        "onboarding_step_data",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_onboarding_step_data_id", "onboarding_step_data", ["id"])
    op.create_index("ix_onboarding_step_data_restaurant_id", "onboarding_step_data", ["restaurant_id"])
    op.create_unique_constraint(
        "uq_onboarding_step_restaurant_step",
        "onboarding_step_data",
        ["restaurant_id", "step_number"],
    )

    # ── restaurant_profiles ───────────────────────────────────────────────────
    op.create_table(
        "restaurant_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("legal_name", sa.String(255), nullable=True),
        sa.Column("restaurant_type", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("social_links", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_restaurant_profiles_id", "restaurant_profiles", ["id"])
    op.create_index("ix_restaurant_profiles_restaurant_id", "restaurant_profiles", ["restaurant_id"], unique=True)

    # ── restaurant_contacts ───────────────────────────────────────────────────
    op.create_table(
        "restaurant_contacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("owner_name", sa.String(255), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_restaurant_contacts_id", "restaurant_contacts", ["id"])
    op.create_index("ix_restaurant_contacts_restaurant_id", "restaurant_contacts", ["restaurant_id"], unique=True)

    # ── restaurant_features ───────────────────────────────────────────────────
    op.create_table(
        "restaurant_features",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("reservation_types", postgresql.JSONB(), nullable=True),
        sa.Column("cuisine_types", postgresql.JSONB(), nullable=True),
        sa.Column("services_offered", postgresql.JSONB(), nullable=True),
        sa.Column("seating_capacity", sa.Integer(), nullable=True),
        sa.Column("number_tables", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_restaurant_features_id", "restaurant_features", ["id"])
    op.create_index("ix_restaurant_features_restaurant_id", "restaurant_features", ["restaurant_id"], unique=True)

    # ── restaurant_documents ──────────────────────────────────────────────────
    op.create_table(
        "restaurant_documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("file_url", sa.String(1000), nullable=True),
        sa.Column("file_name", sa.String(500), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("storage_key", sa.String(500), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_restaurant_documents_id", "restaurant_documents", ["id"])
    op.create_index("ix_restaurant_documents_restaurant_id", "restaurant_documents", ["restaurant_id"])
    op.create_unique_constraint("uq_restaurant_documents_storage_key", "restaurant_documents", ["storage_key"])

    # ── restaurant_subscriptions ──────────────────────────────────────────────
    op.create_table(
        "restaurant_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("restaurant_id", sa.Integer(), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="starter"),
        sa.Column("billing_cycle", sa.String(20), nullable=False, server_default="monthly"),
        sa.Column("status", sa.String(50), nullable=False, server_default="trial"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_restaurant_subscriptions_id", "restaurant_subscriptions", ["id"])
    op.create_index("ix_restaurant_subscriptions_restaurant_id", "restaurant_subscriptions", ["restaurant_id"], unique=True)

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", sa.String(100), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("old_values", postgresql.JSONB(), nullable=True),
        sa.Column("new_values", postgresql.JSONB(), nullable=True),
        sa.Column("performed_by", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(50), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"])
    op.create_index("ix_audit_logs_table_name", "audit_logs", ["table_name"])


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("restaurant_subscriptions")
    op.drop_table("restaurant_documents")
    op.drop_table("restaurant_features")
    op.drop_table("restaurant_contacts")
    op.drop_table("restaurant_profiles")
    op.drop_table("onboarding_step_data")
    op.drop_table("restaurant_onboarding_progress")
    op.drop_table("restaurant_users")
