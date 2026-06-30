"""Add verified master CV generation artifacts.

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("cv_versions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "generation_key",
                sa.String(length=128),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "generation_version",
                sa.String(length=100),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "source_summary",
                sa.JSON(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "generated_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )

    op.create_index(
        "uq_cv_versions_generation_key",
        "cv_versions",
        [
            "candidate_profile_id",
            "parent_version_id",
            "version_type",
            "generation_key",
        ],
        unique=True,
    )

    op.create_table(
        "cv_version_artifacts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cv_version_id", sa.Integer(), nullable=False),
        sa.Column("artifact_type", sa.String(length=20), nullable=False),
        sa.Column("mime_type", sa.String(length=150), nullable=False),
        sa.Column("safe_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_path", sa.String(length=500), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("renderer_version", sa.String(length=100), nullable=False),
        sa.Column("content_version", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "artifact_type IN ('docx', 'pdf')",
            name="ck_cv_version_artifacts_artifact_type",
        ),
        sa.ForeignKeyConstraint(
            ["cv_version_id"],
            ["cv_versions.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cv_version_id",
            "artifact_type",
            name="uq_cv_version_artifacts_version_type",
        ),
        sa.UniqueConstraint("storage_path"),
    )
    op.create_index(
        "ix_cv_version_artifacts_cv_version_id",
        "cv_version_artifacts",
        ["cv_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_cv_version_artifacts_artifact_type",
        "cv_version_artifacts",
        ["artifact_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_cv_version_artifacts_artifact_type",
        table_name="cv_version_artifacts",
    )
    op.drop_index(
        "ix_cv_version_artifacts_cv_version_id",
        table_name="cv_version_artifacts",
    )
    op.drop_table("cv_version_artifacts")

    op.drop_index(
        "uq_cv_versions_generation_key",
        table_name="cv_versions",
    )

    with op.batch_alter_table("cv_versions") as batch_op:
        batch_op.drop_column("generated_at")
        batch_op.drop_column("source_summary")
        batch_op.drop_column("generation_version")
        batch_op.drop_column("generation_key")
