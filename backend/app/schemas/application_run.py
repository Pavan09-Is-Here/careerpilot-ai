from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ApplicationRunStatus = Literal[
    "paused_for_gate",
    "submitted",
    "cancelled",
    "failed",
]


class ApplicationRunGate(BaseModel):
    code: str
    detail: str
    acknowledged: bool


class ApplicationRunFillField(BaseModel):
    field: str
    field_type: str
    source: str
    action: str
    preview: str | None = None


class ApplicationRunManualField(BaseModel):
    field: str
    reason: str


class ApplicationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    application_package_id: int | None
    status: ApplicationRunStatus
    pause_reason: str | None
    gates: list[ApplicationRunGate]
    fill_plan: list[ApplicationRunFillField]
    manual_fields: list[ApplicationRunManualField]
    confirmation_number: str | None
    submitted_at: datetime | None
    driver: str
    workflow_version: str
    created_at: datetime
    updated_at: datetime


class ApplicationRunResumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_number: str | None = Field(
        default=None,
        max_length=200,
    )

    @field_validator("confirmation_number", mode="before")
    @classmethod
    def clean_confirmation(cls, value: object) -> object:
        if isinstance(value, str):
            cleaned = value.strip()
            return cleaned or None

        return value
