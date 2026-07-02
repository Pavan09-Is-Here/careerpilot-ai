"""Application tracking dashboard (Phase 11).

Tracks the candidate's application to each job: pipeline status,
submission confirmation, interview and outcome details, notes, and
follow-ups. Initial status is derived deterministically from the
existing pipeline (runs, packages, tailored CVs, matches). Status
changes follow a validated transition map. Nothing here fabricates
candidate information; it records what the candidate supplies or what
earlier phases already produced.
"""

from datetime import date, datetime, time, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.application_package import ApplicationPackage
from app.models.application_run import ApplicationRun
from app.models.job import NormalizedJob
from app.models.job_match import JobMatch
from app.schemas.application import (
    ApplicationFollowUpCreate,
    ApplicationNoteCreate,
    ApplicationUpdate,
)
from app.services.application_package import load_tailored_cv


CANDIDATE_PROFILE_ID = 1

TERMINAL_STATUSES = frozenset({"rejected", "withdrawn"})

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "discovered": {"analyzing", "not_eligible", "matched"},
    "analyzing": {"not_eligible", "matched"},
    "not_eligible": set(),
    "matched": {"cv_generated", "needs_review", "ready_to_apply"},
    "cv_generated": {"needs_review", "ready_to_apply"},
    "needs_review": {"ready_to_apply", "applying"},
    "ready_to_apply": {"applying", "blocked", "submitted"},
    "applying": {"blocked", "submitted"},
    "blocked": {"applying", "submitted"},
    "submitted": {"interview", "rejected", "offer"},
    "interview": {"interview", "rejected", "offer"},
    "rejected": set(),
    "offer": set(),
    "withdrawn": set(),
}

READINESS_TO_STATUS = {
    "ready_for_automatic_application": "ready_to_apply",
    "needs_user_review": "needs_review",
    "blocked_by_captcha": "blocked",
    "blocked_by_mfa": "blocked",
    "blocked_by_assessment": "blocked",
    "not_eligible": "not_eligible",
}

GATE_BLOCKED_REASONS = frozenset({"captcha", "mfa", "assessment"})


class ApplicationServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


# --- Status derivation ----------------------------------------------------


def latest_run(job_id: int, database: Session) -> ApplicationRun | None:
    return database.scalar(
        select(ApplicationRun)
        .where(ApplicationRun.job_id == job_id)
        .order_by(ApplicationRun.id.desc())
    )


def derive_initial_status(job_id: int, database: Session) -> str:
    run = latest_run(job_id, database)
    if run is not None:
        if run.status == "submitted":
            return "submitted"
        if run.status == "paused_for_gate":
            if run.pause_reason in GATE_BLOCKED_REASONS:
                return "blocked"
            return "applying"

    package = database.scalar(
        select(ApplicationPackage).where(
            ApplicationPackage.job_id == job_id
        )
    )
    if package is not None:
        mapped = READINESS_TO_STATUS.get(package.readiness_status)
        if mapped is not None:
            return mapped
        # blocked_by_missing_information falls through to earlier stages.

    if load_tailored_cv(job_id, database) is not None:
        return "cv_generated"

    match = database.scalar(
        select(JobMatch).where(JobMatch.job_id == job_id)
    )
    if match is not None:
        if match.eligibility_status == "ineligible":
            return "not_eligible"
        return "matched"

    return "discovered"


# --- Transitions ----------------------------------------------------------


def validate_transition(current: str, target: str) -> None:
    if current == target:
        return
    if target == "withdrawn" and current not in TERMINAL_STATUSES:
        return
    if target in ALLOWED_TRANSITIONS.get(current, set()):
        return
    raise ApplicationServiceError(
        f"Status transition from '{current}' to '{target}' is not "
        "allowed.",
    )


# --- Lookups --------------------------------------------------------------


def get_job_or_404(job_id: int, database: Session) -> NormalizedJob:
    job = database.get(NormalizedJob, job_id)
    if job is None:
        raise ApplicationServiceError(
            "Job was not found.",
            status_code=404,
        )
    return job


def get_application_or_404(
    application_id: int,
    database: Session,
) -> Application:
    application = database.get(Application, application_id)
    if (
        application is None
        or application.candidate_profile_id != CANDIDATE_PROFILE_ID
    ):
        raise ApplicationServiceError(
            "Application was not found.",
            status_code=404,
        )
    return application


# --- Commands -------------------------------------------------------------


def track_application(
    job_id: int,
    database: Session,
) -> Application:
    job = get_job_or_404(job_id, database)

    existing = database.scalar(
        select(Application).where(Application.job_id == job.id)
    )
    if existing is not None:
        return existing

    status = derive_initial_status(job.id, database)

    cv_id: int | None = None
    tailored = load_tailored_cv(job.id, database)
    if tailored is not None:
        version, _artifacts = tailored
        cv_id = version.id

    applied_at: datetime | None = None
    confirmation_number: str | None = None
    run = latest_run(job.id, database)
    if run is not None and run.status == "submitted":
        applied_at = run.submitted_at
        confirmation_number = run.confirmation_number

    now = current_utc_time()
    application = Application(
        job_id=job.id,
        candidate_profile_id=CANDIDATE_PROFILE_ID,
        cv_id=cv_id,
        status=status,
        applied_at=applied_at,
        confirmation_number=confirmation_number,
        notes=[],
        follow_ups=[],
        created_at=now,
        updated_at=now,
    )
    database.add(application)

    try:
        database.commit()
        database.refresh(application)
    except IntegrityError as exc:
        database.rollback()
        raise ApplicationServiceError(
            "This job is already tracked.",
            status_code=409,
        ) from exc

    return application


def list_applications(
    database: Session,
    *,
    status: str | None = None,
) -> list[Application]:
    statement = select(Application).where(
        Application.candidate_profile_id == CANDIDATE_PROFILE_ID
    )
    if status is not None:
        statement = statement.where(Application.status == status)

    statement = statement.order_by(
        Application.updated_at.desc(),
        Application.id.desc(),
    )
    return list(database.scalars(statement).all())


def update_application(
    application_id: int,
    data: ApplicationUpdate,
    database: Session,
) -> Application:
    application = get_application_or_404(application_id, database)
    fields = data.model_dump(exclude_unset=True)

    now = current_utc_time()
    previous_status = application.status
    became_submitted = False

    if "status" in fields and fields["status"] is not None:
        target = fields["status"]
        validate_transition(application.status, target)
        application.status = target
        if target == "submitted" and application.applied_at is None:
            application.applied_at = now
        if target == "submitted" and previous_status != "submitted":
            became_submitted = True

    for field_name in (
        "confirmation_number",
        "applied_at",
        "interview_date",
        "interview_stage",
        "offer_details",
        "rejection_reason",
        "outcome_date",
    ):
        if field_name in fields:
            setattr(application, field_name, fields[field_name])

    application.updated_at = now

    try:
        database.commit()
        database.refresh(application)
    except IntegrityError as exc:
        database.rollback()
        raise ApplicationServiceError(
            "Application could not be updated.",
            status_code=409,
        ) from exc

    if became_submitted:
        _notify_application_submitted(application, database)

    return application


def _notify_application_submitted(
    application: Application,
    database: Session,
) -> None:
    """Emit a 'you applied to …' notification. Best-effort — a
    notification failure must never break the status update."""
    from app.services.notification import create_notification

    job = database.get(NormalizedJob, application.job_id)
    title = job.title if job else "a job"
    employer = job.employer_name if job else "the employer"
    confirmation = (
        f" Confirmation: {application.confirmation_number}."
        if application.confirmation_number
        else ""
    )
    try:
        create_notification(
            database,
            category="application_submitted",
            subject=f"You applied to {title} at {employer}",
            body=(
                f"Your application to '{title}' at {employer} has been "
                f"recorded as submitted.{confirmation}"
            ),
            related_job_id=application.job_id,
            dedupe_key=f"application_submitted:{application.id}",
        )
    except Exception:  # noqa: BLE001 - notification is best-effort
        database.rollback()


def add_note(
    application_id: int,
    data: ApplicationNoteCreate,
    database: Session,
) -> Application:
    application = get_application_or_404(application_id, database)
    now = current_utc_time()

    notes = list(application.notes)
    notes.append({"text": data.text, "created_at": now.isoformat()})
    application.notes = notes
    application.updated_at = now

    database.commit()
    database.refresh(application)
    return application


def add_follow_up(
    application_id: int,
    data: ApplicationFollowUpCreate,
    database: Session,
) -> Application:
    application = get_application_or_404(application_id, database)
    now = current_utc_time()

    follow_ups = list(application.follow_ups)
    follow_ups.append(
        {
            "description": data.description,
            "due_date": (
                data.due_date.isoformat() if data.due_date else None
            ),
            "created_at": now.isoformat(),
            "done": False,
        }
    )
    application.follow_ups = follow_ups
    application.updated_at = now

    database.commit()
    database.refresh(application)
    return application


# --- Response composition -------------------------------------------------


def as_aware(value: datetime) -> datetime:
    """Normalize to a UTC-aware datetime.

    SQLite returns naive datetimes even for timezone-aware columns, so
    timeline entries mix naive and aware values. Assume UTC for naive
    values to keep comparisons and sorting well-defined.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def parse_timestamp(value: object) -> datetime | None:
    if isinstance(value, str):
        try:
            return as_aware(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


def build_timeline(
    application: Application,
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = [
        {
            "at": as_aware(application.created_at),
            "label": "Application tracked",
        },
    ]

    if application.applied_at is not None:
        entries.append(
            {"at": as_aware(application.applied_at), "label": "Applied"}
        )
    if application.interview_date is not None:
        stage = application.interview_stage or "interview"
        entries.append(
            {
                "at": as_aware(application.interview_date),
                "label": f"Interview: {stage}",
            }
        )
    if application.outcome_date is not None:
        outcome_at = datetime.combine(
            application.outcome_date,
            time.min,
            tzinfo=timezone.utc,
        )
        entries.append(
            {"at": outcome_at, "label": f"Outcome: {application.status}"}
        )

    for note in application.notes:
        at = parse_timestamp(note.get("created_at"))
        if at is not None:
            entries.append({"at": at, "label": "Note added"})

    for follow_up in application.follow_ups:
        at = parse_timestamp(follow_up.get("created_at"))
        if at is not None:
            entries.append(
                {"at": at, "label": "Follow-up scheduled"}
            )

    entries.sort(key=lambda entry: entry["at"])
    return entries


def build_detail(
    application: Application,
    database: Session,
) -> dict[str, object]:
    job = get_job_or_404(application.job_id, database)
    return {
        "id": application.id,
        "job_id": application.job_id,
        "cv_id": application.cv_id,
        "status": application.status,
        "applied_at": application.applied_at,
        "confirmation_number": application.confirmation_number,
        "interview_date": application.interview_date,
        "interview_stage": application.interview_stage,
        "offer_details": application.offer_details,
        "rejection_reason": application.rejection_reason,
        "outcome_date": application.outcome_date,
        "notes": application.notes,
        "follow_ups": application.follow_ups,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
        "job": {
            "id": job.id,
            "title": job.title,
            "employer_name": job.employer_name,
            "source_url": job.source_url,
        },
        "timeline": build_timeline(application),
    }
