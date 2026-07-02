"""Add Phase 4.5 saved jobs and review workflow.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, None] = "d0e1f2a3b4c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


SAVED_JOB_REVIEW_STATUSES = (
    "saved",
    "shortlisted",
    "dismissed",
    "archived",
)


def upgrade() -> None:
    op.create_table(
        "saved_jobs",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "review_status",
            sa.String(length=50),
            server_default="saved",
            nullable=False,
        ),
        sa.Column("notes", sa.String(length=2000), nullable=True),
        sa.Column(
            "status_changed_at",
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
            enum_check("review_status", SAVED_JOB_REVIEW_STATUSES),
            name="ck_saved_jobs_review_status",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["normalized_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            name="uq_saved_jobs_job_id",
        ),
    )
    op.create_index(
        "ix_saved_jobs_job_id",
        "saved_jobs",
        ["job_id"],
    )
    op.create_index(
        "ix_saved_jobs_review_status",
        "saved_jobs",
        ["review_status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_saved_jobs_review_status",
        table_name="saved_jobs",
    )
    op.drop_index(
        "ix_saved_jobs_job_id",
        table_name="saved_jobs",
    )
    op.drop_table("saved_jobs")
