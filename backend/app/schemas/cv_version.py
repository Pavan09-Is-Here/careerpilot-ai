from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CVVersionType = Literal[
    "original",
    "parsed",
    "verified_master",
    "tailored",
]
CVVersionStatus = Literal[
    "draft",
    "ready",
    "archived",
    "failed",
]


class CVVersionAdoptRequest(BaseModel):
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    status: CVVersionStatus = "ready"
    is_primary: bool = False


class CVVersionCreate(BaseModel):
    version_type: CVVersionType
    parent_version_id: int | None = Field(
        default=None,
        gt=0,
    )
    source_document_id: int | None = Field(
        default=None,
        gt=0,
    )
    status: CVVersionStatus = "draft"
    display_name: str = Field(
        min_length=1,
        max_length=250,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    job_reference: str | None = Field(
        default=None,
        max_length=250,
    )
    is_primary: bool = False
    mime_type: str | None = Field(
        default=None,
        max_length=150,
    )
    file_size: int | None = Field(
        default=None,
        ge=0,
    )
    sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )


class CVVersionUpdate(BaseModel):
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    job_reference: str | None = Field(
        default=None,
        max_length=250,
    )
    status: CVVersionStatus | None = None
    version_type: CVVersionType | None = None
    parent_version_id: int | None = Field(
        default=None,
        gt=0,
    )
    source_document_id: int | None = Field(
        default=None,
        gt=0,
    )


class CVVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_profile_id: int
    source_document_id: int | None = None
    parent_version_id: int | None = None
    version_type: CVVersionType
    status: CVVersionStatus
    display_name: str = Field(
        max_length=250,
    )
    description: str | None = None
    job_reference: str | None = Field(
        default=None,
        max_length=250,
    )
    is_primary: bool
    mime_type: str | None = Field(
        default=None,
        max_length=150,
    )
    file_size: int | None = None
    sha256: str | None = Field(
        default=None,
        max_length=64,
    )
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


class CVVersionHistoryResponse(BaseModel):
    version: CVVersionResponse
    ancestry: list[CVVersionResponse]
    children: list[CVVersionResponse] = Field(
        default_factory=list,
    )
