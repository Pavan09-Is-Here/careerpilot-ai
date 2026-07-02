from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


INGESTION_RUN_STATUSES = (
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
)


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"
    __table_args__ = (
        CheckConstraint(
            enum_check("run_status", INGESTION_RUN_STATUSES),
            name="ck_ingestion_runs_run_status",
        ),
        CheckConstraint(
            "jobs_discovered >= 0",
            name="ck_ingestion_runs_jobs_discovered_non_negative",
        ),
        CheckConstraint(
            "jobs_updated >= 0",
            name="ck_ingestion_runs_jobs_updated_non_negative",
        ),
        CheckConstraint(
            "snapshots_recorded >= 0",
            name="ck_ingestion_runs_snapshots_recorded_non_negative",
        ),
        CheckConstraint(
            "finished_at IS NULL OR started_at IS NOT NULL",
            name="ck_ingestion_runs_finish_requires_start",
        ),
        Index(
            "ix_ingestion_runs_source_created",
            "job_source_id",
            "created_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    job_source_id: Mapped[int] = mapped_column(
        ForeignKey(
            "job_sources.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    run_status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        server_default="pending",
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    failure_summary: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    jobs_discovered: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    jobs_updated: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    snapshots_recorded: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        onupdate=current_utc_time,
        nullable=False,
    )


class SourceSnapshot(Base):
    __tablename__ = "source_snapshots"
    __table_args__ = (
        CheckConstraint(
            "length(content_hash) = 64",
            name="ck_source_snapshots_content_hash_length",
        ),
        CheckConstraint(
            "payload_size_bytes >= 0",
            name="ck_source_snapshots_payload_size_non_negative",
        ),
        CheckConstraint(
            "expires_at > fetched_at",
            name="ck_source_snapshots_expiry_after_fetch",
        ),
        Index(
            "ix_source_snapshots_run_fetched",
            "ingestion_run_id",
            "fetched_at",
            "id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    ingestion_run_id: Mapped[int] = mapped_column(
        ForeignKey(
            "ingestion_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    job_source_id: Mapped[int] = mapped_column(
        ForeignKey(
            "job_sources.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    payload_size_bytes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    payload_media_type: Mapped[str] = mapped_column(
        String(100),
        default="application/json",
        server_default="application/json",
        nullable=False,
    )

    storage_reference: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )
