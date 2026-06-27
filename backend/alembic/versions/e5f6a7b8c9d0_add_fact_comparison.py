"""add fact comparison

Revision ID: e5f6a7b8c9d0
Revises: c4e7d9a1b2c3
Create Date: 2026-06-27 13:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "c4e7d9a1b2c3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "fact_comparison_runs",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "total_findings",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "confirmed_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "mismatch_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "missing_verified_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "unverified_claim_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "manual_review_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "comparison_version",
            sa.String(length=100),
            nullable=False,
        ),
        sa.Column(
            "is_latest_successful",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
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
    )
    op.create_index(
        op.f("ix_fact_comparison_runs_document_id"),
        "fact_comparison_runs",
        ["document_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fact_comparison_runs_is_latest_successful"),
        "fact_comparison_runs",
        ["is_latest_successful"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fact_comparison_runs_status"),
        "fact_comparison_runs",
        ["status"],
        unique=False,
    )

    op.create_table(
        "fact_comparison_findings",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("comparison_run_id", sa.Integer(), nullable=False),
        sa.Column("document_section_id", sa.Integer(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("verified_entity_id", sa.Integer(), nullable=True),
        sa.Column("field_name", sa.String(length=100), nullable=True),
        sa.Column("finding_type", sa.String(length=50), nullable=False),
        sa.Column("cv_value", sa.Text(), nullable=True),
        sa.Column("verified_value", sa.Text(), nullable=True),
        sa.Column(
            "normalized_cv_value",
            sa.String(length=600),
            nullable=True,
        ),
        sa.Column(
            "normalized_verified_value",
            sa.String(length=600),
            nullable=True,
        ),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(length=50), nullable=False),
        sa.Column("explanation", sa.String(length=500), nullable=False),
        sa.Column(
            "requires_manual_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("dedupe_key", sa.String(length=128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["comparison_run_id"],
            ["fact_comparison_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["document_section_id"],
            ["cv_sections.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comparison_run_id",
            "dedupe_key",
            name="uq_fact_comparison_finding_run_dedupe",
        ),
    )
    op.create_index(
        op.f("ix_fact_comparison_findings_comparison_run_id"),
        "fact_comparison_findings",
        ["comparison_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fact_comparison_findings_document_section_id"),
        "fact_comparison_findings",
        ["document_section_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fact_comparison_findings_entity_type"),
        "fact_comparison_findings",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_fact_comparison_findings_finding_type"),
        "fact_comparison_findings",
        ["finding_type"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        op.f("ix_fact_comparison_findings_finding_type"),
        table_name="fact_comparison_findings",
    )
    op.drop_index(
        op.f("ix_fact_comparison_findings_entity_type"),
        table_name="fact_comparison_findings",
    )
    op.drop_index(
        op.f("ix_fact_comparison_findings_document_section_id"),
        table_name="fact_comparison_findings",
    )
    op.drop_index(
        op.f("ix_fact_comparison_findings_comparison_run_id"),
        table_name="fact_comparison_findings",
    )
    op.drop_table("fact_comparison_findings")

    op.drop_index(
        op.f("ix_fact_comparison_runs_status"),
        table_name="fact_comparison_runs",
    )
    op.drop_index(
        op.f("ix_fact_comparison_runs_is_latest_successful"),
        table_name="fact_comparison_runs",
    )
    op.drop_index(
        op.f("ix_fact_comparison_runs_document_id"),
        table_name="fact_comparison_runs",
    )
    op.drop_table("fact_comparison_runs")
