from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


APPLICATION_RUN_STATUSES = (
    "paused_for_gate",
    "submitted",
    "cancelled",
    "failed",
)

# Non-terminal statuses; only one active run may exist per job.
ACTIVE_RUN_STATUSES = ("paused_for_gate",)


class ApplicationRun(Base):
    """Human-in-the-loop browser-assisted application workflow.

    This is an assist workflow, not an autonomous agent. It maps
    application form fields to verified vault data, and enforces
    mandatory safety pauses for CAPTCHA, MFA, assessments, legal
    declarations, and the irreversible submission step. The tool
    never bypasses site protections and never submits on its own —
    the candidate performs the submission and records the resulting
    confirmation number. No candidate information is fabricated.
    """

    __tablename__ = "application_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey(
            "normalized_jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    candidate_profile_id: Mapped[int] = mapped_column(
        ForeignKey(
            "candidate_profiles.id",
            ondelete="CASCADE",
        ),
        default=1,
        nullable=False,
        index=True,
    )

    application_package_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "application_packages.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    pause_reason: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    gates: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    fill_plan: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    manual_fields: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    confirmation_number: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    driver: Mapped[str] = mapped_column(
        String(50),
        default="manual_assist",
        nullable=False,
    )

    workflow_version: Mapped[str] = mapped_column(
        String(100),
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

    __table_args__ = (
        CheckConstraint(
            "status IN ("
            + ", ".join(
                f"'{value}'" for value in APPLICATION_RUN_STATUSES
            )
            + ")",
            name="ck_application_runs_status",
        ),
        UniqueConstraint(
            "job_id",
            "created_at",
            name="uq_application_runs_job_created",
        ),
    )
