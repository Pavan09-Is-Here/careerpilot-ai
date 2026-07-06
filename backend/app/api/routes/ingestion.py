from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.ingestion import (
    IngestionRunPageResponse,
    IngestionRunResponse,
    IngestionRunStatus,
    SourceSnapshotPageResponse,
)
from app.services.ingestion import (
    IngestionServiceError,
    get_ingestion_run_or_404,
    list_ingestion_runs,
    list_run_snapshots,
)
from app.services.provider_greenhouse import (
    GreenhouseAdapterError,
    ingest_greenhouse_source,
)


router = APIRouter(
    tags=["Ingestion"],
)


def raise_ingestion_http_error(error: IngestionServiceError) -> None:
    raise HTTPException(
        status_code=error.status_code,
        detail=error.safe_message,
    ) from error


@router.post(
    "/job-sources/{source_id}/ingest",
    response_model=IngestionRunResponse,
    status_code=201,
)
def trigger_source_ingestion(
    source_id: int,
    database: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> IngestionRunResponse:
    try:
        return ingest_greenhouse_source(source_id, database)
    except GreenhouseAdapterError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc


@router.get(
    "/ingestion-runs",
    response_model=IngestionRunPageResponse,
)
def list_ingestion_run_metadata(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    source_id: int | None = Query(default=None, gt=0, alias="source"),
    run_status: IngestionRunStatus | None = Query(default=None),
    database: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        return list_ingestion_runs(
            database,
            page=page,
            page_size=page_size,
            source_id=source_id,
            run_status=run_status,
        )
    except IngestionServiceError as exc:
        raise_ingestion_http_error(exc)


@router.get(
    "/ingestion-runs/{run_id}",
    response_model=IngestionRunResponse,
)
def get_ingestion_run_metadata(
    run_id: int,
    database: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> IngestionRunResponse:
    try:
        return get_ingestion_run_or_404(run_id, database)
    except IngestionServiceError as exc:
        raise_ingestion_http_error(exc)


@router.get(
    "/ingestion-runs/{run_id}/snapshots",
    response_model=SourceSnapshotPageResponse,
)
def list_ingestion_run_snapshot_metadata(
    run_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    database: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> dict[str, object]:
    try:
        return list_run_snapshots(
            run_id,
            database,
            page=page,
            page_size=page_size,
        )
    except IngestionServiceError as exc:
        raise_ingestion_http_error(exc)
