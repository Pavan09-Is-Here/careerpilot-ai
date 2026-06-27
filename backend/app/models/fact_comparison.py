from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


class FactComparisonRun(Base):
    __tablename__ = "fact_comparison_runs"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    document_id: Mapped[int] = mapped_column(
        ForeignKey(
            "documents.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    total_findings: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    confirmed_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    mismatch_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    missing_verified_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    unverified_claim_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    manual_review_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    comparison_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    is_latest_successful: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )


class FactComparisonFinding(Base):
    __tablename__ = "fact_comparison_findings"
    __table_args__ = (
        UniqueConstraint(
            "comparison_run_id",
            "dedupe_key",
            name="uq_fact_comparison_finding_run_dedupe",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    comparison_run_id: Mapped[int] = mapped_column(
        ForeignKey(
            "fact_comparison_runs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    document_section_id: Mapped[int | None] = mapped_column(
        ForeignKey(
            "cv_sections.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    sort_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    verified_entity_id: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    field_name: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    finding_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    cv_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    verified_value: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    normalized_cv_value: Mapped[str | None] = mapped_column(
        String(600),
        nullable=True,
    )

    normalized_verified_value: Mapped[str | None] = mapped_column(
        String(600),
        nullable=True,
    )

    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    explanation: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    requires_manual_review: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    dedupe_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )
