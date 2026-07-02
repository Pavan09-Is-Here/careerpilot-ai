from datetime import datetime, timedelta, timezone
import re

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.ingestion import IngestionRun, SourceSnapshot
from app.models.job import JobSource
from app.schemas.ingestion import (
    IngestionRunCompletion,
    IngestionRunCreate,
    SourceSnapshotCreate,
)
from app.services.job import (
    MAX_RETENTION_DAYS,
    JobServiceError,
    Page,
    paginate_scalars,
    validate_text,
)


MEDIA_TYPE_RE = re.compile(
    r"^[a-z0-9][a-z0-9!#$&^_.+-]{0,62}/[a-z0-9][a-z0-9!#$&^_.+-]{0,62}$"
)
STORAGE_REFERENCE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,299}$")
RUN_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"running", "cancelled"},
    "running": {"succeeded", "failed", "cancelled"},
    "succeeded": set(),
    "failed": set(),
    "cancelled": set(),
}


class IngestionServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def get_settings() -> Settings:
    return Settings()


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def validate_failure_summary(summary: str | None) -> None:
    try:
        validate_text(
            "Ingestion failure summary",
            summary,
            max_length=1000,
        )
    except JobServiceError as exc:
        raise IngestionServiceError(exc.safe_message) from exc


def validate_payload_media_type(media_type: str) -> None:
    if not MEDIA_TYPE_RE.fullmatch(media_type):
        raise IngestionServiceError(
            "Snapshot payload media type is invalid.",
        )


def validate_storage_reference(reference: str | None) -> None:
    if reference is None:
        return

    if not STORAGE_REFERENCE_RE.fullmatch(reference):
        raise IngestionServiceError(
            "Snapshot storage reference is invalid.",
        )


def validate_payload_size(size_bytes: int) -> None:
    max_bytes = get_settings().max_source_snapshot_payload_bytes
    if size_bytes < 0 or size_bytes > max_bytes:
        raise IngestionServiceError(
            "Snapshot payload size is outside the permitted bounds.",
        )


def validate_run_status_transition(
    current_status: str,
    next_status: str,
) -> None:
    allowed = RUN_STATUS_TRANSITIONS.get(current_status, set())
    if next_status not in allowed:
        raise IngestionServiceError(
            "Ingestion run status transition is not allowed.",
        )


def get_ingestion_run_or_404(
    run_id: int,
    database: Session,
) -> IngestionRun:
    run = database.get(IngestionRun, run_id)
    if run is None:
        raise IngestionServiceError(
            "Ingestion run was not found.",
            status_code=404,
        )
    return run


def create_ingestion_run(
    data: IngestionRunCreate,
    database: Session,
) -> IngestionRun:
    source = database.get(JobSource, data.job_source_id)
    if source is None:
        raise IngestionServiceError("Job source was not found.")

    if not source.enabled:
        raise IngestionServiceError(
            "Ingestion runs require an enabled job source.",
        )

    now = current_utc_time()
    run = IngestionRun(
        job_source_id=source.id,
        run_status="pending",
        created_at=now,
        updated_at=now,
    )
    database.add(run)

    try:
        database.commit()
        database.refresh(run)
    except IntegrityError as exc:
        database.rollback()
        raise IngestionServiceError(
            "Ingestion run could not be saved.",
            status_code=409,
        ) from exc

    return run


def start_ingestion_run(
    run_id: int,
    database: Session,
) -> IngestionRun:
    run = get_ingestion_run_or_404(run_id, database)
    validate_run_status_transition(run.run_status, "running")

    now = current_utc_time()
    run.run_status = "running"
    run.started_at = now
    run.updated_at = now

    try:
        database.commit()
        database.refresh(run)
    except IntegrityError as exc:
        database.rollback()
        raise IngestionServiceError(
            "Ingestion run could not be updated.",
            status_code=409,
        ) from exc

    return run


def complete_ingestion_run(
    run_id: int,
    data: IngestionRunCompletion,
    database: Session,
) -> IngestionRun:
    run = get_ingestion_run_or_404(run_id, database)
    validate_run_status_transition(run.run_status, data.run_status)

    if data.run_status == "failed" and not data.failure_summary:
        raise IngestionServiceError(
            "Failed ingestion runs require a failure summary.",
        )

    if data.run_status == "succeeded" and data.failure_summary:
        raise IngestionServiceError(
            "Succeeded ingestion runs cannot include a failure summary.",
        )

    validate_failure_summary(data.failure_summary)

    now = current_utc_time()
    run.run_status = data.run_status
    run.failure_summary = data.failure_summary
    run.jobs_discovered = data.jobs_discovered
    run.jobs_updated = data.jobs_updated
    run.finished_at = now
    if run.started_at is None:
        run.started_at = run.created_at
    run.updated_at = now

    try:
        database.commit()
        database.refresh(run)
    except IntegrityError as exc:
        database.rollback()
        raise IngestionServiceError(
            "Ingestion run could not be updated.",
            status_code=409,
        ) from exc

    return run


def compute_snapshot_expiry(
    fetched_at: datetime,
    source: JobSource,
    requested_expiry: datetime | None,
) -> datetime:
    if requested_expiry is None:
        return fetched_at + timedelta(
            days=source.configured_retention_days,
        )

    if requested_expiry <= fetched_at:
        raise IngestionServiceError(
            "Snapshot expiry must be after the fetch time.",
        )

    latest_allowed = fetched_at + timedelta(days=MAX_RETENTION_DAYS)
    if requested_expiry > latest_allowed:
        raise IngestionServiceError(
            "Snapshot expiry exceeds the maximum retention window.",
        )

    return requested_expiry


def record_source_snapshot(
    data: SourceSnapshotCreate,
    database: Session,
) -> SourceSnapshot:
    run = database.get(IngestionRun, data.ingestion_run_id)
    if run is None:
        raise IngestionServiceError("Ingestion run was not found.")

    if run.run_status != "running":
        raise IngestionServiceError(
            "Snapshots can only be recorded for running ingestion runs.",
        )

    source = database.get(JobSource, run.job_source_id)
    if source is None:
        raise IngestionServiceError("Job source was not found.")

    if not re.fullmatch(r"[0-9a-f]{64}", data.content_hash):
        raise IngestionServiceError(
            "Snapshot content hash must be a lowercase SHA-256 hex digest.",
        )

    validate_payload_size(data.payload_size_bytes)
    validate_payload_media_type(data.payload_media_type)
    validate_storage_reference(data.storage_reference)

    now = current_utc_time()
    fetched_at = data.fetched_at or now
    expires_at = compute_snapshot_expiry(
        fetched_at,
        source,
        data.expires_at,
    )

    snapshot = SourceSnapshot(
        ingestion_run_id=run.id,
        job_source_id=run.job_source_id,
        content_hash=data.content_hash,
        payload_size_bytes=data.payload_size_bytes,
        payload_media_type=data.payload_media_type,
        storage_reference=data.storage_reference,
        fetched_at=fetched_at,
        expires_at=expires_at,
        created_at=now,
    )
    run.snapshots_recorded = (  # type: ignore[assignment]
        IngestionRun.snapshots_recorded + 1
    )
    run.updated_at = now
    database.add(snapshot)

    try:
        database.commit()
        database.refresh(snapshot)
        database.refresh(run)
    except IntegrityError as exc:
        database.rollback()
        raise IngestionServiceError(
            "Snapshot could not be saved.",
            status_code=409,
        ) from exc

    return snapshot


def paginate_or_error(
    statement: object,
    database: Session,
    *,
    page: int,
    page_size: int,
) -> Page:
    try:
        return paginate_scalars(
            statement,
            database,
            page=page,
            page_size=page_size,
        )
    except JobServiceError as exc:
        raise IngestionServiceError(exc.safe_message) from exc


def cleanup_expired_source_snapshots(
    database: Session,
    *,
    now: datetime | None = None,
) -> int:
    """Delete expired snapshot metadata only.

    Never deletes ingestion runs, job sources, or normalized job
    provenance.
    """
    cutoff = now or current_utc_time()
    result = database.execute(
        delete(SourceSnapshot).where(SourceSnapshot.expires_at <= cutoff),
        execution_options={"synchronize_session": "fetch"},
    )
    database.commit()
    return int(result.rowcount or 0)


def list_ingestion_runs(
    database: Session,
    *,
    page: int = 1,
    page_size: int = 50,
    source_id: int | None = None,
    run_status: str | None = None,
) -> dict[str, object]:
    statement = select(IngestionRun)

    if source_id is not None:
        statement = statement.where(
            IngestionRun.job_source_id == source_id
        )

    if run_status is not None:
        statement = statement.where(
            IngestionRun.run_status == run_status
        )

    statement = statement.order_by(
        IngestionRun.created_at.desc(),
        IngestionRun.id.desc(),
    )

    result = paginate_or_error(
        statement,
        database,
        page=page,
        page_size=page_size,
    )
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }


def list_run_snapshots(
    run_id: int,
    database: Session,
    *,
    page: int = 1,
    page_size: int = 50,
) -> dict[str, object]:
    get_ingestion_run_or_404(run_id, database)

    statement = (
        select(SourceSnapshot)
        .where(SourceSnapshot.ingestion_run_id == run_id)
        .order_by(
            SourceSnapshot.fetched_at.desc(),
            SourceSnapshot.id.desc(),
        )
    )

    result = paginate_or_error(
        statement,
        database,
        page=page,
        page_size=page_size,
    )
    return {
        "items": result.items,
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }
