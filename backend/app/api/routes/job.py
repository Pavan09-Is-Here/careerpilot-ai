from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.job import (
    JobEmploymentType,
    JobLifecycleStatus,
    JobRemoteMode,
    JobSourcePageResponse,
    JobSourceResponse,
    NormalizedJobDetailResponse,
    NormalizedJobPageResponse,
)
from app.services.job import (
    JobServiceError,
    get_job_source_or_404,
    get_normalized_job_or_404,
    list_job_sources,
    list_normalized_jobs,
    build_job_detail,
)


router = APIRouter(
    tags=["Jobs"],
)


def raise_job_http_error(error: JobServiceError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.get(
    "/job-sources",
    response_model=JobSourcePageResponse,
)
def list_job_source_metadata(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return list_job_sources(
            database,
            page=page,
            page_size=page_size,
        )
    except JobServiceError as exc:
        raise_job_http_error(exc)


@router.get(
    "/job-sources/{source_id}",
    response_model=JobSourceResponse,
)
def get_job_source_metadata(
    source_id: int,
    database: Session = Depends(get_db),
) -> JobSourceResponse:
    try:
        return get_job_source_or_404(source_id, database)
    except JobServiceError as exc:
        raise_job_http_error(exc)


@router.get(
    "/jobs",
    response_model=NormalizedJobPageResponse,
)
def list_job_metadata(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    source_id: int | None = Query(default=None, gt=0, alias="source"),
    lifecycle_status: JobLifecycleStatus | None = Query(default=None),
    employer: str | None = Query(default=None, min_length=1, max_length=250),
    employment_type: JobEmploymentType | None = Query(default=None),
    remote_mode: JobRemoteMode | None = Query(default=None),
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return list_normalized_jobs(
            database,
            page=page,
            page_size=page_size,
            source_id=source_id,
            lifecycle_status=lifecycle_status,
            employer=employer,
            employment_type=employment_type,
            remote_mode=remote_mode,
        )
    except JobServiceError as exc:
        raise_job_http_error(exc)


@router.get(
    "/jobs/{job_id}",
    response_model=NormalizedJobDetailResponse,
)
def get_job_metadata(
    job_id: int,
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        job = get_normalized_job_or_404(job_id, database)
        return build_job_detail(job, database)
    except JobServiceError as exc:
        raise_job_http_error(exc)
