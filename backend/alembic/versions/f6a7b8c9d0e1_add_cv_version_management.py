"""Add CV version management.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, None] = "e5f6a7b8c9d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cv_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("candidate_profile_id", sa.Integer(), nullable=False),
        sa.Column("source_document_id", sa.Integer(), nullable=True),
        sa.Column("parent_version_id", sa.Integer(), nullable=True),
        sa.Column("version_type", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("display_name", sa.String(length=250), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("job_reference", sa.String(length=250), nullable=True),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column("storage_path", sa.String(length=500), nullable=True),
        sa.Column("mime_type", sa.String(length=150), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("sha256", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "version_type IN ('original', 'parsed', 'verified_master', "
            "'tailored')",
            name="ck_cv_versions_version_type",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'ready', 'archived', 'failed')",
            name="ck_cv_versions_status",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_profile_id"],
            ["candidate_profiles.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["parent_version_id"],
            ["cv_versions.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["source_document_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_document_id",
            name="uq_cv_versions_source_document_id",
        ),
    )
    op.create_index(
        "ix_cv_versions_candidate_profile_id",
        "cv_versions",
        ["candidate_profile_id"],
        unique=False,
    )
    op.create_index(
        "ix_cv_versions_source_document_id",
        "cv_versions",
        ["source_document_id"],
        unique=False,
    )
    op.create_index(
        "ix_cv_versions_parent_version_id",
        "cv_versions",
        ["parent_version_id"],
        unique=False,
    )
    op.create_index(
        "ix_cv_versions_version_type",
        "cv_versions",
        ["version_type"],
        unique=False,
    )
    op.create_index(
        "ix_cv_versions_status",
        "cv_versions",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_cv_versions_is_primary",
        "cv_versions",
        ["is_primary"],
        unique=False,
    )
    op.create_index(
        "ix_cv_versions_candidate_type",
        "cv_versions",
        ["candidate_profile_id", "version_type"],
        unique=False,
    )
    op.create_index(
        "uq_cv_versions_primary_per_type",
        "cv_versions",
        ["candidate_profile_id", "version_type"],
        unique=True,
        sqlite_where=sa.text("is_primary = 1"),
        postgresql_where=sa.text("is_primary = true"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_cv_versions_primary_per_type",
        table_name="cv_versions",
        sqlite_where=sa.text("is_primary = 1"),
    )
    op.drop_index(
        "ix_cv_versions_candidate_type",
        table_name="cv_versions",
    )
    op.drop_index("ix_cv_versions_is_primary", table_name="cv_versions")
    op.drop_index("ix_cv_versions_status", table_name="cv_versions")
    op.drop_index("ix_cv_versions_version_type", table_name="cv_versions")
    op.drop_index(
        "ix_cv_versions_parent_version_id",
        table_name="cv_versions",
    )
    op.drop_index(
        "ix_cv_versions_source_document_id",
        table_name="cv_versions",
    )
    op.drop_index(
        "ix_cv_versions_candidate_profile_id",
        table_name="cv_versions",
    )
    op.drop_table("cv_versions")
