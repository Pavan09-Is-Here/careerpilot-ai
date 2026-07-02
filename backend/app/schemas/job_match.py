from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


JobMatchEligibilityStatus = Literal[
    "eligible",
    "conditionally_eligible",
    "ineligible",
]


class JobMatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    candidate_profile_id: int
    match_score: int | None = Field(default=None, ge=0, le=100)
    skills_match: int | None = Field(default=None, ge=0, le=100)
    experience_match: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    education_match: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    projects_match: int | None = Field(default=None, ge=0, le=100)
    location_match: int | None = Field(default=None, ge=0, le=100)
    work_auth_match: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    eligibility_status: JobMatchEligibilityStatus
    blocker_reason: str | None = Field(
        default=None,
        max_length=1000,
    )
    explanation: str = Field(max_length=8000)
    algorithm_version: str = Field(max_length=100)
    created_at: datetime
    updated_at: datetime
