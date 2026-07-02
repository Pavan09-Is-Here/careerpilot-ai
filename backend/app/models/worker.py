from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


WORKER_NAMES = (
    "job_discovery",
    "job_analysis",
    "application_preparation",
    "expiry_checker",
    "auto_apply_pipeline",
)

WORKER_RUN_STATUSES = (
    "running",
    "success",
    "partial",
    "failed",
    "skipped",
)

AUDIT_LEVELS = (
    "info",
    "warning",
    "error",
)


class WorkerRun(Base):
    """Audit record for one bounded execution of a background worker.

    Workers run as bounded, on-demand cycles (never as always-on
    daemons and never submitting applications). Each run records its
    outcome, counts, and retry total for health monitoring and daily
    rate limiting.
    """

    __tablename__ = "worker_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    worker_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    run_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )

    items_processed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    items_succeeded: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    items_failed: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    retries: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            + ", ".join(f"'{value}'" for value in WORKER_RUN_STATUSES)
            + ")",
            name="ck_worker_runs_status",
        ),
    )


class AuditLogEntry(Base):
    """A single audited action taken by a background worker.

    Every automated action is recorded here for transparency. No
    action ever submits an application; submission always requires a
    deliberate human step.
    """

    __tablename__ = "audit_log_entries"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    worker_run_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "worker_runs.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    worker_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    entity_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    level: Mapped[str] = mapped_column(
        String(20),
        default="info",
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
        index=True,
    )

    __table_args__ = (
        CheckConstraint(
            "level IN ("
            + ", ".join(f"'{value}'" for value in AUDIT_LEVELS)
            + ")",
            name="ck_audit_log_entries_level",
        ),
    )
