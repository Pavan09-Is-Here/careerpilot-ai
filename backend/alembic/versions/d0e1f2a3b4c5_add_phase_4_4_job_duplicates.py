"""Add Phase 4.4 job duplicate links.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d0e1f2a3b4c5"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


JOB_DUPLICATE_DETECTION_METHODS = (
    "canonical_url",
    "content_hash",
)


def upgrade() -> None:
    op.create_table(
        "job_duplicates",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "duplicate_of_job_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "detection_method",
            sa.String(length=50),
            nullable=False,
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            enum_check(
                "detection_method",
                JOB_DUPLICATE_DETECTION_METHODS,
            ),
            name="ck_job_duplicates_detection_method",
        ),
        sa.CheckConstraint(
            "job_id != duplicate_of_job_id",
            name="ck_job_duplicates_distinct_jobs",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["normalized_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_job_id"],
            ["normalized_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "duplicate_of_job_id",
            "detection_method",
            name="uq_job_duplicates_pair_method",
        ),
    )
    op.create_index(
        "ix_job_duplicates_job_id",
        "job_duplicates",
        ["job_id"],
    )
    op.create_index(
        "ix_job_duplicates_duplicate_of_job_id",
        "job_duplicates",
        ["duplicate_of_job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_duplicates_duplicate_of_job_id",
        table_name="job_duplicates",
    )
    op.drop_index(
        "ix_job_duplicates_job_id",
        table_name="job_duplicates",
    )
    op.drop_table("job_duplicates")
