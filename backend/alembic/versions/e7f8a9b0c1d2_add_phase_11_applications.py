"""Add Phase 11 application tracking records.

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPLICATION_STATUSES = (
    "discovered",
    "analyzing",
    "not_eligible",
    "matched",
    "cv_generated",
    "needs_review",
    "ready_to_apply",
    "applying",
    "blocked",
    "submitted",
    "interview",
    "rejected",
    "offer",
    "withdrawn",
)

APPLICATION_INTERVIEW_STAGES = (
    "phone_screen",
    "technical",
    "onsite",
    "final",
    "other",
)


def status_check() -> str:
    quoted = ", ".join(f"'{value}'" for value in APPLICATION_STATUSES)
    return f"status IN ({quoted})"


def interview_stage_check() -> str:
    quoted = ", ".join(
        f"'{value}'" for value in APPLICATION_INTERVIEW_STAGES
    )
    return f"interview_stage IS NULL OR interview_stage IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "applications",
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
        sa.Column("cv_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "applied_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "confirmation_number",
            sa.String(length=200),
            nullable=True,
        ),
        sa.Column(
            "interview_date",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "interview_stage",
            sa.String(length=50),
            nullable=True,
        ),
        sa.Column("offer_details", sa.Text(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("outcome_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.JSON(), nullable=False),
        sa.Column("follow_ups", sa.JSON(), nullable=False),
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
            name="ck_applications_status",
        ),
        sa.CheckConstraint(
            interview_stage_check(),
            name="ck_applications_interview_stage",
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
            ["cv_id"],
            ["cv_versions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            name="uq_applications_job_id",
        ),
    )
    op.create_index(
        "ix_applications_job_id",
        "applications",
        ["job_id"],
    )
    op.create_index(
        "ix_applications_candidate_profile_id",
        "applications",
        ["candidate_profile_id"],
    )
    op.create_index(
        "ix_applications_cv_id",
        "applications",
        ["cv_id"],
    )
    op.create_index(
        "ix_applications_status",
        "applications",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_cv_id", table_name="applications")
    op.drop_index(
        "ix_applications_candidate_profile_id",
        table_name="applications",
    )
    op.drop_index("ix_applications_job_id", table_name="applications")
    op.drop_table("applications")
