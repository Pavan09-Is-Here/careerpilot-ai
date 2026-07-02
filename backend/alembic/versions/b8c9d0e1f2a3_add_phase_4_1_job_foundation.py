"""Add Phase 4.1 job source and normalized job foundation.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-06-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def enum_check(column_name: str, values: tuple[str, ...]) -> str:
    quoted_values = ", ".join(f"'{value}'" for value in values)
    return f"{column_name} IN ({quoted_values})"


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


def upgrade() -> None:
    op.create_table(
        "job_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_key", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("source_category", sa.String(length=50), nullable=False),
        sa.Column(
            "provider_type",
            sa.String(length=50),
            server_default="none",
            nullable=False,
        ),
        sa.Column("base_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "enabled",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "allowlisted",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "access_mode",
            sa.String(length=50),
            server_default="metadata_only",
            nullable=False,
        ),
        sa.Column(
            "attribution_required",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("attribution_text", sa.String(length=500), nullable=True),
        sa.Column("attribution_url", sa.String(length=1000), nullable=True),
        sa.Column(
            "terms_review_status",
            sa.String(length=50),
            server_default="not_reviewed",
            nullable=False,
        ),
        sa.Column("terms_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "robots_review_status",
            sa.String(length=50),
            server_default="not_reviewed",
            nullable=False,
        ),
        sa.Column("robots_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "manual_review_required",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "commercial_use_review_status",
            sa.String(length=50),
            server_default="not_reviewed",
            nullable=False,
        ),
        sa.Column(
            "server_fetch_allowed",
            sa.Boolean(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "configured_retention_days",
            sa.Integer(),
            server_default=sa.text("30"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            enum_check("source_category", JOB_SOURCE_CATEGORIES),
            name="ck_job_sources_source_category",
        ),
        sa.CheckConstraint(
            enum_check("provider_type", JOB_SOURCE_PROVIDER_TYPES),
            name="ck_job_sources_provider_type",
        ),
        sa.CheckConstraint(
            enum_check("access_mode", JOB_SOURCE_ACCESS_MODES),
            name="ck_job_sources_access_mode",
        ),
        sa.CheckConstraint(
            enum_check("terms_review_status", JOB_SOURCE_REVIEW_STATUSES),
            name="ck_job_sources_terms_review_status",
        ),
        sa.CheckConstraint(
            enum_check("robots_review_status", JOB_SOURCE_REVIEW_STATUSES),
            name="ck_job_sources_robots_review_status",
        ),
        sa.CheckConstraint(
            enum_check(
                "commercial_use_review_status",
                JOB_SOURCE_REVIEW_STATUSES,
            ),
            name="ck_job_sources_commercial_use_review_status",
        ),
        sa.CheckConstraint(
            "configured_retention_days BETWEEN 1 AND 365",
            name="ck_job_sources_retention_days_range",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_key",
            name="uq_job_sources_source_key",
        ),
    )
    op.create_index(
        "ix_job_sources_access_mode",
        "job_sources",
        ["access_mode"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_allowlisted",
        "job_sources",
        ["allowlisted"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_commercial_use_review_status",
        "job_sources",
        ["commercial_use_review_status"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_display_name",
        "job_sources",
        ["display_name"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_enabled",
        "job_sources",
        ["enabled"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_manual_review_required",
        "job_sources",
        ["manual_review_required"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_provider_type",
        "job_sources",
        ["provider_type"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_robots_review_status",
        "job_sources",
        ["robots_review_status"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_server_fetch_allowed",
        "job_sources",
        ["server_fetch_allowed"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_source_category",
        "job_sources",
        ["source_category"],
        unique=False,
    )
    op.create_index(
        "ix_job_sources_terms_review_status",
        "job_sources",
        ["terms_review_status"],
        unique=False,
    )

    op.create_table(
        "normalized_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_source_id", sa.Integer(), nullable=False),
        sa.Column("source_job_id", sa.String(length=300), nullable=False),
        sa.Column("canonical_url", sa.String(length=1000), nullable=True),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("employer_name", sa.String(length=250), nullable=False),
        sa.Column("employer_external_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=250), nullable=False),
        sa.Column("normalized_title", sa.String(length=250), nullable=True),
        sa.Column("description_text", sa.Text(), nullable=True),
        sa.Column("responsibilities_text", sa.Text(), nullable=True),
        sa.Column("required_qualifications_text", sa.Text(), nullable=True),
        sa.Column("preferred_qualifications_text", sa.Text(), nullable=True),
        sa.Column(
            "remote_mode",
            sa.String(length=50),
            server_default="unspecified",
            nullable=False,
        ),
        sa.Column(
            "employment_type",
            sa.String(length=50),
            server_default="unspecified",
            nullable=False,
        ),
        sa.Column(
            "seniority",
            sa.String(length=50),
            server_default="unspecified",
            nullable=False,
        ),
        sa.Column("source_sponsorship_visa_text", sa.Text(), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source_attribution_text",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "source_attribution_url",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "source_license_reference",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("normalization_version", sa.String(length=100), nullable=False),
        sa.Column(
            "lifecycle_status",
            sa.String(length=50),
            server_default="discovered",
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            enum_check("remote_mode", JOB_REMOTE_MODES),
            name="ck_normalized_jobs_remote_mode",
        ),
        sa.CheckConstraint(
            enum_check("employment_type", JOB_EMPLOYMENT_TYPES),
            name="ck_normalized_jobs_employment_type",
        ),
        sa.CheckConstraint(
            enum_check("seniority", JOB_SENIORITIES),
            name="ck_normalized_jobs_seniority",
        ),
        sa.CheckConstraint(
            enum_check("lifecycle_status", JOB_LIFECYCLE_STATUSES),
            name="ck_normalized_jobs_lifecycle_status",
        ),
        sa.CheckConstraint(
            "length(content_hash) = 64",
            name="ck_normalized_jobs_content_hash_length",
        ),
        sa.CheckConstraint(
            "description_text IS NULL OR length(description_text) <= 20000",
            name="ck_normalized_jobs_description_length",
        ),
        sa.CheckConstraint(
            (
                "responsibilities_text IS NULL OR "
                "length(responsibilities_text) <= 10000"
            ),
            name="ck_normalized_jobs_responsibilities_length",
        ),
        sa.CheckConstraint(
            (
                "required_qualifications_text IS NULL OR "
                "length(required_qualifications_text) <= 10000"
            ),
            name="ck_normalized_jobs_required_qualifications_length",
        ),
        sa.CheckConstraint(
            (
                "preferred_qualifications_text IS NULL OR "
                "length(preferred_qualifications_text) <= 10000"
            ),
            name="ck_normalized_jobs_preferred_qualifications_length",
        ),
        sa.ForeignKeyConstraint(
            ["job_source_id"],
            ["job_sources.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_source_id",
            "source_job_id",
            name="uq_normalized_jobs_source_job_id",
        ),
    )
    op.create_index(
        "ix_normalized_jobs_content_hash",
        "normalized_jobs",
        ["content_hash"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_employer_name",
        "normalized_jobs",
        ["employer_name"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_employment_type",
        "normalized_jobs",
        ["employment_type"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_first_seen_at",
        "normalized_jobs",
        ["first_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_ingested_at",
        "normalized_jobs",
        ["ingested_at"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_job_source_id",
        "normalized_jobs",
        ["job_source_id"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_last_seen",
        "normalized_jobs",
        ["last_seen_at", "id"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_last_seen_at",
        "normalized_jobs",
        ["last_seen_at"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_lifecycle_status",
        "normalized_jobs",
        ["lifecycle_status"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_remote_mode",
        "normalized_jobs",
        ["remote_mode"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_seniority",
        "normalized_jobs",
        ["seniority"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_source_lifecycle",
        "normalized_jobs",
        ["job_source_id", "lifecycle_status"],
        unique=False,
    )
    op.create_index(
        "ix_normalized_jobs_title",
        "normalized_jobs",
        ["title"],
        unique=False,
    )

    op.create_table(
        "job_locations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("raw_location_text", sa.String(length=500), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("region", sa.String(length=150), nullable=True),
        sa.Column("city", sa.String(length=150), nullable=True),
        sa.Column("postal_code", sa.String(length=50), nullable=True),
        sa.Column("remote_mode", sa.String(length=50), nullable=True),
        sa.Column(
            "source_provided",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("normalization_version", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "remote_mode IS NULL OR "
            + enum_check("remote_mode", JOB_REMOTE_MODES),
            name="ck_job_locations_remote_mode",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["normalized_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_locations_job_id",
        "job_locations",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_locations_job_order",
        "job_locations",
        ["job_id", "sort_order", "id"],
        unique=False,
    )

    op.create_table(
        "job_compensations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("min_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("max_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column(
            "compensation_period",
            sa.String(length=50),
            server_default="unspecified",
            nullable=False,
        ),
        sa.Column("source_text", sa.String(length=1000), nullable=True),
        sa.Column(
            "explicitly_supplied",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            (
                "min_amount IS NULL OR max_amount IS NULL OR "
                "min_amount <= max_amount"
            ),
            name="ck_job_compensations_min_lte_max",
        ),
        sa.CheckConstraint(
            "currency IS NULL OR length(currency) = 3",
            name="ck_job_compensations_currency_length",
        ),
        sa.CheckConstraint(
            enum_check("compensation_period", JOB_COMPENSATION_PERIODS),
            name="ck_job_compensations_period",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["normalized_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_job_compensations_job_id",
        "job_compensations",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_compensations_job_order",
        "job_compensations",
        ["job_id", "sort_order", "id"],
        unique=False,
    )

    op.create_table(
        "job_skill_requirements",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.Integer(), nullable=False),
        sa.Column(
            "sort_order",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("skill_text", sa.String(length=200), nullable=False),
        sa.Column("normalized_skill_key", sa.String(length=150), nullable=True),
        sa.Column("requirement_type", sa.String(length=50), nullable=False),
        sa.Column(
            "source_provided",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column("normalization_version", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            enum_check("requirement_type", JOB_SKILL_REQUIREMENT_TYPES),
            name="ck_job_skill_requirements_type",
        ),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["normalized_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "job_id",
            "skill_text",
            "requirement_type",
            name="uq_job_skill_requirements_job_text_type",
        ),
    )
    op.create_index(
        "ix_job_skill_requirements_job_id",
        "job_skill_requirements",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_skill_requirements_job_order",
        "job_skill_requirements",
        ["job_id", "sort_order", "id"],
        unique=False,
    )
    op.create_index(
        "ix_job_skill_requirements_normalized_skill_key",
        "job_skill_requirements",
        ["normalized_skill_key"],
        unique=False,
    )
    op.create_index(
        "ix_job_skill_requirements_requirement_type",
        "job_skill_requirements",
        ["requirement_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_job_skill_requirements_requirement_type",
        table_name="job_skill_requirements",
    )
    op.drop_index(
        "ix_job_skill_requirements_normalized_skill_key",
        table_name="job_skill_requirements",
    )
    op.drop_index(
        "ix_job_skill_requirements_job_order",
        table_name="job_skill_requirements",
    )
    op.drop_index(
        "ix_job_skill_requirements_job_id",
        table_name="job_skill_requirements",
    )
    op.drop_table("job_skill_requirements")

    op.drop_index(
        "ix_job_compensations_job_order",
        table_name="job_compensations",
    )
    op.drop_index(
        "ix_job_compensations_job_id",
        table_name="job_compensations",
    )
    op.drop_table("job_compensations")

    op.drop_index("ix_job_locations_job_order", table_name="job_locations")
    op.drop_index("ix_job_locations_job_id", table_name="job_locations")
    op.drop_table("job_locations")

    op.drop_index("ix_normalized_jobs_title", table_name="normalized_jobs")
    op.drop_index(
        "ix_normalized_jobs_source_lifecycle",
        table_name="normalized_jobs",
    )
    op.drop_index("ix_normalized_jobs_seniority", table_name="normalized_jobs")
    op.drop_index(
        "ix_normalized_jobs_remote_mode",
        table_name="normalized_jobs",
    )
    op.drop_index(
        "ix_normalized_jobs_lifecycle_status",
        table_name="normalized_jobs",
    )
    op.drop_index(
        "ix_normalized_jobs_last_seen_at",
        table_name="normalized_jobs",
    )
    op.drop_index("ix_normalized_jobs_last_seen", table_name="normalized_jobs")
    op.drop_index(
        "ix_normalized_jobs_job_source_id",
        table_name="normalized_jobs",
    )
    op.drop_index(
        "ix_normalized_jobs_ingested_at",
        table_name="normalized_jobs",
    )
    op.drop_index(
        "ix_normalized_jobs_first_seen_at",
        table_name="normalized_jobs",
    )
    op.drop_index(
        "ix_normalized_jobs_employment_type",
        table_name="normalized_jobs",
    )
    op.drop_index(
        "ix_normalized_jobs_employer_name",
        table_name="normalized_jobs",
    )
    op.drop_index(
        "ix_normalized_jobs_content_hash",
        table_name="normalized_jobs",
    )
    op.drop_table("normalized_jobs")

    op.drop_index(
        "ix_job_sources_terms_review_status",
        table_name="job_sources",
    )
    op.drop_index("ix_job_sources_source_category", table_name="job_sources")
    op.drop_index(
        "ix_job_sources_server_fetch_allowed",
        table_name="job_sources",
    )
    op.drop_index(
        "ix_job_sources_robots_review_status",
        table_name="job_sources",
    )
    op.drop_index("ix_job_sources_provider_type", table_name="job_sources")
    op.drop_index(
        "ix_job_sources_manual_review_required",
        table_name="job_sources",
    )
    op.drop_index("ix_job_sources_enabled", table_name="job_sources")
    op.drop_index("ix_job_sources_display_name", table_name="job_sources")
    op.drop_index(
        "ix_job_sources_commercial_use_review_status",
        table_name="job_sources",
    )
    op.drop_index("ix_job_sources_allowlisted", table_name="job_sources")
    op.drop_index("ix_job_sources_access_mode", table_name="job_sources")
    op.drop_table("job_sources")
