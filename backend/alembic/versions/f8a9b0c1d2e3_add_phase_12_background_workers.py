"""Add Phase 12 background worker runs and audit log.

Revision ID: f8a9b0c1d2e3
Revises: e7f8a9b0c1d2
Create Date: 2026-07-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f8a9b0c1d2e3"
down_revision: Union[str, None] = "e7f8a9b0c1d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


WORKER_RUN_STATUSES = (
    "running",
    "success",
    "partial",
    "failed",
    "skipped",
)

AUDIT_LEVELS = ("info", "warning", "error")


def status_check() -> str:
    quoted = ", ".join(f"'{value}'" for value in WORKER_RUN_STATUSES)
    return f"status IN ({quoted})"


def level_check() -> str:
    quoted = ", ".join(f"'{value}'" for value in AUDIT_LEVELS)
    return f"level IN ({quoted})"


def upgrade() -> None:
    op.create_table(
        "worker_runs",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("worker_name", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("run_date", sa.Date(), nullable=False),
        sa.Column(
            "items_processed",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "items_succeeded",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "items_failed",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "retries",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column("error", sa.String(length=1000), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "finished_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            status_check(),
            name="ck_worker_runs_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_worker_runs_worker_name",
        "worker_runs",
        ["worker_name"],
    )
    op.create_index(
        "ix_worker_runs_status",
        "worker_runs",
        ["status"],
    )
    op.create_index(
        "ix_worker_runs_run_date",
        "worker_runs",
        ["run_date"],
    )

    op.create_table(
        "audit_log_entries",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("worker_run_id", sa.Integer(), nullable=True),
        sa.Column("worker_name", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column(
            "level",
            sa.String(length=20),
            server_default="info",
            nullable=False,
        ),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.CheckConstraint(
            level_check(),
            name="ck_audit_log_entries_level",
        ),
        sa.ForeignKeyConstraint(
            ["worker_run_id"],
            ["worker_runs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_audit_log_entries_worker_run_id",
        "audit_log_entries",
        ["worker_run_id"],
    )
    op.create_index(
        "ix_audit_log_entries_worker_name",
        "audit_log_entries",
        ["worker_name"],
    )
    op.create_index(
        "ix_audit_log_entries_level",
        "audit_log_entries",
        ["level"],
    )
    op.create_index(
        "ix_audit_log_entries_created_at",
        "audit_log_entries",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_audit_log_entries_created_at",
        table_name="audit_log_entries",
    )
    op.drop_index(
        "ix_audit_log_entries_level",
        table_name="audit_log_entries",
    )
    op.drop_index(
        "ix_audit_log_entries_worker_name",
        table_name="audit_log_entries",
    )
    op.drop_index(
        "ix_audit_log_entries_worker_run_id",
        table_name="audit_log_entries",
    )
    op.drop_table("audit_log_entries")

    op.drop_index("ix_worker_runs_run_date", table_name="worker_runs")
    op.drop_index("ix_worker_runs_status", table_name="worker_runs")
    op.drop_index(
        "ix_worker_runs_worker_name",
        table_name="worker_runs",
    )
    op.drop_table("worker_runs")
