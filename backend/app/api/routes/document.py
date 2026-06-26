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
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.candidate_profile import CandidateProfile
from app.models.document import Document
from app.schemas.document import (
    DocumentExtractionResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentType,
)
from app.services.document_extraction import (
    DocumentExtractionError,
    ExtractionResult,
    extract_document_text,
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
) -> Document:
    document = database.get(Document, document_id)

    if document is None or document.candidate_profile_id != 1:
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
) -> Document:
    profile = database.get(CandidateProfile, 1)

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
            Document.candidate_profile_id == 1,
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
                    Document.candidate_profile_id == 1,
                    Document.document_type == "original_cv",
                    Document.is_primary.is_(True),
                )
                .values(is_primary=False)
            )

        document = Document(
            candidate_profile_id=1,
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
) -> list[Document]:
    documents = database.scalars(
        select(Document)
        .where(Document.candidate_profile_id == 1)
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
) -> Document:
    return get_document_or_404(document_id, database)


@router.post(
    "/{document_id}/extract",
    response_model=DocumentExtractionResponse,
)
def extract_document(
    document_id: int,
    database: Session = Depends(get_db),
) -> Document:
    document = get_document_or_404(document_id, database)

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


@router.patch(
    "/{document_id}/primary",
    response_model=DocumentResponse,
)
def set_primary_document(
    document_id: int,
    database: Session = Depends(get_db),
) -> Document:
    document = get_document_or_404(document_id, database)

    if document.document_type != "original_cv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only original CV documents can be marked as primary.",
        )

    database.execute(
        update(Document)
        .where(
            Document.candidate_profile_id == 1,
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
) -> Response:
    document = get_document_or_404(document_id, database)

    remove_uploaded_file(document.stored_filename)
    database.delete(document)
    database.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)
