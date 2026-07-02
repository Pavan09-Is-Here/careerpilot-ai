from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.worker import (
    AuditLevel,
    AuditLogPageResponse,
    WorkerName,
    WorkerStartRequest,
    WorkerStartResponse,
    WorkerStatusResponse,
)
from app.services.worker import (
    WorkerServiceError,
    all_worker_health,
    list_audit_log,
    run_all_workers,
    run_worker,
)


router = APIRouter(
    tags=["Workers"],
)


@router.post(
    "/workers/start",
    response_model=WorkerStartResponse,
    status_code=201,
)
def start_workers(
    payload: WorkerStartRequest | None = None,
    database: Session = Depends(get_db),
) -> dict[str, object]:
    request = payload or WorkerStartRequest()
    try:
        if request.worker == "all":
            runs = run_all_workers(database)
        else:
            runs = [run_worker(request.worker, database)]
    except WorkerServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.safe_message,
        ) from exc

    return {"runs": runs}


@router.get(
    "/workers/status",
    response_model=WorkerStatusResponse,
)
def get_worker_status(
    database: Session = Depends(get_db),
) -> dict[str, object]:
    return {"workers": all_worker_health(database)}


@router.get(
    "/audit-log",
    response_model=AuditLogPageResponse,
)
def get_audit_log(
    worker: WorkerName | None = Query(default=None),
    level: AuditLevel | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    database: Session = Depends(get_db),
) -> dict[str, object]:
    return list_audit_log(
        database,
        worker=worker,
        level=level,
        limit=limit,
        offset=offset,
    )
