from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
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


APPLICATION_PACKAGE_READINESS_STATUSES = (
    "ready_for_automatic_application",
    "needs_user_review",
    "blocked_by_missing_information",
    "blocked_by_captcha",
    "blocked_by_mfa",
    "blocked_by_assessment",
    "not_eligible",
)


class ApplicationPackage(Base):
    """Assembled, reviewable application package for a single job.

    Combines the verified match report, tailored CV, verified
    application answers, salary guidance, and a verified-fact-only
    cover letter into one reviewable record with a deterministic
    readiness assessment. The package never fabricates candidate
    information and never marks itself ready when a safety blocker
    (CAPTCHA, MFA, assessment), a hard ineligibility, or missing
    required information is present. Confirmation and submission
    remain deliberate human actions.
    """

    __tablename__ = "application_packages"

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

    readiness_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    cover_letter_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    blockers: Mapped[list[dict[str, str]]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    risk_warnings: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    missing_items: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    user_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    user_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    assembly_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    prepared_at: Mapped[datetime] = mapped_column(
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

    __table_args__ = (
        CheckConstraint(
            "readiness_status IN ("
            + ", ".join(
                f"'{value}'"
                for value in APPLICATION_PACKAGE_READINESS_STATUSES
            )
            + ")",
            name="ck_application_packages_readiness_status",
        ),
        UniqueConstraint(
            "job_id",
            name="uq_application_packages_job_id",
        ),
    )
