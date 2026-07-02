from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ApplicationStatus = Literal[
    "discovered",
    "analyzing",
    "not_eligible",
    "matched",
    "cv_generated",
    "needs_review",
    "ready_to_apply",
    "applying",
    "blocked",
    "submitted",
    "interview",
    "rejected",
    "offer",
    "withdrawn",
]

ApplicationInterviewStage = Literal[
    "phone_screen",
    "technical",
    "onsite",
    "final",
    "other",
]


class ApplicationNote(BaseModel):
    text: str
    created_at: datetime


class ApplicationFollowUp(BaseModel):
    description: str
    due_date: date | None = None
    created_at: datetime
    done: bool = False


class ApplicationTimelineEntry(BaseModel):
    at: datetime
    label: str


class ApplicationJob(BaseModel):
    id: int
    title: str
    employer_name: str
    source_url: str


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    cv_id: int | None
    status: ApplicationStatus
    applied_at: datetime | None
    confirmation_number: str | None
    interview_date: datetime | None
    interview_stage: ApplicationInterviewStage | None
    offer_details: str | None
    rejection_reason: str | None
    outcome_date: date | None
    notes: list[ApplicationNote]
    follow_ups: list[ApplicationFollowUp]
    created_at: datetime
    updated_at: datetime


class ApplicationDetailResponse(ApplicationResponse):
    job: ApplicationJob
    timeline: list[ApplicationTimelineEntry]


class ApplicationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ApplicationStatus | None = None
    confirmation_number: str | None = Field(default=None, max_length=200)
    applied_at: datetime | None = None
    interview_date: datetime | None = None
    interview_stage: ApplicationInterviewStage | None = None
    offer_details: str | None = Field(default=None, max_length=4000)
    rejection_reason: str | None = Field(default=None, max_length=4000)
    outcome_date: date | None = None


class ApplicationNoteCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1, max_length=4000)

    @field_validator("text")
    @classmethod
    def clean_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Note text cannot be empty.")
        return cleaned


class ApplicationFollowUpCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=2000)
    due_date: date | None = None

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Follow-up description cannot be empty.")
        return cleaned
