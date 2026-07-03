from dataclasses import asdict
from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id
from app.core.database import get_db
from app.models.candidate_profile import CandidateProfile
from app.models.certification import Certification
from app.models.cv_section import CVSection
from app.models.document import Document
from app.models.education import Education
from app.models.experience import Experience
from app.models.fact_comparison import (
    FactComparisonFinding,
    FactComparisonRun,
)
from app.models.project import Project
from app.models.skill import Skill
from app.api.routes.fact_comparison import (
    build_fact_comparison_response,
    get_latest_fact_comparison_run,
)
from app.schemas.document import (
    CVSectionResponse,
    DocumentExtractionResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentSectionDetectionResponse,
    DocumentType,
)
from app.schemas.fact_comparison import FactComparisonRunResponse
from app.schemas.cv_version import (
    CVVersionAdoptRequest,
    CVVersionResponse,
)
from app.services.fact_comparison import (
    COMPARISON_VERSION,
    ComparisonResult,
    FactComparisonError,
    compare_document_to_verified_facts,
)
from app.services.cv_version import (
    CVVersionServiceError,
    adopt_original_version_from_document,
)
from app.services.document_extraction import (
    DocumentExtractionError,
    ExtractionResult,
    extract_document_text,
)
from app.services.cv_profile_extraction import (
    CVProfileExtractionError,
    apply_profile_suggestion,
    build_profile_suggestion,
)
from app.schemas.cv_profile_extraction import (
    ApplyProfileSuggestionRequest,
    ApplyProfileSuggestionResponse,
    ProfileSuggestionResponse,
)
from app.services.document_section_detection import (
    CVSectionDetectionError,
    SectionDetectionResult,
    detect_document_sections,
)
from app.services.document_storage import (
    ALLOWED_EXTENSIONS,
    DocumentStorageError,
    DocumentValidationError,
    prepare_upload,
    remove_uploaded_file,
    save_uploaded_file,
)


router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)


def get_document_or_404(
    document_id: int,
    database: Session,
    candidate_profile_id: int,
) -> Document:
    document = database.get(Document, document_id)

    if document is None or document.candidate_profile_id != candidate_profile_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document was not found.",
        )

    return document


def commit_document_update(
    document: Document,
    database: Session,
) -> None:
    try:
        database.commit()
        database.refresh(document)
    except Exception:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update document metadata.",
        )


def apply_extraction_result(
    document: Document,
    result: ExtractionResult,
) -> None:
    document.extraction_status = result.status
    document.extracted_text = result.extracted_text
    document.extraction_error = result.extraction_error
    document.extracted_at = result.extracted_at
    document.page_count = result.page_count
    document.extracted_character_count = result.extracted_character_count


def list_document_sections(
    document_id: int,
    database: Session,
) -> list[CVSection]:
    sections = database.scalars(
        select(CVSection)
        .where(CVSection.document_id == document_id)
        .order_by(CVSection.section_order.asc(), CVSection.start_char.asc())
    ).all()

    return list(sections)


def build_section_detection_response(
    document: Document,
    sections: list[CVSection],
) -> dict[str, object]:
    return {
        "id": document.id,
        "section_detection_status": document.section_detection_status,
        "section_detection_error": document.section_detection_error,
        "section_detected_at": document.section_detected_at,
        "section_count": document.section_count,
        "section_detection_method": document.section_detection_method,
        "sections": sections,
    }


def build_document_response(
    document: Document,
    database: Session,
) -> dict[str, object]:
    payload = DocumentResponse.model_validate(document).model_dump()
    payload["fact_comparison_summary"] = get_latest_fact_comparison_run(
        document.id,
        database,
    )

    return payload


def validate_fact_comparison_ready(
    document: Document,
    sections: list[CVSection],
) -> None:
    if document.upload_status != "validated":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only validated documents can be compared to verified facts."
            ),
        )

    if document.extraction_status != "completed" or not document.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only documents with completed text extraction can be "
                "compared."
            ),
        )

    if document.section_detection_status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only documents with completed section detection can be "
                "compared."
            ),
        )

    if not sections:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Detected CV sections are required before fact comparison."
            ),
        )


def record_fact_comparison_failure(
    document_id: int,
    message: str,
    database: Session,
    *,
    started_at: datetime | None = None,
) -> FactComparisonRun:
    now = datetime.now(timezone.utc)
    failed_run = FactComparisonRun(
        document_id=document_id,
        status="failed",
        started_at=started_at or now,
        completed_at=now,
        error=message,
        total_findings=0,
        confirmed_count=0,
        mismatch_count=0,
        missing_verified_count=0,
        unverified_claim_count=0,
        manual_review_count=0,
        comparison_version=COMPARISON_VERSION,
        is_latest_successful=False,
        created_at=now,
    )

    try:
        database.add(failed_run)
        database.commit()
        database.refresh(failed_run)
    except Exception:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record fact comparison failure.",
        )

    return failed_run


def persist_fact_comparison_result(
    document_id: int,
    result: ComparisonResult,
    database: Session,
    *,
    started_at: datetime,
) -> FactComparisonRun:
    completed_at = datetime.now(timezone.utc)
    comparison_run = FactComparisonRun(
        document_id=document_id,
        status=result.status,
        started_at=started_at,
        completed_at=completed_at,
        error=None,
        total_findings=result.total_findings,
        confirmed_count=result.confirmed_count,
        mismatch_count=result.mismatch_count,
        missing_verified_count=result.missing_verified_count,
        unverified_claim_count=result.unverified_claim_count,
        manual_review_count=result.manual_review_count,
        comparison_version=result.comparison_version,
        is_latest_successful=result.status == "completed",
        created_at=completed_at,
    )

    try:
        database.execute(
            update(FactComparisonRun)
            .where(
                FactComparisonRun.document_id == document_id,
                FactComparisonRun.is_latest_successful.is_(True),
            )
            .values(is_latest_successful=False)
        )
        database.add(comparison_run)
        database.flush()

        for finding in result.findings:
            database.add(
                FactComparisonFinding(
                    comparison_run_id=comparison_run.id,
                    document_section_id=finding.document_section_id,
                    sort_order=finding.sort_order,
                    entity_type=finding.entity_type,
                    verified_entity_id=finding.verified_entity_id,
                    field_name=finding.field_name,
                    finding_type=finding.finding_type,
                    cv_value=finding.cv_value,
                    verified_value=finding.verified_value,
                    normalized_cv_value=finding.normalized_cv_value,
                    normalized_verified_value=(
                        finding.normalized_verified_value
                    ),
                    confidence=finding.confidence,
                    severity=finding.severity,
                    explanation=finding.explanation,
                    requires_manual_review=finding.requires_manual_review,
                    dedupe_key=finding.dedupe_key,
                    created_at=completed_at,
                )
            )

        database.commit()
        database.refresh(comparison_run)
    except Exception:
        database.rollback()
        raise

    return comparison_run


def record_section_detection_failure(
    document_id: int,
    message: str,
    database: Session,
    candidate_profile_id: int,
) -> dict[str, object]:
    try:
        document = get_document_or_404(
            document_id, database, candidate_profile_id
        )
        preserved_sections = list_document_sections(document.id, database)
        document.section_detection_status = "failed"
        document.section_detection_error = message
        document.section_detected_at = datetime.now(timezone.utc)
        document.section_count = len(preserved_sections)

        database.commit()
        database.refresh(document)
    except HTTPException:
        raise
    except Exception:
        database.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record CV section detection failure.",
        )

    sections = list_document_sections(document.id, database)
    return build_section_detection_response(document, sections)


def replace_document_sections(
    document: Document,
    result: SectionDetectionResult,
    database: Session,
) -> None:
    database.execute(
        delete(CVSection).where(CVSection.document_id == document.id)
    )

    for section in result.sections:
        database.add(
            CVSection(
                document_id=document.id,
                section_order=section.section_order,
                section_type=section.section_type,
                title=section.title,
                start_char=section.start_char,
                end_char=section.end_char,
                content_text=section.content_text,
                confidence=section.confidence,
                detection_method=section.detection_method,
                created_at=result.section_detected_at,
            )
        )

    document.section_detection_status = result.status
    document.section_detection_error = result.section_detection_error
    document.section_detected_at = result.section_detected_at
    document.section_count = result.section_count
    document.section_detection_method = result.section_detection_method

    database.flush()


def failed_extraction_result(
    message: str,
    *,
    page_count: int | None = None,
) -> ExtractionResult:
    return ExtractionResult(
        status="failed",
        extracted_text=None,
        extraction_error=message,
        extracted_at=datetime.now(timezone.utc),
        page_count=page_count,
        extracted_character_count=0,
    )


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    is_primary: bool = Form(False),
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Document:
    profile = database.get(CandidateProfile, profile_id)

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Create the candidate profile before uploading documents."
            ),
        )

    try:
        document_data, temp_path = prepare_upload(
            file,
            document_type,
            is_primary,
        )
    except DocumentValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except DocumentStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    duplicate = database.scalars(
        select(Document)
        .where(
            Document.candidate_profile_id == profile_id,
            Document.sha256_hash == document_data["sha256_hash"],
        )
    ).one_or_none()

    if duplicate is not None:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate document upload detected.",
        )

    try:
        save_uploaded_file(
            temp_path,
            document_data["stored_filename"],
        )

        if (
            document_data["document_type"] == "original_cv"
            and document_data["is_primary"]
        ):
            database.execute(
                update(Document)
                .where(
                    Document.candidate_profile_id == profile_id,
                    Document.document_type == "original_cv",
                    Document.is_primary.is_(True),
                )
                .values(is_primary=False)
            )

        document = Document(
            candidate_profile_id=profile_id,
            **document_data,
        )

        database.add(document)
        database.commit()
        database.refresh(document)

        return document
    except Exception:
        remove_uploaded_file(document_data["stored_filename"])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Failed to save document metadata."
            ),
        )


@router.get(
    "",
    response_model=list[DocumentListResponse],
)
def list_documents(
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> list[Document]:
    documents = database.scalars(
        select(Document)
        .where(Document.candidate_profile_id == profile_id)
        .order_by(Document.created_at.desc(), Document.id.desc())
    ).all()

    return list(documents)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
)
def get_document(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    document = get_document_or_404(document_id, database, profile_id)

    return build_document_response(document, database)


@router.post(
    "/{document_id}/cv-version",
    response_model=CVVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def adopt_document_as_cv_version(
    document_id: int,
    request: CVVersionAdoptRequest | None = None,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> CVVersionResponse:
    try:
        return adopt_original_version_from_document(
            document_id,
            request or CVVersionAdoptRequest(),
            database,
            candidate_profile_id=profile_id,
        )
    except CVVersionServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc


def list_candidate_education(
    database: Session, candidate_profile_id: int
) -> list[Education]:
    return list(
        database.scalars(
            select(Education)
            .where(Education.candidate_profile_id == candidate_profile_id)
            .order_by(Education.start_date.desc(), Education.id.asc())
        ).all()
    )


def list_candidate_experience(
    database: Session, candidate_profile_id: int
) -> list[Experience]:
    return list(
        database.scalars(
            select(Experience)
            .where(Experience.candidate_profile_id == candidate_profile_id)
            .order_by(Experience.start_date.desc(), Experience.id.asc())
        ).all()
    )


def list_candidate_projects(
    database: Session, candidate_profile_id: int
) -> list[Project]:
    return list(
        database.scalars(
            select(Project)
            .where(Project.candidate_profile_id == candidate_profile_id)
            .order_by(Project.start_date.desc(), Project.id.asc())
        ).all()
    )


def list_candidate_skills(
    database: Session, candidate_profile_id: int
) -> list[Skill]:
    return list(
        database.scalars(
            select(Skill)
            .where(Skill.candidate_profile_id == candidate_profile_id)
            .order_by(Skill.name.asc(), Skill.id.asc())
        ).all()
    )


def list_candidate_certifications(
    database: Session, candidate_profile_id: int
) -> list[Certification]:
    return list(
        database.scalars(
            select(Certification)
            .where(Certification.candidate_profile_id == candidate_profile_id)
            .order_by(
                Certification.issue_date.desc(),
                Certification.id.asc(),
            )
        ).all()
    )


@router.post(
    "/{document_id}/compare-facts",
    response_model=FactComparisonRunResponse,
)
def compare_document_facts(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    document = get_document_or_404(document_id, database, profile_id)
    sections = list_document_sections(document.id, database)
    validate_fact_comparison_ready(document, sections)
    started_at = datetime.now(timezone.utc)

    try:
        comparison_result = compare_document_to_verified_facts(
            document=document,
            sections=sections,
            profile=database.get(CandidateProfile, profile_id),
            education_records=list_candidate_education(database, profile_id),
            experience_records=list_candidate_experience(database, profile_id),
            project_records=list_candidate_projects(database, profile_id),
            skill_records=list_candidate_skills(database, profile_id),
            certification_records=list_candidate_certifications(
                database, profile_id
            ),
        )
    except FactComparisonError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.safe_message,
        ) from exc
    except Exception:
        failed_run = record_fact_comparison_failure(
            document.id,
            "Fact comparison failed.",
            database,
            started_at=started_at,
        )
        return build_fact_comparison_response(failed_run, database)

    try:
        comparison_run = persist_fact_comparison_result(
            document.id,
            comparison_result,
            database,
            started_at=started_at,
        )
    except Exception:
        failed_run = record_fact_comparison_failure(
            document.id,
            "Fact comparison failed.",
            database,
            started_at=started_at,
        )
        return build_fact_comparison_response(failed_run, database)

    return build_fact_comparison_response(comparison_run, database)


@router.get(
    "/{document_id}/fact-comparison",
    response_model=FactComparisonRunResponse,
)
def get_document_fact_comparison(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    document = get_document_or_404(document_id, database, profile_id)
    comparison_run = get_latest_fact_comparison_run(
        document.id,
        database,
    )

    if comparison_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fact comparison was not found.",
        )

    return build_fact_comparison_response(comparison_run, database)


@router.post(
    "/{document_id}/extract",
    response_model=DocumentExtractionResponse,
)
def extract_document(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Document:
    document = get_document_or_404(document_id, database, profile_id)

    if document.upload_status != "validated":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only validated documents can be extracted.",
        )

    if document.file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported document format.",
        )

    document.extraction_status = "processing"
    document.extraction_error = None
    commit_document_update(document, database)

    try:
        extraction_result = extract_document_text(document)
    except DocumentExtractionError as exc:
        extraction_result = failed_extraction_result(
            exc.safe_message,
            page_count=exc.page_count,
        )
    except Exception:
        extraction_result = failed_extraction_result(
            "Document text extraction failed."
        )

    apply_extraction_result(document, extraction_result)
    commit_document_update(document, database)

    return document


@router.get(
    "/{document_id}/profile-suggestion",
    response_model=ProfileSuggestionResponse,
)
def get_document_profile_suggestion(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> object:
    document = get_document_or_404(document_id, database, profile_id)
    try:
        return asdict(build_profile_suggestion(document))
    except CVProfileExtractionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc


@router.post(
    "/{document_id}/apply-profile-suggestion",
    response_model=ApplyProfileSuggestionResponse,
)
def apply_document_profile_suggestion(
    document_id: int,
    payload: ApplyProfileSuggestionRequest | None = None,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    document = get_document_or_404(document_id, database, profile_id)
    request = payload or ApplyProfileSuggestionRequest()
    try:
        return apply_profile_suggestion(
            document,
            database,
            profile_id,
            apply_profile=request.apply_profile,
            apply_skills=request.apply_skills,
            include_sensitive=request.include_sensitive,
            overwrite=request.overwrite,
        )
    except CVProfileExtractionError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc


@router.post(
    "/{document_id}/detect-sections",
    response_model=DocumentSectionDetectionResponse,
)
def detect_document_cv_sections(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    document = get_document_or_404(document_id, database, profile_id)

    if document.extraction_status != "completed" or not document.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Only documents with completed text extraction can be "
                "section-detected."
            ),
        )

    document.section_detection_status = "processing"
    document.section_detection_error = None

    try:
        database.flush()
        detection_result = detect_document_sections(document)
        replace_document_sections(document, detection_result, database)
        database.commit()
        database.refresh(document)
    except CVSectionDetectionError as exc:
        database.rollback()
        return record_section_detection_failure(
            document_id,
            exc.safe_message,
            database,
            profile_id,
        )
    except Exception:
        database.rollback()
        return record_section_detection_failure(
            document_id,
            "CV section detection failed.",
            database,
            profile_id,
        )

    sections = list_document_sections(document.id, database)
    return build_section_detection_response(document, sections)


@router.get(
    "/{document_id}/sections",
    response_model=list[CVSectionResponse],
)
def get_document_cv_sections(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> list[CVSection]:
    document = get_document_or_404(document_id, database, profile_id)

    return list_document_sections(document.id, database)


@router.patch(
    "/{document_id}/primary",
    response_model=DocumentResponse,
)
def set_primary_document(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Document:
    document = get_document_or_404(document_id, database, profile_id)

    if document.document_type != "original_cv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only original CV documents can be marked as primary.",
        )

    database.execute(
        update(Document)
        .where(
            Document.candidate_profile_id == profile_id,
            Document.document_type == "original_cv",
        )
        .values(is_primary=False)
    )

    document.is_primary = True
    database.commit()
    database.refresh(document)

    return document


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_document(
    document_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> Response:
    document = get_document_or_404(document_id, database, profile_id)

    remove_uploaded_file(document.stored_filename)
    database.delete(document)
    database.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
