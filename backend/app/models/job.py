from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


JOB_SOURCE_CATEGORIES = (
    "provider_api",
    "job_board_api",
    "company_career_page",
    "user_supplied_url",
    "manual_reference",
)
JOB_SOURCE_PROVIDER_TYPES = (
    "none",
    "greenhouse",
    "lever",
    "ashby",
    "workable",
    "adzuna",
    "usajobs",
    "remotive",
    "arbeitnow",
    "reed",
    "generic_api",
    "company_career_page",
    "manual",
    "other",
)
JOB_SOURCE_ACCESS_MODES = (
    "metadata_only",
    "manual_import",
    "api",
    "approved_static_fetch",
)
JOB_SOURCE_REVIEW_STATUSES = (
    "not_reviewed",
    "review_required",
    "approved_for_configured_use",
    "rejected",
    "suspended",
)
JOB_REMOTE_MODES = (
    "unspecified",
    "onsite",
    "hybrid",
    "remote",
    "flexible",
)
JOB_EMPLOYMENT_TYPES = (
    "unspecified",
    "full_time",
    "part_time",
    "contract",
    "temporary",
    "internship",
    "apprenticeship",
    "volunteer",
    "per_diem",
    "other",
)
JOB_SENIORITIES = (
    "unspecified",
    "internship",
    "entry",
    "associate",
    "mid",
    "senior",
    "lead",
    "manager",
    "director",
    "executive",
    "other",
)
JOB_LIFECYCLE_STATUSES = (
    "discovered",
    "active",
    "possibly_stale",
    "expired",
    "removed",
    "unavailable",
)
JOB_COMPENSATION_PERIODS = (
    "unspecified",
    "hourly",
    "daily",
    "weekly",
    "monthly",
    "yearly",
    "one_time",
)
JOB_SKILL_REQUIREMENT_TYPES = (
    "required",
    "preferred",
    "mentioned",
)
JOB_DUPLICATE_DETECTION_METHODS = (
    "canonical_url",
    "content_hash",
)


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


class JobSource(Base):
    __tablename__ = "job_sources"
    __table_args__ = (
        CheckConstraint(
            enum_check("source_category", JOB_SOURCE_CATEGORIES),
            name="ck_job_sources_source_category",
        ),
        CheckConstraint(
            enum_check("provider_type", JOB_SOURCE_PROVIDER_TYPES),
            name="ck_job_sources_provider_type",
        ),
        CheckConstraint(
            enum_check("access_mode", JOB_SOURCE_ACCESS_MODES),
            name="ck_job_sources_access_mode",
        ),
        CheckConstraint(
            enum_check("terms_review_status", JOB_SOURCE_REVIEW_STATUSES),
            name="ck_job_sources_terms_review_status",
        ),
        CheckConstraint(
            enum_check("robots_review_status", JOB_SOURCE_REVIEW_STATUSES),
            name="ck_job_sources_robots_review_status",
        ),
        CheckConstraint(
            enum_check(
                "commercial_use_review_status",
                JOB_SOURCE_REVIEW_STATUSES,
            ),
            name="ck_job_sources_commercial_use_review_status",
        ),
        CheckConstraint(
            "configured_retention_days BETWEEN 1 AND 365",
            name="ck_job_sources_retention_days_range",
        ),
        UniqueConstraint(
            "source_key",
            name="uq_job_sources_source_key",
        ),
        Index("ix_job_sources_display_name", "display_name"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    source_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    display_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    source_category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    provider_type: Mapped[str] = mapped_column(
        String(50),
        default="none",
        server_default="none",
        nullable=False,
        index=True,
    )

    base_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
        index=True,
    )

    allowlisted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
        index=True,
    )

    access_mode: Mapped[str] = mapped_column(
        String(50),
        default="metadata_only",
        server_default="metadata_only",
        nullable=False,
        index=True,
    )

    attribution_required: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
    )

    attribution_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    attribution_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    terms_review_status: Mapped[str] = mapped_column(
        String(50),
        default="not_reviewed",
        server_default="not_reviewed",
        nullable=False,
        index=True,
    )

    terms_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    robots_review_status: Mapped[str] = mapped_column(
        String(50),
        default="not_reviewed",
        server_default="not_reviewed",
        nullable=False,
        index=True,
    )

    robots_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    manual_review_required: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("1"),
        nullable=False,
        index=True,
    )

    commercial_use_review_status: Mapped[str] = mapped_column(
        String(50),
        default="not_reviewed",
        server_default="not_reviewed",
        nullable=False,
        index=True,
    )

    server_fetch_allowed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("0"),
        nullable=False,
        index=True,
    )

    configured_retention_days: Mapped[int] = mapped_column(
        Integer,
        default=30,
        server_default=text("30"),
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


class NormalizedJob(Base):
    __tablename__ = "normalized_jobs"
    __table_args__ = (
        CheckConstraint(
            enum_check("remote_mode", JOB_REMOTE_MODES),
            name="ck_normalized_jobs_remote_mode",
        ),
        CheckConstraint(
            enum_check("employment_type", JOB_EMPLOYMENT_TYPES),
            name="ck_normalized_jobs_employment_type",
        ),
        CheckConstraint(
            enum_check("seniority", JOB_SENIORITIES),
            name="ck_normalized_jobs_seniority",
        ),
        CheckConstraint(
            enum_check("lifecycle_status", JOB_LIFECYCLE_STATUSES),
            name="ck_normalized_jobs_lifecycle_status",
        ),
        CheckConstraint(
            "length(content_hash) = 64",
            name="ck_normalized_jobs_content_hash_length",
        ),
        CheckConstraint(
            "description_text IS NULL OR length(description_text) <= 20000",
            name="ck_normalized_jobs_description_length",
        ),
        CheckConstraint(
            (
                "responsibilities_text IS NULL OR "
                "length(responsibilities_text) <= 10000"
            ),
            name="ck_normalized_jobs_responsibilities_length",
        ),
        CheckConstraint(
            (
                "required_qualifications_text IS NULL OR "
                "length(required_qualifications_text) <= 10000"
            ),
            name="ck_normalized_jobs_required_qualifications_length",
        ),
        CheckConstraint(
            (
                "preferred_qualifications_text IS NULL OR "
                "length(preferred_qualifications_text) <= 10000"
            ),
            name="ck_normalized_jobs_preferred_qualifications_length",
        ),
        UniqueConstraint(
            "job_source_id",
            "source_job_id",
            name="uq_normalized_jobs_source_job_id",
        ),
        Index(
            "ix_normalized_jobs_source_lifecycle",
            "job_source_id",
            "lifecycle_status",
        ),
        Index(
            "ix_normalized_jobs_last_seen",
            "last_seen_at",
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

    source_job_id: Mapped[str] = mapped_column(
        String(300),
        nullable=False,
    )

    canonical_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    source_url: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    employer_name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
        index=True,
    )

    employer_external_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    title: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
        index=True,
    )

    normalized_title: Mapped[str | None] = mapped_column(
        String(250),
        nullable=True,
    )

    description_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    responsibilities_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    required_qualifications_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    preferred_qualifications_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    remote_mode: Mapped[str] = mapped_column(
        String(50),
        default="unspecified",
        server_default="unspecified",
        nullable=False,
        index=True,
    )

    employment_type: Mapped[str] = mapped_column(
        String(50),
        default="unspecified",
        server_default="unspecified",
        nullable=False,
        index=True,
    )

    seniority: Mapped[str] = mapped_column(
        String(50),
        default="unspecified",
        server_default="unspecified",
        nullable=False,
        index=True,
    )

    source_sponsorship_visa_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    posted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    source_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
        index=True,
    )

    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
        index=True,
    )

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
        index=True,
    )

    source_attribution_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    source_attribution_url: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    source_license_reference: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
    )

    normalization_version: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    lifecycle_status: Mapped[str] = mapped_column(
        String(50),
        default="discovered",
        server_default="discovered",
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


class JobLocation(Base):
    __tablename__ = "job_locations"
    __table_args__ = (
        CheckConstraint(
            "remote_mode IS NULL OR "
            + enum_check("remote_mode", JOB_REMOTE_MODES),
            name="ck_job_locations_remote_mode",
        ),
        Index("ix_job_locations_job_order", "job_id", "sort_order", "id"),
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

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    raw_location_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    country: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    region: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    city: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
    )

    postal_code: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    remote_mode: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    source_provided: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("1"),
        nullable=False,
    )

    normalization_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )


class JobCompensation(Base):
    __tablename__ = "job_compensations"
    __table_args__ = (
        CheckConstraint(
            (
                "min_amount IS NULL OR max_amount IS NULL OR "
                "min_amount <= max_amount"
            ),
            name="ck_job_compensations_min_lte_max",
        ),
        CheckConstraint(
            "currency IS NULL OR length(currency) = 3",
            name="ck_job_compensations_currency_length",
        ),
        CheckConstraint(
            enum_check("compensation_period", JOB_COMPENSATION_PERIODS),
            name="ck_job_compensations_period",
        ),
        Index("ix_job_compensations_job_order", "job_id", "sort_order", "id"),
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

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    min_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    max_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
    )

    currency: Mapped[str | None] = mapped_column(
        String(3),
        nullable=True,
    )

    compensation_period: Mapped[str] = mapped_column(
        String(50),
        default="unspecified",
        server_default="unspecified",
        nullable=False,
    )

    source_text: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    explicitly_supplied: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("1"),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )


class JobDuplicate(Base):
    """Deterministic duplicate link between two normalized jobs.

    Links are additive audit records; duplicate detection never
    merges or deletes job rows, preserving provenance.
    """

    __tablename__ = "job_duplicates"
    __table_args__ = (
        CheckConstraint(
            enum_check(
                "detection_method",
                JOB_DUPLICATE_DETECTION_METHODS,
            ),
            name="ck_job_duplicates_detection_method",
        ),
        CheckConstraint(
            "job_id != duplicate_of_job_id",
            name="ck_job_duplicates_distinct_jobs",
        ),
        UniqueConstraint(
            "job_id",
            "duplicate_of_job_id",
            "detection_method",
            name="uq_job_duplicates_pair_method",
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

    duplicate_of_job_id: Mapped[int] = mapped_column(
        ForeignKey(
            "normalized_jobs.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    detection_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )

    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )


class JobSkillRequirement(Base):
    __tablename__ = "job_skill_requirements"
    __table_args__ = (
        CheckConstraint(
            enum_check("requirement_type", JOB_SKILL_REQUIREMENT_TYPES),
            name="ck_job_skill_requirements_type",
        ),
        UniqueConstraint(
            "job_id",
            "skill_text",
            "requirement_type",
            name="uq_job_skill_requirements_job_text_type",
        ),
        Index(
            "ix_job_skill_requirements_job_order",
            "job_id",
            "sort_order",
            "id",
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

    sort_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default=text("0"),
        nullable=False,
    )

    skill_text: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    normalized_skill_key: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        index=True,
    )

    requirement_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
    )

    source_provided: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("1"),
        nullable=False,
    )

    normalization_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=current_utc_time,
        nullable=False,
    )
