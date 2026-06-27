from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ComparisonRunStatus = Literal[
    "pending",
    "processing",
    "completed",
    "partial",
    "failed",
]
ComparisonEntityType = Literal[
    "candidate_profile",
    "education",
    "work_experience",
    "project",
    "skill",
    "certification",
]
ComparisonFindingType = Literal[
    "confirmed",
    "possible_mismatch",
    "missing_verified_fact",
    "unverified_claim",
    "date_conflict",
    "organisation_conflict",
    "skill_conflict",
    "manual_review",
]
ComparisonSeverity = Literal[
    "info",
    "review",
    "warning",
]


class FactComparisonSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    status: ComparisonRunStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = Field(
        default=None,
        max_length=500,
    )
    total_findings: int
    confirmed_count: int
    mismatch_count: int
    missing_verified_count: int
    unverified_claim_count: int
    manual_review_count: int
    comparison_version: str = Field(
        max_length=100,
    )
    is_latest_successful: bool
    created_at: datetime


class FactComparisonFindingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    comparison_run_id: int
    document_section_id: int | None = None
    sort_order: int
    entity_type: ComparisonEntityType
    verified_entity_id: int | None = None
    field_name: str | None = Field(
        default=None,
        max_length=100,
    )
    finding_type: ComparisonFindingType
    cv_value: str | None = Field(
        default=None,
        max_length=500,
    )
    verified_value: str | None = Field(
        default=None,
        max_length=500,
    )
    normalized_cv_value: str | None = Field(
        default=None,
        max_length=600,
    )
    normalized_verified_value: str | None = Field(
        default=None,
        max_length=600,
    )
    confidence: float = Field(
        ge=0,
        le=1,
    )
    severity: ComparisonSeverity
    explanation: str = Field(
        max_length=500,
    )
    requires_manual_review: bool
    created_at: datetime


class FactComparisonRunResponse(FactComparisonSummary):
    findings: list[FactComparisonFindingResponse] = Field(
        default_factory=list,
    )
