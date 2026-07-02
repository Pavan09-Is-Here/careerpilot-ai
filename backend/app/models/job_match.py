from datetime import datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


JOB_MATCH_ELIGIBILITY_STATUSES = (
    "eligible",
    "conditionally_eligible",
    "ineligible",
)


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


def score_check(column_name: str) -> str:
    return (
        f"{column_name} IS NULL OR "
        f"({column_name} >= 0 AND {column_name} <= 100)"
    )


class JobMatch(Base):
    """Deterministic, explainable job match assessment.

    Component scores are NULL when the vault or the job lacks the
    data to evaluate them — missing data is flagged for review,
    never counted against the candidate.
    """

    __tablename__ = "job_matches"
    __table_args__ = (
        CheckConstraint(
            enum_check(
                "eligibility_status",
                JOB_MATCH_ELIGIBILITY_STATUSES,
            ),
            name="ck_job_matches_eligibility_status",
        ),
        CheckConstraint(
            score_check("match_score"),
            name="ck_job_matches_match_score_range",
        ),
        CheckConstraint(
            score_check("skills_match"),
            name="ck_job_matches_skills_range",
        ),
        CheckConstraint(
            score_check("experience_match"),
            name="ck_job_matches_experience_range",
        ),
        CheckConstraint(
            score_check("education_match"),
            name="ck_job_matches_education_range",
        ),
        CheckConstraint(
            score_check("projects_match"),
            name="ck_job_matches_projects_range",
        ),
        CheckConstraint(
            score_check("location_match"),
            name="ck_job_matches_location_range",
        ),
        CheckConstraint(
            score_check("work_auth_match"),
            name="ck_job_matches_work_auth_range",
        ),
        UniqueConstraint(
            "job_id",
            "candidate_profile_id",
            name="uq_job_matches_job_profile",
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
        nullable=False,
        index=True,
    )

    match_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    skills_match: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    experience_match: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    education_match: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    projects_match: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    location_match: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    work_auth_match: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    eligibility_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    blocker_reason: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    algorithm_version: Mapped[str] = mapped_column(
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
