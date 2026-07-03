"""Saved jobs and candidate review workflow (Phase 4.5).

Candidates save discovered jobs and move them through a validated
review workflow. Records are archived, never deleted, and the
underlying normalized jobs are protected from deletion so removed,
expired, unavailable, and stale jobs stay inspectable.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job import NormalizedJob
from app.models.saved_job import SavedJob
from app.schemas.saved_job import SavedJobCreate, SavedJobUpdate
from app.services.job import (
    JobServiceError,
    build_job_list_item,
    paginate_scalars,
    validate_text,
)


REVIEW_STATUS_TRANSITIONS: dict[str, set[str]] = {
    "saved": {"shortlisted", "dismissed", "archived"},
    "shortlisted": {"saved", "dismissed", "archived"},
    "dismissed": {"saved", "archived"},
    "archived": set(),
}


class SavedJobServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def validate_notes(notes: str | None) -> None:
    try:
        validate_text("Saved job notes", notes, max_length=2000)
    except JobServiceError as exc:
        raise SavedJobServiceError(exc.safe_message) from exc


def validate_review_transition(
    current_status: str,
    next_status: str,
) -> None:
    if current_status == next_status:
        return

    allowed = REVIEW_STATUS_TRANSITIONS.get(current_status, set())
    if next_status not in allowed:
        raise SavedJobServiceError(
            "Saved job review transition is not allowed.",
        )


def get_saved_job_or_404(
    saved_job_id: int,
    database: Session,
    candidate_profile_id: int,
) -> SavedJob:
    saved = database.get(SavedJob, saved_job_id)
    if saved is None or saved.candidate_profile_id != candidate_profile_id:
        raise SavedJobServiceError(
            "Saved job was not found.",
            status_code=404,
        )
    return saved


def build_saved_job_payload(
    saved: SavedJob,
    database: Session,
) -> dict[str, object]:
    job = database.get(NormalizedJob, saved.job_id)
    if job is None:
        raise SavedJobServiceError("Job was not found.", status_code=404)

    return {
        "id": saved.id,
        "job_id": saved.job_id,
        "review_status": saved.review_status,
        "notes": saved.notes,
        "status_changed_at": saved.status_changed_at,
        "created_at": saved.created_at,
        "updated_at": saved.updated_at,
        "job": build_job_list_item(job),
    }


def create_saved_job(
    data: SavedJobCreate,
    database: Session,
    candidate_profile_id: int,
) -> dict[str, object]:
    job = database.get(NormalizedJob, data.job_id)
    if job is None:
        raise SavedJobServiceError(
            "Job was not found.",
            status_code=404,
        )

    validate_notes(data.notes)

    now = current_utc_time()
    saved = SavedJob(
        candidate_profile_id=candidate_profile_id,
        job_id=job.id,
        review_status="saved",
        notes=data.notes,
        status_changed_at=now,
        created_at=now,
        updated_at=now,
    )
    database.add(saved)

    try:
        database.commit()
        database.refresh(saved)
    except IntegrityError as exc:
        database.rollback()
        raise SavedJobServiceError(
            "Job is already saved.",
            status_code=409,
        ) from exc

    return build_saved_job_payload(saved, database)


def update_saved_job(
    saved_job_id: int,
    data: SavedJobUpdate,
    database: Session,
    candidate_profile_id: int,
) -> dict[str, object]:
    saved = get_saved_job_or_404(
        saved_job_id,
        database,
        candidate_profile_id,
    )
    now = current_utc_time()

    if data.review_status is not None:
        validate_review_transition(
            saved.review_status,
            data.review_status,
        )
        if saved.review_status != data.review_status:
            saved.review_status = data.review_status
            saved.status_changed_at = now

    if data.notes is not None:
        validate_notes(data.notes)
        saved.notes = data.notes

    saved.updated_at = now

    try:
        database.commit()
        database.refresh(saved)
    except IntegrityError as exc:
        database.rollback()
        raise SavedJobServiceError(
            "Saved job could not be updated.",
            status_code=409,
        ) from exc

    return build_saved_job_payload(saved, database)


def list_saved_jobs(
    database: Session,
    *,
    candidate_profile_id: int,
    page: int = 1,
    page_size: int = 50,
    review_status: str | None = None,
) -> dict[str, object]:
    statement = select(SavedJob).where(
        SavedJob.candidate_profile_id == candidate_profile_id
    )

    if review_status is not None:
        statement = statement.where(
            SavedJob.review_status == review_status
        )

    statement = statement.order_by(
        SavedJob.updated_at.desc(),
        SavedJob.id.desc(),
    )

    try:
        result = paginate_scalars(
            statement,
            database,
            page=page,
            page_size=page_size,
        )
    except JobServiceError as exc:
        raise SavedJobServiceError(exc.safe_message) from exc

    return {
        "items": [
            build_saved_job_payload(saved, database)
            for saved in result.items
            if isinstance(saved, SavedJob)
        ],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
    }
