from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id
from app.core.database import get_db
from app.schemas.application_package import (
    ApplicationPackageResponse,
    ApplicationPackageUpdate,
)
from app.services.application_package import (
    ApplicationPackageServiceError,
    build_package_response,
    get_package_or_404,
    prepare_application_package,
    update_application_package,
)


router = APIRouter(
    tags=["Application Packages"],
)


def raise_package_http_error(
    error: ApplicationPackageServiceError,
) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.post(
    "/jobs/{job_id}/prepare-application",
    response_model=ApplicationPackageResponse,
    status_code=201,
)
def prepare_application(
    job_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    try:
        package = prepare_application_package(job_id, database, profile_id)
        return build_package_response(package, database, profile_id)
    except ApplicationPackageServiceError as exc:
        raise_package_http_error(exc)


@router.get(
    "/jobs/{job_id}/application-package",
    response_model=ApplicationPackageResponse,
)
def get_application_package(
    job_id: int,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    try:
        package = get_package_or_404(job_id, database, profile_id)
        return build_package_response(package, database, profile_id)
    except ApplicationPackageServiceError as exc:
        raise_package_http_error(exc)


@router.put(
    "/jobs/{job_id}/application-package",
    response_model=ApplicationPackageResponse,
)
def update_application_package_record(
    job_id: int,
    payload: ApplicationPackageUpdate,
    database: Session = Depends(get_db),
    profile_id: int = Depends(get_current_profile_id),
) -> dict[str, object]:
    try:
        package = update_application_package(
            job_id,
            payload,
            database,
            profile_id,
        )
        return build_package_response(package, database, profile_id)
    except ApplicationPackageServiceError as exc:
        raise_package_http_error(exc)
