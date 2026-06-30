from datetime import datetime
from typing import Any, Literal

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


class CVMasterGenerationRequest(BaseModel):
    display_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=250,
    )
    description: str | None = Field(
        default=None,
        max_length=1000,
    )
    idempotency_key: str = Field(
        min_length=8,
        max_length=128,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$",
    )
    is_primary: bool = False


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
    generation_version: str | None = Field(
        default=None,
        max_length=100,
    )
    source_summary: dict[str, Any] | None = None
    generated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    archived_at: datetime | None = None


CVArtifactType = Literal[
    "docx",
    "pdf",
]


class CVVersionArtifactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    cv_version_id: int
    artifact_type: CVArtifactType
    mime_type: str = Field(max_length=150)
    safe_filename: str = Field(max_length=255)
    file_size: int
    sha256: str = Field(min_length=64, max_length=64)
    page_count: int | None = None
    renderer_version: str = Field(max_length=100)
    content_version: str = Field(max_length=100)
    created_at: datetime


class CVMasterGenerationResponse(BaseModel):
    version: CVVersionResponse
    artifacts: list[CVVersionArtifactResponse] = Field(
        default_factory=list,
    )
    created: bool


class CVVersionHistoryResponse(BaseModel):
    version: CVVersionResponse
    ancestry: list[CVVersionResponse]
    children: list[CVVersionResponse] = Field(
        default_factory=list,
    )
