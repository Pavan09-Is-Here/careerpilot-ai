from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id
from app.core.database import get_db
from app.schemas.saved_job import (
    SavedJobCreate,
    SavedJobPageResponse,
    SavedJobResponse,
    SavedJobReviewStatus,
    SavedJobUpdate,
)
from app.services.saved_job import (
    SavedJobServiceError,
    build_saved_job_payload,
    create_saved_job,
    get_saved_job_or_404,
    list_saved_jobs,
    update_saved_job,
)


router = APIRouter(
    tags=["Saved Jobs"],
)


def raise_saved_job_http_error(error: SavedJobServiceError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.post(
    "/saved-jobs",
    response_model=SavedJobResponse,
    status_code=201,
)
def save_job(
    payload: SavedJobCreate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    try:
        return create_saved_job(payload, database, profile_id)
    except SavedJobServiceError as exc:
        raise_saved_job_http_error(exc)


@router.get(
    "/saved-jobs",
    response_model=SavedJobPageResponse,
)
def list_saved_job_records(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    review_status: SavedJobReviewStatus | None = Query(default=None),
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    try:
        return list_saved_jobs(
            database,
            candidate_profile_id=profile_id,
            page=page,
            page_size=page_size,
            review_status=review_status,
        )
    except SavedJobServiceError as exc:
        raise_saved_job_http_error(exc)


@router.get(
    "/saved-jobs/{saved_job_id}",
    response_model=SavedJobResponse,
)
def get_saved_job_record(
    saved_job_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    try:
        saved = get_saved_job_or_404(saved_job_id, database, profile_id)
        return build_saved_job_payload(saved, database)
    except SavedJobServiceError as exc:
        raise_saved_job_http_error(exc)


@router.patch(
    "/saved-jobs/{saved_job_id}",
    response_model=SavedJobResponse,
)
def update_saved_job_record(
    saved_job_id: int,
    payload: SavedJobUpdate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    try:
        return update_saved_job(saved_job_id, payload, database, profile_id)
    except SavedJobServiceError as exc:
        raise_saved_job_http_error(exc)
