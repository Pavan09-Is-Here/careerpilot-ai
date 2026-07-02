"""Add Phase 6 job tailored CV links.

Revision ID: a3b4c5d6e7f8
Revises: f2a3b4c5d6e7
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "f2a3b4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "job_tailored_cvs",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column("cv_version_id", sa.Integer(), nullable=False),
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
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["normalized_jobs.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["cv_version_id"],
            ["cv_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            name="uq_job_tailored_cvs_job_id",
        ),
    )
    op.create_index(
        "ix_job_tailored_cvs_job_id",
        "job_tailored_cvs",
        ["job_id"],
    )
    op.create_index(
        "ix_job_tailored_cvs_cv_version_id",
        "job_tailored_cvs",
        ["cv_version_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_tailored_cvs_cv_version_id",
        table_name="job_tailored_cvs",
    )
    op.drop_index(
        "ix_job_tailored_cvs_job_id",
        table_name="job_tailored_cvs",
    )
    op.drop_table("job_tailored_cvs")
