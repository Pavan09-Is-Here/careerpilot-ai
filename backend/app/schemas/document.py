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


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_profile_id: int
    created_at: datetime
    updated_at: datetime
