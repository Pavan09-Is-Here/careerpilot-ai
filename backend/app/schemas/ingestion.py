from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


IngestionRunStatus = Literal[
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
]
TERMINAL_INGESTION_RUN_STATUSES: tuple[str, ...] = (
    "succeeded",
    "failed",
    "cancelled",
)


class IngestionRunCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_source_id: int = Field(gt=0)


class IngestionRunCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_status: Literal["succeeded", "failed", "cancelled"]
    failure_summary: str | None = Field(default=None, max_length=1000)
    jobs_discovered: int = Field(default=0, ge=0, le=1_000_000)
    jobs_updated: int = Field(default=0, ge=0, le=1_000_000)


class IngestionRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_source_id: int
    run_status: IngestionRunStatus
    started_at: datetime | None = None
    finished_at: datetime | None = None
    failure_summary: str | None = Field(default=None, max_length=1000)
    jobs_discovered: int
    jobs_updated: int
    snapshots_recorded: int
    created_at: datetime
    updated_at: datetime


class IngestionRunPageResponse(BaseModel):
    items: list[IngestionRunResponse]
    total: int
    page: int
    page_size: int


class SourceSnapshotCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ingestion_run_id: int = Field(gt=0)
    content_hash: str = Field(min_length=64, max_length=64)
    payload_size_bytes: int = Field(ge=0)
    payload_media_type: str = Field(
        default="application/json",
        min_length=1,
        max_length=100,
    )
    storage_reference: str | None = Field(default=None, max_length=300)
    fetched_at: datetime | None = None
    expires_at: datetime | None = None


class SourceSnapshotResponse(BaseModel):
    """Snapshot metadata safe for the client.

    Never includes the provider payload or the internal storage
    reference.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    ingestion_run_id: int
    job_source_id: int
    content_hash: str = Field(max_length=64)
    payload_size_bytes: int
    payload_media_type: str = Field(max_length=100)
    fetched_at: datetime
    expires_at: datetime
    created_at: datetime


class SourceSnapshotPageResponse(BaseModel):
    items: list[SourceSnapshotResponse]
    total: int
    page: int
    page_size: int
