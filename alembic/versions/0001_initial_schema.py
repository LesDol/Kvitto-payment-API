"""Create payment tables.

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-19
"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tariffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=30), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("price_kopecks", sa.Integer(), nullable=False),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tariff_id", sa.Integer(), sa.ForeignKey("tariffs.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("method", sa.String(length=20), nullable=False),
        sa.Column("installment_months", sa.Integer(), nullable=True),
        sa.Column("promo_code", sa.String(length=50), nullable=True),
        sa.Column("amount_kopecks", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("amount_kopecks >= 0", name="ck_payment_amount_nonnegative"),
        sa.CheckConstraint("status IN ('pending', 'succeeded', 'failed', 'refunded')", name="ck_payment_status"),
        sa.CheckConstraint("method IN ('card', 'sbp', 'installment')", name="ck_payment_method"),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_table(
        "installments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("amount_kopecks", sa.Integer(), nullable=False),
        sa.UniqueConstraint("payment_id", "number", name="uq_installment_payment_number"),
        sa.CheckConstraint("amount_kopecks >= 0", name="ck_installment_amount_nonnegative"),
    )


def downgrade() -> None:
    op.drop_table("installments")
    op.drop_table("payments")
    op.drop_table("tariffs")
