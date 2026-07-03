from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_profile_id
from app.core.database import get_db
from app.schemas.auth import DeleteRequest
from app.services.privacy import (
    PrivacyServiceError,
    delete_candidate_data,
    export_candidate_data,
)


router = APIRouter(
    prefix="/privacy",
    tags=["Privacy"],
)


def raise_privacy_http_error(error: PrivacyServiceError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.get("/export")
def export_data(
    profile_id: int = Depends(get_current_profile_id),
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return export_candidate_data(database, profile_id)
    except PrivacyServiceError as exc:
        raise_privacy_http_error(exc)


@router.post("/delete")
def delete_data(
    payload: DeleteRequest,
    profile_id: int = Depends(get_current_profile_id),
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return delete_candidate_data(
            database,
            profile_id,
            confirm=payload.confirm,
        )
    except PrivacyServiceError as exc:
        raise_privacy_http_error(exc)
