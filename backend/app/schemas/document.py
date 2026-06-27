from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.fact_comparison import FactComparisonSummary


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
SectionDetectionStatus = Literal[
    "pending",
    "processing",
    "completed",
    "failed",
]
CVSectionType = Literal[
    "contact",
    "summary",
    "work_experience",
    "education",
    "skills",
    "projects",
    "certifications",
    "awards",
    "publications",
    "volunteering",
    "languages",
    "interests",
    "references",
    "additional",
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
    section_detection_status: SectionDetectionStatus
    section_detection_error: str | None = None
    section_detected_at: datetime | None = None
    section_count: int = 0
    section_detection_method: str | None = None


class DocumentListResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    candidate_profile_id: int
    created_at: datetime
    updated_at: datetime


class DocumentResponse(DocumentListResponse):
    extracted_text: str | None = None
    fact_comparison_summary: FactComparisonSummary | None = None


class DocumentExtractionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    extraction_status: ExtractionStatus
    extraction_error: str | None = None
    extracted_at: datetime | None = None
    page_count: int | None = None
    extracted_character_count: int | None = None


class CVSectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    section_order: int
    section_type: CVSectionType
    title: str | None = None
    start_char: int
    end_char: int
    content_text: str
    confidence: float = Field(
        ge=0,
        le=1,
    )
    detection_method: str
    created_at: datetime


class DocumentSectionDetectionResponse(BaseModel):
    id: int
    section_detection_status: SectionDetectionStatus
    section_detection_error: str | None = None
    section_detected_at: datetime | None = None
    section_count: int
    section_detection_method: str | None = None
    sections: list[CVSectionResponse]
