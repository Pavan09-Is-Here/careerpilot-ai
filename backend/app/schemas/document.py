from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DocumentType = Literal[
    "original_cv",
    "cover_letter",
    "supporting_document",
]
UploadStatus = Literal[
    "uploaded",
    "validated",
    "rejected",
    "processing_failed",
]
ExtractionStatus = Literal[
    "pending",
    "processing",
    "completed",
    "no_text",
    "failed",
]


class DocumentBase(BaseModel):
    original_filename: str = Field(
        min_length=1,
        max_length=500,
    )

    stored_filename: str = Field(
        min_length=1,
        max_length=255,
    )

    file_extension: str = Field(
        min_length=1,
        max_length=10,
    )

    media_type: str = Field(
        min_length=1,
        max_length=150,
    )

    size_bytes: int
    sha256_hash: str = Field(
        min_length=64,
        max_length=64,
    )
    document_type: DocumentType
    upload_status: UploadStatus
    is_primary: bool = False
    extraction_status: ExtractionStatus
    extraction_error: str | None = None
    extracted_at: datetime | None = None
    page_count: int | None = None
    extracted_character_count: int | None = None


class DocumentListResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_profile_id: int
    created_at: datetime
    updated_at: datetime


class DocumentResponse(DocumentListResponse):
    extracted_text: str | None = None


class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    extraction_status: ExtractionStatus
    extraction_error: str | None = None
    extracted_at: datetime | None = None
    page_count: int | None = None
    extracted_character_count: int | None = None
