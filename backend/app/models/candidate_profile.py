from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    # CareerPilot is initially for one user, so the profile uses ID 1.
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        default=1,
    )

    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    location: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    professional_title: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    professional_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    linkedin_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    github_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    portfolio_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    work_authorization: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True,
    )

    requires_sponsorship: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    willing_to_relocate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    preferred_work_modes: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    target_roles: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    preferred_locations: Mapped[list[str]] = mapped_column(
        JSON,
        default=list,
        nullable=False,
    )

    minimum_salary: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    salary_currency: Mapped[str] = mapped_column(
        String(10),
        default="GBP",
        nullable=False,
    )

    minimum_match_score: Mapped[int] = mapped_column(
        Integer,
        default=85,
        nullable=False,
    )

    auto_apply_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    facts_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
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