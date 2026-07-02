from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


NotificationCategory = Literal[
    "application_prepared",
    "application_submitted",
    "manual_action_required",
    "new_matching_jobs",
]

NotificationStatus = Literal["pending", "sent", "failed", "suppressed"]


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: str
    channel: str
    recipient: str
    subject: str
    body: str
    status: str
    related_job_id: int | None
    error: str | None
    created_at: datetime
    sent_at: datetime | None


class NotificationPageResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    limit: int
    offset: int = Field(ge=0)


class NotificationDeliverResponse(BaseModel):
    sent: int
    failed: int
    skipped: int
