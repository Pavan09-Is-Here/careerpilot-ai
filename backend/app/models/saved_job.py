from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


SAVED_JOB_REVIEW_STATUSES = (
    "saved",
    "shortlisted",
    "dismissed",
    "archived",
)


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


class SavedJob(Base):
    """Candidate review record for a discovered job.

    Saved jobs restrict deletion of the underlying normalized job,
    so removed, expired, unavailable, and stale jobs remain fully
    inspectable. Records are archived, never deleted.
    """

    __tablename__ = "saved_jobs"
    __table_args__ = (
        CheckConstraint(
            enum_check("review_status", SAVED_JOB_REVIEW_STATUSES),
            name="ck_saved_jobs_review_status",
        ),
        UniqueConstraint(
            "candidate_profile_id",
            "job_id",
            name="uq_saved_jobs_profile_job",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    candidate_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "candidate_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey(
            "normalized_jobs.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    review_status: Mapped[str] = mapped_column(
        String(50),
        default="saved",
        server_default="saved",
        nullable=False,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(
        String(2000),
        nullable=True,
    )

    status_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
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
