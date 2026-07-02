from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


WorkerName = Literal[
    "job_discovery",
    "job_analysis",
    "application_preparation",
    "expiry_checker",
    "auto_apply_pipeline",
]

WorkerRunStatus = Literal[
    "running",
    "success",
    "partial",
    "failed",
    "skipped",
]

AuditLevel = Literal["info", "warning", "error"]


class WorkerRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_name: str
    status: WorkerRunStatus
    run_date: date
    items_processed: int
    items_succeeded: int
    items_failed: int
    retries: int
    error: str | None
    started_at: datetime
    finished_at: datetime | None


class WorkerStartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    worker: WorkerName | Literal["all"] = "all"


class WorkerStartResponse(BaseModel):
    runs: list[WorkerRunResponse]


class WorkerHealth(BaseModel):
    worker_name: str
    health: Literal["healthy", "degraded", "failed", "never_run"]
    last_status: WorkerRunStatus | None
    last_run_at: datetime | None
    runs_today: int
    max_runs_per_day: int
    daily_limit_reached: bool


class WorkerStatusResponse(BaseModel):
    workers: list[WorkerHealth]


class AuditLogEntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    worker_run_id: int | None
    worker_name: str
    action: str
    entity_type: str | None
    entity_id: int | None
    level: AuditLevel
    message: str
    created_at: datetime


class AuditLogPageResponse(BaseModel):
    items: list[AuditLogEntryResponse]
    total: int
    limit: int
    offset: int = Field(ge=0)
