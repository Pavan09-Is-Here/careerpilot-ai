from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.application import Application
from app.schemas.application import (
    ApplicationDetailResponse,
    ApplicationFollowUpCreate,
    ApplicationNoteCreate,
    ApplicationResponse,
    ApplicationStatus,
    ApplicationUpdate,
)
from app.services.application import (
    ApplicationServiceError,
    add_follow_up,
    add_note,
    build_detail,
    get_application_or_404,
    list_applications,
    track_application,
    update_application,
)


router = APIRouter(
    tags=["Applications"],
)


def raise_application_http_error(
    error: ApplicationServiceError,
) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.post(
    "/jobs/{job_id}/track",
    response_model=ApplicationResponse,
    status_code=201,
)
def track_job_application(
    job_id: int,
    database: Session = Depends(get_db),
) -> Application:
    try:
        return track_application(job_id, database)
    except ApplicationServiceError as exc:
        raise_application_http_error(exc)


@router.get(
    "/applications",
    response_model=list[ApplicationResponse],
)
def list_all_applications(
    status: ApplicationStatus | None = Query(default=None),
    database: Session = Depends(get_db),
) -> list[Application]:
    return list(list_applications(database, status=status))


@router.get(
    "/applications/{application_id}",
    response_model=ApplicationDetailResponse,
)
def get_application_detail(
    application_id: int,
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        application = get_application_or_404(application_id, database)
        return build_detail(application, database)
    except ApplicationServiceError as exc:
        raise_application_http_error(exc)


@router.put(
    "/applications/{application_id}",
    response_model=ApplicationResponse,
)
def update_application_record(
    application_id: int,
    payload: ApplicationUpdate,
    database: Session = Depends(get_db),
) -> Application:
    try:
        return update_application(application_id, payload, database)
    except ApplicationServiceError as exc:
        raise_application_http_error(exc)


@router.post(
    "/applications/{application_id}/notes",
    response_model=ApplicationResponse,
    status_code=201,
)
def add_application_note(
    application_id: int,
    payload: ApplicationNoteCreate,
    database: Session = Depends(get_db),
) -> Application:
    try:
        return add_note(application_id, payload, database)
    except ApplicationServiceError as exc:
        raise_application_http_error(exc)


@router.post(
    "/applications/{application_id}/follow-up",
    response_model=ApplicationResponse,
    status_code=201,
)
def add_application_follow_up(
    application_id: int,
    payload: ApplicationFollowUpCreate,
    database: Session = Depends(get_db),
) -> Application:
    try:
        return add_follow_up(application_id, payload, database)
    except ApplicationServiceError as exc:
        raise_application_http_error(exc)
