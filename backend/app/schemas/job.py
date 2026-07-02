from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


JobSourceCategory = Literal[
    "provider_api",
    "job_board_api",
    "company_career_page",
    "user_supplied_url",
    "manual_reference",
]
JobSourceProviderType = Literal[
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
]
JobSourceAccessMode = Literal[
    "metadata_only",
    "manual_import",
    "api",
    "approved_static_fetch",
]
JobSourceReviewStatus = Literal[
    "not_reviewed",
    "review_required",
    "approved_for_configured_use",
    "rejected",
    "suspended",
]
JobRemoteMode = Literal[
    "unspecified",
    "onsite",
    "hybrid",
    "remote",
    "flexible",
]
JobEmploymentType = Literal[
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
]
JobSeniority = Literal[
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
]
JobLifecycleStatus = Literal[
    "discovered",
    "active",
    "possibly_stale",
    "expired",
    "removed",
    "unavailable",
]
JobCompensationPeriod = Literal[
    "unspecified",
    "hourly",
    "daily",
    "weekly",
    "monthly",
    "yearly",
    "one_time",
]
JobSkillRequirementType = Literal[
    "required",
    "preferred",
    "mentioned",
]
JobDuplicateDetectionMethod = Literal[
    "canonical_url",
    "content_hash",
]


class JobSourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str = Field(min_length=1, max_length=100)
    display_name: str = Field(min_length=1, max_length=200)
    source_category: JobSourceCategory
    provider_type: JobSourceProviderType = "none"
    base_url: str | None = Field(default=None, max_length=1000)
    enabled: bool = False
    allowlisted: bool = False
    access_mode: JobSourceAccessMode = "metadata_only"
    attribution_required: bool = False
    attribution_text: str | None = Field(default=None, max_length=500)
    attribution_url: str | None = Field(default=None, max_length=1000)
    terms_review_status: JobSourceReviewStatus = "not_reviewed"
    terms_reviewed_at: datetime | None = None
    robots_review_status: JobSourceReviewStatus = "not_reviewed"
    robots_reviewed_at: datetime | None = None
    manual_review_required: bool = True
    commercial_use_review_status: JobSourceReviewStatus = "not_reviewed"
    server_fetch_allowed: bool = False
    configured_retention_days: int = Field(default=30, ge=1, le=365)


class JobSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_key: str = Field(max_length=100)
    display_name: str = Field(max_length=200)
    source_category: JobSourceCategory
    provider_type: JobSourceProviderType
    base_url: str | None = Field(default=None, max_length=1000)
    enabled: bool
    allowlisted: bool
    access_mode: JobSourceAccessMode
    attribution_required: bool
    attribution_text: str | None = Field(default=None, max_length=500)
    attribution_url: str | None = Field(default=None, max_length=1000)
    terms_review_status: JobSourceReviewStatus
    terms_reviewed_at: datetime | None = None
    robots_review_status: JobSourceReviewStatus
    robots_reviewed_at: datetime | None = None
    manual_review_required: bool
    commercial_use_review_status: JobSourceReviewStatus
    server_fetch_allowed: bool
    configured_retention_days: int
    created_at: datetime
    updated_at: datetime


class JobSourcePageResponse(BaseModel):
    items: list[JobSourceResponse]
    total: int
    page: int
    page_size: int


class JobLocationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort_order: int = Field(default=0, ge=0)
    raw_location_text: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=150)
    city: str | None = Field(default=None, max_length=150)
    postal_code: str | None = Field(default=None, max_length=50)
    remote_mode: JobRemoteMode | None = None
    source_provided: bool = True
    normalization_version: str | None = Field(default=None, max_length=100)


class JobCompensationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort_order: int = Field(default=0, ge=0)
    min_amount: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
    )
    max_amount: Decimal | None = Field(
        default=None,
        max_digits=12,
        decimal_places=2,
    )
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    compensation_period: JobCompensationPeriod = "unspecified"
    source_text: str | None = Field(default=None, max_length=1000)
    explicitly_supplied: bool = True


class JobSkillRequirementCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sort_order: int = Field(default=0, ge=0)
    skill_text: str = Field(min_length=1, max_length=200)
    normalized_skill_key: str | None = Field(default=None, max_length=150)
    requirement_type: JobSkillRequirementType
    source_provided: bool = True
    normalization_version: str | None = Field(default=None, max_length=100)


class NormalizedJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_source_id: int = Field(gt=0)
    source_job_id: str = Field(min_length=1, max_length=300)
    canonical_url: str | None = Field(default=None, max_length=1000)
    source_url: str = Field(min_length=1, max_length=1000)
    employer_name: str = Field(min_length=1, max_length=250)
    employer_external_id: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=1, max_length=250)
    normalized_title: str | None = Field(default=None, max_length=250)
    description_text: str | None = Field(default=None, max_length=20000)
    responsibilities_text: str | None = Field(default=None, max_length=10000)
    required_qualifications_text: str | None = Field(
        default=None,
        max_length=10000,
    )
    preferred_qualifications_text: str | None = Field(
        default=None,
        max_length=10000,
    )
    remote_mode: JobRemoteMode = "unspecified"
    employment_type: JobEmploymentType = "unspecified"
    seniority: JobSeniority = "unspecified"
    source_sponsorship_visa_text: str | None = Field(
        default=None,
        max_length=1000,
    )
    posted_at: datetime | None = None
    source_updated_at: datetime | None = None
    expires_at: datetime | None = None
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    ingested_at: datetime | None = None
    source_attribution_text: str | None = Field(default=None, max_length=500)
    source_attribution_url: str | None = Field(default=None, max_length=1000)
    source_license_reference: str | None = Field(default=None, max_length=1000)
    content_hash: str = Field(min_length=64, max_length=64)
    normalization_version: str = Field(min_length=1, max_length=100)
    lifecycle_status: JobLifecycleStatus = "discovered"


class JobLocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    sort_order: int
    raw_location_text: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=100)
    region: str | None = Field(default=None, max_length=150)
    city: str | None = Field(default=None, max_length=150)
    postal_code: str | None = Field(default=None, max_length=50)
    remote_mode: JobRemoteMode | None = None
    source_provided: bool
    normalization_version: str | None = Field(default=None, max_length=100)
    created_at: datetime


class JobCompensationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    sort_order: int
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=3)
    compensation_period: JobCompensationPeriod
    source_text: str | None = Field(default=None, max_length=1000)
    explicitly_supplied: bool
    created_at: datetime


class JobSkillRequirementResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    sort_order: int
    skill_text: str = Field(max_length=200)
    normalized_skill_key: str | None = Field(default=None, max_length=150)
    requirement_type: JobSkillRequirementType
    source_provided: bool
    normalization_version: str | None = Field(default=None, max_length=100)
    created_at: datetime


class NormalizedJobListItemResponse(BaseModel):
    id: int
    job_source_id: int
    source_job_id: str = Field(max_length=300)
    canonical_url: str | None = Field(default=None, max_length=1000)
    source_url: str = Field(max_length=1000)
    employer_name: str = Field(max_length=250)
    title: str = Field(max_length=250)
    normalized_title: str | None = Field(default=None, max_length=250)
    remote_mode: JobRemoteMode
    employment_type: JobEmploymentType
    seniority: JobSeniority
    posted_at: datetime | None = None
    expires_at: datetime | None = None
    first_seen_at: datetime
    last_seen_at: datetime
    ingested_at: datetime
    lifecycle_status: JobLifecycleStatus
    description_excerpt: str | None = Field(default=None, max_length=240)
    created_at: datetime
    updated_at: datetime


class NormalizedJobPageResponse(BaseModel):
    items: list[NormalizedJobListItemResponse]
    total: int
    page: int
    page_size: int


class JobDuplicateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    duplicate_of_job_id: int
    detection_method: JobDuplicateDetectionMethod
    detected_at: datetime
    created_at: datetime


class JobDuplicateListResponse(BaseModel):
    items: list[JobDuplicateResponse]
    total: int


class JobMaintenanceResponse(BaseModel):
    jobs_marked_expired: int
    jobs_marked_possibly_stale: int
    duplicate_links_created: int


class NormalizedJobDetailResponse(NormalizedJobListItemResponse):
    employer_external_id: str | None = Field(default=None, max_length=255)
    description_text: str | None = Field(default=None, max_length=20000)
    responsibilities_text: str | None = Field(default=None, max_length=10000)
    required_qualifications_text: str | None = Field(
        default=None,
        max_length=10000,
    )
    preferred_qualifications_text: str | None = Field(
        default=None,
        max_length=10000,
    )
    source_sponsorship_visa_text: str | None = Field(
        default=None,
        max_length=1000,
    )
    source_updated_at: datetime | None = None
    source_attribution_text: str | None = Field(default=None, max_length=500)
    source_attribution_url: str | None = Field(default=None, max_length=1000)
    source_license_reference: str | None = Field(default=None, max_length=1000)
    content_hash: str = Field(max_length=64)
    normalization_version: str = Field(max_length=100)
    locations: list[JobLocationResponse] = Field(default_factory=list)
    compensations: list[JobCompensationResponse] = Field(default_factory=list)
    skill_requirements: list[JobSkillRequirementResponse] = Field(
        default_factory=list,
    )
