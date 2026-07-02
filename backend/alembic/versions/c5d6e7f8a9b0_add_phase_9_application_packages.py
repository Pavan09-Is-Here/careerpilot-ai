"""Add Phase 9 application preparation packages.

Revision ID: c5d6e7f8a9b0
Revises: b4c5d6e7f8a9
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, None] = "b4c5d6e7f8a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPLICATION_PACKAGE_READINESS_STATUSES = (
    "ready_for_automatic_application",
    "needs_user_review",
    "blocked_by_missing_information",
    "blocked_by_captcha",
    "blocked_by_mfa",
    "blocked_by_assessment",
    "not_eligible",
)


def readiness_check() -> str:
    quoted = ", ".join(
        f"'{value}'"
        for value in APPLICATION_PACKAGE_READINESS_STATUSES
    )
    return f"readiness_status IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "application_packages",
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
            "readiness_status",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column("cover_letter_text", sa.Text(), nullable=True),
        sa.Column("blockers", sa.JSON(), nullable=False),
        sa.Column("risk_warnings", sa.JSON(), nullable=False),
        sa.Column("missing_items", sa.JSON(), nullable=False),
        sa.Column(
            "user_confirmed",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column(
            "assembly_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "prepared_at",
            sa.DateTime(timezone=True),
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
            readiness_check(),
            name="ck_application_packages_readiness_status",
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            name="uq_application_packages_job_id",
        ),
    )
    op.create_index(
        "ix_application_packages_job_id",
        "application_packages",
        ["job_id"],
    )
    op.create_index(
        "ix_application_packages_candidate_profile_id",
        "application_packages",
        ["candidate_profile_id"],
    )
    op.create_index(
        "ix_application_packages_readiness_status",
        "application_packages",
        ["readiness_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_application_packages_readiness_status",
        table_name="application_packages",
    )
    op.drop_index(
        "ix_application_packages_candidate_profile_id",
        table_name="application_packages",
    )
    op.drop_index(
        "ix_application_packages_job_id",
        table_name="application_packages",
    )
    op.drop_table("application_packages")
