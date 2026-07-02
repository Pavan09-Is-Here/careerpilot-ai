"""Add Phase 4.2 ingestion runs and source snapshots.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


INGESTION_RUN_STATUSES = (
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
)


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("job_source_id", sa.Integer(), nullable=False),
        sa.Column(
            "run_status",
            sa.String(length=50),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "failure_summary",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "jobs_discovered",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "jobs_updated",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "snapshots_recorded",
            sa.Integer(),
            server_default="0",
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
            enum_check("run_status", INGESTION_RUN_STATUSES),
            name="ck_ingestion_runs_run_status",
        ),
        sa.CheckConstraint(
            "jobs_discovered >= 0",
            name="ck_ingestion_runs_jobs_discovered_non_negative",
        ),
        sa.CheckConstraint(
            "jobs_updated >= 0",
            name="ck_ingestion_runs_jobs_updated_non_negative",
        ),
        sa.CheckConstraint(
            "snapshots_recorded >= 0",
            name="ck_ingestion_runs_snapshots_recorded_non_negative",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR started_at IS NOT NULL",
            name="ck_ingestion_runs_finish_requires_start",
        ),
        sa.ForeignKeyConstraint(
            ["job_source_id"],
            ["job_sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ingestion_runs_job_source_id",
        "ingestion_runs",
        ["job_source_id"],
    )
    op.create_index(
        "ix_ingestion_runs_run_status",
        "ingestion_runs",
        ["run_status"],
    )
    op.create_index(
        "ix_ingestion_runs_source_created",
        "ingestion_runs",
        ["job_source_id", "created_at", "id"],
    )

    op.create_table(
        "source_snapshots",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("ingestion_run_id", sa.Integer(), nullable=False),
        sa.Column("job_source_id", sa.Integer(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("payload_size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "payload_media_type",
            sa.String(length=100),
            server_default="application/json",
            nullable=False,
        ),
        sa.Column(
            "storage_reference",
            sa.String(length=300),
            nullable=True,
        ),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64",
            name="ck_source_snapshots_content_hash_length",
        ),
        sa.CheckConstraint(
            "payload_size_bytes >= 0",
            name="ck_source_snapshots_payload_size_non_negative",
        ),
        sa.CheckConstraint(
            "expires_at > fetched_at",
            name="ck_source_snapshots_expiry_after_fetch",
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["ingestion_runs.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_source_id"],
            ["job_sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_source_snapshots_ingestion_run_id",
        "source_snapshots",
        ["ingestion_run_id"],
    )
    op.create_index(
        "ix_source_snapshots_job_source_id",
        "source_snapshots",
        ["job_source_id"],
    )
    op.create_index(
        "ix_source_snapshots_content_hash",
        "source_snapshots",
        ["content_hash"],
    )
    op.create_index(
        "ix_source_snapshots_expires_at",
        "source_snapshots",
        ["expires_at"],
    )
    op.create_index(
        "ix_source_snapshots_run_fetched",
        "source_snapshots",
        ["ingestion_run_id", "fetched_at", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_source_snapshots_run_fetched",
        table_name="source_snapshots",
    )
    op.drop_index(
        "ix_source_snapshots_expires_at",
        table_name="source_snapshots",
    )
    op.drop_index(
        "ix_source_snapshots_content_hash",
        table_name="source_snapshots",
    )
    op.drop_index(
        "ix_source_snapshots_job_source_id",
        table_name="source_snapshots",
    )
    op.drop_index(
        "ix_source_snapshots_ingestion_run_id",
        table_name="source_snapshots",
    )
    op.drop_table("source_snapshots")

    op.drop_index(
        "ix_ingestion_runs_source_created",
        table_name="ingestion_runs",
    )
    op.drop_index(
        "ix_ingestion_runs_run_status",
        table_name="ingestion_runs",
    )
    op.drop_index(
        "ix_ingestion_runs_job_source_id",
        table_name="ingestion_runs",
    )
    op.drop_table("ingestion_runs")
