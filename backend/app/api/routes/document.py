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
from app.schemas.document import DocumentResponse, DocumentType
from app.services.document_storage import (
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
    response_model=list[DocumentResponse],
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
