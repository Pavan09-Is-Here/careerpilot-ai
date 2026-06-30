from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.cv_version import (
    CVVersionCreate,
    CVVersionHistoryResponse,
    CVVersionResponse,
    CVVersionUpdate,
)
from app.services.cv_version import (
    CVVersionServiceError,
    archive_cv_version,
    create_cv_version,
    delete_cv_version,
    get_cv_version_history,
    get_cv_version_or_404,
    list_cv_versions,
    set_primary_cv_version,
    update_cv_version,
)


router = APIRouter(
    prefix="/cv-versions",
    tags=["CV Versions"],
)


def raise_cv_version_http_error(error: CVVersionServiceError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.post(
    "",
    response_model=CVVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cv_version_metadata(
    data: CVVersionCreate,
    database: Session = Depends(get_db),
) -> CVVersionResponse:
    try:
        return create_cv_version(data, database)
    except CVVersionServiceError as exc:
        raise_cv_version_http_error(exc)


@router.get(
    "",
    response_model=list[CVVersionResponse],
)
def list_cv_version_metadata(
    database: Session = Depends(get_db),
) -> list[CVVersionResponse]:
    return list_cv_versions(database)


@router.get(
    "/{version_id}",
    response_model=CVVersionResponse,
)
def get_cv_version_metadata(
    version_id: int,
    database: Session = Depends(get_db),
) -> CVVersionResponse:
    try:
        return get_cv_version_or_404(version_id, database)
    except CVVersionServiceError as exc:
        raise_cv_version_http_error(exc)


@router.patch(
    "/{version_id}",
    response_model=CVVersionResponse,
)
def update_cv_version_metadata(
    version_id: int,
    data: CVVersionUpdate,
    database: Session = Depends(get_db),
) -> CVVersionResponse:
    try:
        return update_cv_version(version_id, data, database)
    except CVVersionServiceError as exc:
        raise_cv_version_http_error(exc)


@router.patch(
    "/{version_id}/primary",
    response_model=CVVersionResponse,
)
def set_primary_cv_version_metadata(
    version_id: int,
    database: Session = Depends(get_db),
) -> CVVersionResponse:
    try:
        return set_primary_cv_version(version_id, database)
    except CVVersionServiceError as exc:
        raise_cv_version_http_error(exc)


@router.patch(
    "/{version_id}/archive",
    response_model=CVVersionResponse,
)
def archive_cv_version_metadata(
    version_id: int,
    database: Session = Depends(get_db),
) -> CVVersionResponse:
    try:
        return archive_cv_version(version_id, database)
    except CVVersionServiceError as exc:
        raise_cv_version_http_error(exc)


@router.delete(
    "/{version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_cv_version_metadata(
    version_id: int,
    database: Session = Depends(get_db),
) -> Response:
    try:
        delete_cv_version(version_id, database)
    except CVVersionServiceError as exc:
        raise_cv_version_http_error(exc)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{version_id}/history",
    response_model=CVVersionHistoryResponse,
)
def get_cv_version_history_metadata(
    version_id: int,
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return get_cv_version_history(version_id, database)
    except CVVersionServiceError as exc:
        raise_cv_version_http_error(exc)
