from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id, get_settings
from app.core.database import get_db
from app.models.application_run import ApplicationRun
from app.schemas.application_run import (
    ApplicationRunResponse,
    ApplicationRunResumeRequest,
    ApplicationRunStartRequest,
)
from app.services.application_run import (
    ApplicationRunServiceError,
    cancel_application_run,
    get_run_or_404,
    resume_application_run,
    start_application_run,
)


router = APIRouter(
    tags=["Application Runs"],
)


def raise_run_http_error(error: ApplicationRunServiceError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.post(
    "/jobs/{job_id}/apply",
    response_model=ApplicationRunResponse,
    status_code=201,
)
def start_application(
    job_id: int,
    payload: ApplicationRunStartRequest | None = None,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> ApplicationRun:
    options = payload or ApplicationRunStartRequest()
    try:
        return start_application_run(
            job_id,
            database,
            profile_id,
            driver=options.driver,
            acknowledged_gates=list(options.acknowledged_gates),
            settings=get_settings(),
        )
    except ApplicationRunServiceError as exc:
        raise_run_http_error(exc)


@router.get(
    "/application-runs/{run_id}/status",
    response_model=ApplicationRunResponse,
)
def get_application_status(
    run_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> ApplicationRun:
    try:
        return get_run_or_404(run_id, database, profile_id)
    except ApplicationRunServiceError as exc:
        raise_run_http_error(exc)


@router.post(
    "/application-runs/{run_id}/resume",
    response_model=ApplicationRunResponse,
)
def resume_application(
    run_id: int,
    payload: ApplicationRunResumeRequest,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> ApplicationRun:
    try:
        return resume_application_run(
            run_id,
            payload.confirmation_number,
            database,
            profile_id,
            settings=get_settings(),
        )
    except ApplicationRunServiceError as exc:
        raise_run_http_error(exc)


@router.post(
    "/application-runs/{run_id}/cancel",
    response_model=ApplicationRunResponse,
)
def cancel_application(
    run_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> ApplicationRun:
    try:
        return cancel_application_run(run_id, database, profile_id)
    except ApplicationRunServiceError as exc:
        raise_run_http_error(exc)
