from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.cv_version import CVVersionArtifactResponse
from app.services.cv_version import CVVersionServiceError
from app.services.verified_master_cv import (
    get_cv_version_artifact_or_404,
    resolve_artifact_download_path,
)


router = APIRouter(
    prefix="/cv-artifacts",
    tags=["CV Artifacts"],
)


def raise_artifact_http_error(error: CVVersionServiceError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.get(
    "/{artifact_id}",
    response_model=CVVersionArtifactResponse,
)
def get_generated_cv_artifact_metadata(
    artifact_id: int,
    database: Session = Depends(get_db),
) -> CVVersionArtifactResponse:
    try:
        return get_cv_version_artifact_or_404(artifact_id, database)
    except CVVersionServiceError as exc:
        raise_artifact_http_error(exc)


@router.get(
    "/{artifact_id}/download",
)
def download_generated_cv_artifact(
    artifact_id: int,
    database: Session = Depends(get_db),
) -> FileResponse:
    try:
        artifact = get_cv_version_artifact_or_404(artifact_id, database)
        artifact_path = resolve_artifact_download_path(artifact)
    except CVVersionServiceError as exc:
        raise_artifact_http_error(exc)

    return FileResponse(
        path=artifact_path,
        media_type=artifact.mime_type,
        filename=artifact.safe_filename,
    )
