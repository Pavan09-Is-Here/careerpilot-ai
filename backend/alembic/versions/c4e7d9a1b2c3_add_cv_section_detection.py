"""add cv section detection

Revision ID: c4e7d9a1b2c3
Revises: d8e9f0a1b2c3
Create Date: 2026-06-26 18:31:49.781760

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e7d9a1b2c3"
down_revision: Union[str, Sequence[str], None] = "d8e9f0a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "documents",
        sa.Column(
            "section_detection_status",
            sa.String(length=50),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "documents",
        sa.Column("section_detection_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "documents",
        sa.Column(
            "section_detected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "section_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "documents",
        sa.Column(
            "section_detection_method",
            sa.String(length=100),
            nullable=True,
        ),
    )

    op.create_table(
        "cv_sections",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("section_order", sa.Integer(), nullable=False),
        sa.Column("section_type", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("detection_method", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["documents.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "document_id",
            "section_type",
            "start_char",
            name="uq_cv_section_document_type_start",
        ),
    )
    op.create_index(
        op.f("ix_cv_sections_document_id"),
        "cv_sections",
        ["document_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_cv_sections_document_id"),
        table_name="cv_sections",
    )
    op.drop_table("cv_sections")
    op.drop_column("documents", "section_detection_method")
    op.drop_column("documents", "section_count")
    op.drop_column("documents", "section_detected_at")
    op.drop_column("documents", "section_detection_error")
    op.drop_column("documents", "section_detection_status")
