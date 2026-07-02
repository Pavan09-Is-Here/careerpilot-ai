"""Add notifications outbox.

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, None] = "a9b0c1d2e3f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


NOTIFICATION_CATEGORIES = (
    "application_prepared",
    "application_submitted",
    "manual_action_required",
    "new_matching_jobs",
)
NOTIFICATION_STATUSES = ("pending", "sent", "failed", "suppressed")


def category_check() -> str:
    quoted = ", ".join(f"'{v}'" for v in NOTIFICATION_CATEGORIES)
    return f"category IN ({quoted})"


def status_check() -> str:
    quoted = ", ".join(f"'{v}'" for v in NOTIFICATION_STATUSES)
    return f"status IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "notifications",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column(
            "channel",
            sa.String(length=20),
            server_default="email",
            nullable=False,
        ),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("subject", sa.String(length=300), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("related_job_id", sa.Integer(), nullable=True),
        sa.Column("dedupe_key", sa.String(length=200), nullable=True),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "sent_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.CheckConstraint(
            category_check(),
            name="ck_notifications_category",
        ),
        sa.CheckConstraint(
            status_check(),
            name="ck_notifications_status",
        ),
        sa.ForeignKeyConstraint(
            ["related_job_id"],
            ["normalized_jobs.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "dedupe_key",
            name="uq_notifications_dedupe_key",
        ),
    )
    op.create_index(
        "ix_notifications_category",
        "notifications",
        ["category"],
    )
    op.create_index(
        "ix_notifications_status",
        "notifications",
        ["status"],
    )
    op.create_index(
        "ix_notifications_related_job_id",
        "notifications",
        ["related_job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_notifications_related_job_id",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_status",
        table_name="notifications",
    )
    op.drop_index(
        "ix_notifications_category",
        table_name="notifications",
    )
    op.drop_table("notifications")
