from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


APPLICATION_ANSWER_CATEGORIES = (
    "work_authorization",
    "sponsorship",
    "availability",
    "notice_period",
    "relocation",
    "remote_preference",
    "expected_salary",
    "company_interest",
    "cover_letter",
    "other",
)


class ApplicationAnswer(Base):
    """A verified reusable answer to a recurring application question.

    Answers are grounded in verified candidate facts. Sensitive
    categories (legal declarations, demographic, health, or criminal
    questions) require explicit manual confirmation before an answer
    may be marked verified. The vault never fabricates candidate
    information; unverified answers stay clearly distinguishable.
    """

    __tablename__ = "application_answers"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
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

    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    question_label: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    manually_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    requires_manual_confirmation: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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
            "category IN ("
            + ", ".join(
                f"'{value}'" for value in APPLICATION_ANSWER_CATEGORIES
            )
            + ")",
            name="ck_application_answers_category",
        ),
        UniqueConstraint(
            "candidate_profile_id",
            "category",
            "question_label",
            name="uq_application_answers_identity",
        ),
        Index(
            "ix_application_answers_candidate_category",
            "candidate_profile_id",
            "category",
        ),
    )
