from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_session
from app.core.database import get_db
from app.models.auth import AuthSession
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
    _session: AuthSession = Depends(get_current_session),
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return export_candidate_data(database)
    except PrivacyServiceError as exc:
        raise_privacy_http_error(exc)


@router.post("/delete")
def delete_data(
    payload: DeleteRequest,
    _session: AuthSession = Depends(get_current_session),
    database: Session = Depends(get_db),
) -> dict[str, object]:
    try:
        return delete_candidate_data(
            database,
            confirm=payload.confirm,
        )
    except PrivacyServiceError as exc:
        raise_privacy_http_error(exc)
