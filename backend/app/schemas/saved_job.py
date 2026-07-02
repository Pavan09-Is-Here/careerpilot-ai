from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.job import NormalizedJobListItemResponse


SavedJobReviewStatus = Literal[
    "saved",
    "shortlisted",
    "dismissed",
    "archived",
]


class SavedJobCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: int = Field(gt=0)
    notes: str | None = Field(default=None, max_length=2000)


class SavedJobUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_status: SavedJobReviewStatus | None = None
    notes: str | None = Field(default=None, max_length=2000)


class SavedJobResponse(BaseModel):
    id: int
    job_id: int
    review_status: SavedJobReviewStatus
    notes: str | None = Field(default=None, max_length=2000)
    status_changed_at: datetime
    created_at: datetime
    updated_at: datetime
    job: NormalizedJobListItemResponse


class SavedJobPageResponse(BaseModel):
    items: list[SavedJobResponse]
    total: int
    page: int
    page_size: int
