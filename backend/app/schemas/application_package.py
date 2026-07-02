from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ApplicationPackageReadiness = Literal[
    "ready_for_automatic_application",
    "needs_user_review",
    "blocked_by_missing_information",
    "blocked_by_captcha",
    "blocked_by_mfa",
    "blocked_by_assessment",
    "not_eligible",
]

BlockerCode = Literal["captcha", "mfa", "assessment"]


class ApplicationPackageBlocker(BaseModel):
    code: BlockerCode
    detail: str


class ApplicationPackageJob(BaseModel):
    id: int
    title: str
    employer_name: str
    source_url: str
    lifecycle_status: str
    remote_mode: str
    employment_type: str


class ApplicationPackageMatch(BaseModel):
    match_score: int | None
    eligibility_status: str
    blocker_reason: str | None


class ApplicationPackageArtifact(BaseModel):
    artifact_type: str
    safe_filename: str
    file_size: int
    page_count: int | None = None


class ApplicationPackageCV(BaseModel):
    cv_version_id: int
    status: str
    artifacts: list[ApplicationPackageArtifact]


class ApplicationPackageAnswer(BaseModel):
    id: int
    category: str
    question_label: str
    verified: bool
    requires_manual_confirmation: bool
    manually_confirmed: bool


class ApplicationPackageSalary(BaseModel):
    currency: str | None
    minimum: Decimal | None
    maximum: Decimal | None
    midpoint: Decimal | None
    confidence: str
    basis: str
    safe_answer: str
    below_declared_minimum: bool


class ApplicationPackageResponse(BaseModel):
    job_id: int
    readiness_status: ApplicationPackageReadiness
    prepared_at: datetime
    assembly_version: str
    user_confirmed: bool
    user_notes: str | None
    cover_letter_text: str | None
    blockers: list[ApplicationPackageBlocker]
    risk_warnings: list[str]
    missing_items: list[str]
    job: ApplicationPackageJob
    match: ApplicationPackageMatch | None
    tailored_cv: ApplicationPackageCV | None
    verified_answers: list[ApplicationPackageAnswer]
    salary: ApplicationPackageSalary | None


class ApplicationPackageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_confirmed: bool = False

    user_notes: str | None = Field(
        default=None,
        max_length=2000,
    )

    @field_validator("user_notes", mode="before")
    @classmethod
    def clean_notes(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None

        return value
