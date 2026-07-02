"""Add Phase 10 browser-assisted application runs.

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, None] = "c5d6e7f8a9b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPLICATION_RUN_STATUSES = (
    "paused_for_gate",
    "submitted",
    "cancelled",
    "failed",
)


def status_check() -> str:
    quoted = ", ".join(
        f"'{value}'" for value in APPLICATION_RUN_STATUSES
    )
    return f"status IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "application_runs",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "candidate_profile_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "application_package_id",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("pause_reason", sa.String(length=100), nullable=True),
        sa.Column("gates", sa.JSON(), nullable=False),
        sa.Column("fill_plan", sa.JSON(), nullable=False),
        sa.Column("manual_fields", sa.JSON(), nullable=False),
        sa.Column(
            "confirmation_number",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "driver",
            sa.String(length=50),
            server_default="manual_assist",
            nullable=False,
        ),
        sa.Column(
            "workflow_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            status_check(),
            name="ck_application_runs_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["normalized_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["application_package_id"],
            ["application_packages.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "created_at",
            name="uq_application_runs_job_created",
        ),
    )
    op.create_index(
        "ix_application_runs_job_id",
        "application_runs",
        ["job_id"],
    )
    op.create_index(
        "ix_application_runs_candidate_profile_id",
        "application_runs",
        ["candidate_profile_id"],
    )
    op.create_index(
        "ix_application_runs_application_package_id",
        "application_runs",
        ["application_package_id"],
    )
    op.create_index(
        "ix_application_runs_status",
        "application_runs",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_runs_status",
        table_name="application_runs",
    )
    op.drop_index(
        "ix_application_runs_application_package_id",
        table_name="application_runs",
    )
    op.drop_index(
        "ix_application_runs_candidate_profile_id",
        table_name="application_runs",
    )
    op.drop_index(
        "ix_application_runs_job_id",
        table_name="application_runs",
    )
    op.drop_table("application_runs")
