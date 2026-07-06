from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class JobTailoredCV(Base):
    """Link between a job and one candidate's current tailored CV
    version. Each candidate profile may have its own tailored CV for
    the same job; ownership is enforced per (job, profile)."""

    __tablename__ = "job_tailored_cvs"
    __table_args__ = (
        UniqueConstraint(
            "job_id",
            "candidate_profile_id",
            name="uq_job_tailored_cvs_job_profile",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    job_id: Mapped[int] = mapped_column(
        ForeignKey(
            "normalized_jobs.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
        index=True,
    )

    # Nullable for pre-multi-tenant rows; the migration backfills it
    # from the linked CV version's owner and code always sets it.
    candidate_profile_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "candidate_profiles.id",
            ondelete="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    cv_version_id: Mapped[int] = mapped_column(
        ForeignKey(
            "cv_versions.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
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
