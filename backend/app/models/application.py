from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Date,
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


APPLICATION_STATUSES = (
    "discovered",
    "analyzing",
    "not_eligible",
    "matched",
    "cv_generated",
    "needs_review",
    "ready_to_apply",
    "applying",
    "blocked",
    "submitted",
    "interview",
    "rejected",
    "offer",
    "withdrawn",
)

APPLICATION_INTERVIEW_STAGES = (
    "phone_screen",
    "technical",
    "onsite",
    "final",
    "other",
)


class Application(Base):
    """Tracking record for the candidate's application to one job.

    Captures pipeline status, submission confirmation, interview and
    outcome details, notes, and follow-ups. Statuses progress along a
    validated set of transitions. This record never fabricates
    candidate information — it tracks facts the candidate supplies or
    that the pipeline has already produced.
    """

    __tablename__ = "applications"

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

    cv_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "cv_versions.id",
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

    applied_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    confirmation_number: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    interview_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    interview_stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    offer_details: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    outcome_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    notes: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    follow_ups: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        default=list,
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
            + ", ".join(f"'{value}'" for value in APPLICATION_STATUSES)
            + ")",
            name="ck_applications_status",
        ),
        CheckConstraint(
            "interview_stage IS NULL OR interview_stage IN ("
            + ", ".join(
                f"'{value}'"
                for value in APPLICATION_INTERVIEW_STAGES
            )
            + ")",
            name="ck_applications_interview_stage",
        ),
        UniqueConstraint(
            "job_id",
            name="uq_applications_job_id",
        ),
    )
