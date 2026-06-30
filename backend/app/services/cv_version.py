from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.cv_version import CVVersion
from app.models.document import Document
from app.schemas.cv_version import (
    CVVersionAdoptRequest,
    CVVersionCreate,
    CVVersionUpdate,
)


DEFAULT_CANDIDATE_PROFILE_ID = 1
VERSION_TYPES = {"original", "parsed", "verified_master", "tailored"}
VERSION_STATUSES = {"draft", "ready", "archived", "failed"}
PARENT_TYPES_BY_VERSION_TYPE = {
    "parsed": {"original"},
    "verified_master": {"parsed", "verified_master"},
    "tailored": {"verified_master"},
}
IMMUTABLE_UPDATE_FIELDS = {
    "version_type",
    "parent_version_id",
    "source_document_id",
}


class CVVersionServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def require_candidate_profile(
    database: Session,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> CandidateProfile:
    profile = database.get(CandidateProfile, candidate_profile_id)

    if profile is None:
        raise CVVersionServiceError(
            "Create the candidate profile before managing CV versions.",
            status_code=400,
        )

    return profile


def get_document_for_candidate(
    document_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> Document:
    document = database.get(Document, document_id)

    if document is None or document.candidate_profile_id != candidate_profile_id:
        raise CVVersionServiceError(
            "Document was not found.",
            status_code=404,
        )

    return document


def validate_original_document(document: Document) -> None:
    if document.upload_status != "validated":
        raise CVVersionServiceError(
            "Only validated documents can be adopted as original CV versions.",
            status_code=400,
        )

    if document.document_type != "original_cv":
        raise CVVersionServiceError(
            "Only original CV documents can be adopted as original versions.",
            status_code=400,
        )


def get_cv_version_or_404(
    version_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> CVVersion:
    version = database.get(CVVersion, version_id)

    if version is None or version.candidate_profile_id != candidate_profile_id:
        raise CVVersionServiceError(
            "CV version was not found.",
            status_code=404,
        )

    return version


def list_cv_versions(
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> list[CVVersion]:
    return list(
        database.scalars(
            select(CVVersion)
            .where(CVVersion.candidate_profile_id == candidate_profile_id)
            .order_by(CVVersion.created_at.desc(), CVVersion.id.desc())
        ).all()
    )


def get_original_version_for_document(
    document_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> CVVersion | None:
    return database.scalars(
        select(CVVersion).where(
            CVVersion.candidate_profile_id == candidate_profile_id,
            CVVersion.version_type == "original",
            CVVersion.source_document_id == document_id,
        )
    ).first()


def clear_primary_for_type(
    database: Session,
    *,
    candidate_profile_id: int,
    version_type: str,
    now: datetime,
) -> None:
    database.execute(
        update(CVVersion)
        .where(
            CVVersion.candidate_profile_id == candidate_profile_id,
            CVVersion.version_type == version_type,
            CVVersion.is_primary.is_(True),
        )
        .values(is_primary=False, updated_at=now)
    )


def commit_version_change(
    database: Session,
    message: str,
    *,
    refresh: CVVersion | None = None,
) -> CVVersion | None:
    try:
        database.commit()

        if refresh is not None:
            database.refresh(refresh)

        return refresh
    except Exception as exc:
        database.rollback()
        raise CVVersionServiceError(message, status_code=500) from exc


def validate_status_for_primary(status: str) -> None:
    if status == "archived":
        raise CVVersionServiceError(
            "Archived CV versions cannot be primary.",
            status_code=400,
        )

    if status == "failed":
        raise CVVersionServiceError(
            "Failed CV versions cannot be primary.",
            status_code=400,
        )


def validate_create_status(status: str, *, is_primary: bool) -> None:
    if status == "archived":
        raise CVVersionServiceError(
            "Use the archive action to archive CV versions.",
            status_code=400,
        )

    if is_primary:
        validate_status_for_primary(status)


def validate_existing_parent_chain(
    parent: CVVersion,
    database: Session,
) -> None:
    seen: set[int] = set()
    current: CVVersion | None = parent

    while current is not None:
        if current.id in seen:
            raise CVVersionServiceError(
                "Circular CV version ancestry is not allowed.",
                status_code=400,
            )

        seen.add(current.id)

        if current.parent_version_id is None:
            return

        next_parent = database.get(CVVersion, current.parent_version_id)

        if next_parent is None:
            raise CVVersionServiceError(
                "CV version ancestry is invalid.",
                status_code=400,
            )

        if next_parent.candidate_profile_id != current.candidate_profile_id:
            raise CVVersionServiceError(
                "Parent CV versions must belong to the same candidate.",
                status_code=400,
            )

        current = next_parent


def validate_parent_for_create(
    version_type: str,
    parent_version_id: int | None,
    database: Session,
    *,
    candidate_profile_id: int,
) -> CVVersion | None:
    allowed_parent_types = PARENT_TYPES_BY_VERSION_TYPE.get(version_type)

    if allowed_parent_types is None:
        if parent_version_id is not None:
            raise CVVersionServiceError(
                "Original CV versions cannot have a parent version.",
                status_code=400,
            )

        return None

    if parent_version_id is None:
        raise CVVersionServiceError(
            f"{version_type} CV versions require a parent version.",
            status_code=400,
        )

    parent = get_cv_version_or_404(
        parent_version_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    validate_existing_parent_chain(parent, database)

    if parent.version_type not in allowed_parent_types:
        raise CVVersionServiceError(
            "Parent CV version type is not valid for this version type.",
            status_code=400,
        )

    return parent


def build_original_version_from_document(
    document: Document,
    request: CVVersionAdoptRequest,
) -> CVVersion:
    return CVVersion(
        candidate_profile_id=document.candidate_profile_id,
        source_document_id=document.id,
        parent_version_id=None,
        version_type="original",
        status=request.status,
        display_name=request.display_name or document.original_filename,
        description=request.description,
        job_reference=None,
        is_primary=False,
        storage_path=None,
        mime_type=document.media_type,
        file_size=document.size_bytes,
        sha256=document.sha256_hash,
        created_at=current_utc_time(),
        updated_at=current_utc_time(),
        archived_at=None,
    )


def adopt_original_version_from_document(
    document_id: int,
    request: CVVersionAdoptRequest,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> CVVersion:
    require_candidate_profile(database, candidate_profile_id)
    document = get_document_for_candidate(
        document_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    validate_original_document(document)
    validate_create_status(request.status, is_primary=request.is_primary)

    existing = get_original_version_for_document(
        document.id,
        database,
        candidate_profile_id=candidate_profile_id,
    )

    if existing is not None:
        if request.is_primary and not existing.is_primary:
            return set_primary_cv_version(
                existing.id,
                database,
                candidate_profile_id=candidate_profile_id,
            )

        return existing

    version = build_original_version_from_document(document, request)

    try:
        database.add(version)
        database.flush()

        if request.is_primary:
            now = current_utc_time()
            clear_primary_for_type(
                database,
                candidate_profile_id=candidate_profile_id,
                version_type=version.version_type,
                now=now,
            )
            version.is_primary = True
            version.updated_at = now

        database.commit()
        database.refresh(version)
    except Exception as exc:
        database.rollback()
        raise CVVersionServiceError(
            "Failed to adopt original CV version.",
            status_code=500,
        ) from exc

    return version


def validate_source_document_for_create(
    data: CVVersionCreate,
    database: Session,
    *,
    candidate_profile_id: int,
) -> Document | None:
    if data.version_type != "original":
        if data.source_document_id is not None:
            raise CVVersionServiceError(
                "Only original CV versions can reference source documents.",
                status_code=400,
            )

        return None

    if data.source_document_id is None:
        raise CVVersionServiceError(
            "Original CV versions require a source document.",
            status_code=400,
        )

    document = get_document_for_candidate(
        data.source_document_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    validate_original_document(document)
    return document


def create_cv_version(
    data: CVVersionCreate,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> CVVersion:
    require_candidate_profile(database, candidate_profile_id)
    validate_create_status(data.status, is_primary=data.is_primary)
    document = validate_source_document_for_create(
        data,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    parent = validate_parent_for_create(
        data.version_type,
        data.parent_version_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )

    if document is not None:
        existing = get_original_version_for_document(
            document.id,
            database,
            candidate_profile_id=candidate_profile_id,
        )

        if existing is not None:
            if data.is_primary and not existing.is_primary:
                return set_primary_cv_version(
                    existing.id,
                    database,
                    candidate_profile_id=candidate_profile_id,
                )

            return existing

    version = CVVersion(
        candidate_profile_id=candidate_profile_id,
        source_document_id=document.id if document else None,
        parent_version_id=parent.id if parent else None,
        version_type=data.version_type,
        status=data.status,
        display_name=data.display_name,
        description=data.description,
        job_reference=data.job_reference,
        is_primary=False,
        storage_path=None,
        mime_type=document.media_type if document else data.mime_type,
        file_size=document.size_bytes if document else data.file_size,
        sha256=document.sha256_hash if document else data.sha256,
        created_at=current_utc_time(),
        updated_at=current_utc_time(),
        archived_at=None,
    )

    try:
        database.add(version)
        database.flush()

        if data.is_primary:
            now = current_utc_time()
            clear_primary_for_type(
                database,
                candidate_profile_id=candidate_profile_id,
                version_type=version.version_type,
                now=now,
            )
            version.is_primary = True
            version.updated_at = now

        database.commit()
        database.refresh(version)
    except Exception as exc:
        database.rollback()
        raise CVVersionServiceError(
            "Failed to create CV version.",
            status_code=500,
        ) from exc

    return version


def update_cv_version(
    version_id: int,
    data: CVVersionUpdate,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> CVVersion:
    version = get_cv_version_or_404(
        version_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    fields = data.model_fields_set

    if (
        "parent_version_id" in fields
        and data.parent_version_id == version.id
    ):
        raise CVVersionServiceError(
            "A CV version cannot be its own parent.",
            status_code=400,
        )

    if IMMUTABLE_UPDATE_FIELDS.intersection(fields):
        raise CVVersionServiceError(
            "CV version relationship fields cannot be modified.",
            status_code=400,
        )

    if "status" in fields and data.status == "archived":
        raise CVVersionServiceError(
            "Use the archive action to archive CV versions.",
            status_code=400,
        )

    if "display_name" in fields:
        if data.display_name is None:
            raise CVVersionServiceError(
                "Display name cannot be cleared.",
                status_code=400,
            )

        version.display_name = data.display_name

    if "description" in fields:
        version.description = data.description

    if "job_reference" in fields:
        version.job_reference = data.job_reference

    if "status" in fields and data.status is not None:
        version.status = data.status

        if data.status == "failed":
            version.is_primary = False

    version.updated_at = current_utc_time()
    updated = commit_version_change(
        database,
        "Failed to update CV version.",
        refresh=version,
    )
    assert updated is not None
    return updated


def set_primary_cv_version(
    version_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> CVVersion:
    version = get_cv_version_or_404(
        version_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    validate_status_for_primary(version.status)
    now = current_utc_time()

    try:
        clear_primary_for_type(
            database,
            candidate_profile_id=candidate_profile_id,
            version_type=version.version_type,
            now=now,
        )
        version.is_primary = True
        version.updated_at = now
        database.commit()
        database.refresh(version)
    except Exception as exc:
        database.rollback()
        raise CVVersionServiceError(
            "Failed to set primary CV version.",
            status_code=500,
        ) from exc

    return version


def archive_cv_version(
    version_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> CVVersion:
    version = get_cv_version_or_404(
        version_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    now = current_utc_time()
    version.status = "archived"
    version.is_primary = False
    version.archived_at = version.archived_at or now
    version.updated_at = now

    archived = commit_version_change(
        database,
        "Failed to archive CV version.",
        refresh=version,
    )
    assert archived is not None
    return archived


def list_child_versions(
    version_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> list[CVVersion]:
    return list(
        database.scalars(
            select(CVVersion)
            .where(
                CVVersion.candidate_profile_id == candidate_profile_id,
                CVVersion.parent_version_id == version_id,
            )
            .order_by(CVVersion.created_at.asc(), CVVersion.id.asc())
        ).all()
    )


def delete_cv_version(
    version_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> None:
    version = get_cv_version_or_404(
        version_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    children = list_child_versions(
        version.id,
        database,
        candidate_profile_id=candidate_profile_id,
    )

    if children:
        raise CVVersionServiceError(
            "CV versions with child history cannot be deleted.",
            status_code=400,
        )

    try:
        database.delete(version)
        database.commit()
    except Exception as exc:
        database.rollback()
        raise CVVersionServiceError(
            "Failed to delete CV version.",
            status_code=500,
        ) from exc


def get_cv_version_ancestry(
    version: CVVersion,
    database: Session,
) -> list[CVVersion]:
    ancestry: list[CVVersion] = []
    seen: set[int] = set()
    current: CVVersion | None = version

    while current is not None:
        if current.id in seen:
            raise CVVersionServiceError(
                "Circular CV version ancestry is not allowed.",
                status_code=400,
            )

        seen.add(current.id)
        ancestry.append(current)

        if current.parent_version_id is None:
            break

        parent = database.get(CVVersion, current.parent_version_id)

        if parent is None:
            raise CVVersionServiceError(
                "CV version ancestry is invalid.",
                status_code=400,
            )

        if parent.candidate_profile_id != version.candidate_profile_id:
            raise CVVersionServiceError(
                "Parent CV versions must belong to the same candidate.",
                status_code=400,
            )

        current = parent

    return list(reversed(ancestry))


def get_cv_version_history(
    version_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> dict[str, object]:
    version = get_cv_version_or_404(
        version_id,
        database,
        candidate_profile_id=candidate_profile_id,
    )
    ancestry = get_cv_version_ancestry(version, database)
    children = list_child_versions(
        version.id,
        database,
        candidate_profile_id=candidate_profile_id,
    )

    return {
        "version": version,
        "ancestry": ancestry,
        "children": children,
    }
