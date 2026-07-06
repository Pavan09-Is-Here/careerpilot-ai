"""Background automation workers (Phase 12).

Workers run as bounded, on-demand cycles — one pass per invocation of
`run_worker` — rather than always-on daemons. This keeps behaviour
deterministic and testable and avoids a new scheduling dependency; an
external scheduler (cron) is expected to call the start endpoint on the
desired cadence.

Safety:
- No worker ever submits an application. There is deliberately no
  submission worker; submission always requires a human step.
- Daily limits cap how often each worker runs.
- Every action is written to the audit log.
- Failures are retried with exponential backoff and, if still failing,
  recorded rather than raised — one bad item never aborts the cycle.
- The discovery worker respects the source compliance gate and does not
  perform live network fetches in this environment.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.application_package import ApplicationPackage
from app.models.candidate_profile import CandidateProfile
from app.models.job import JobSource, NormalizedJob
from app.models.job_match import JobMatch
from app.models.job_tailored_cv import JobTailoredCV
from app.models.worker import AuditLogEntry, WorkerRun
from app.services.application_package import (
    ApplicationPackageServiceError,
    load_tailored_cv,
    prepare_application_package,
)
from app.services.job_match import (
    JobMatchServiceError,
    analyze_job_match,
    normalize_token,
)
from app.services.notification import create_notification


CANDIDATE_PROFILE_ID = 1

WORKER_ORDER = (
    "job_discovery",
    "job_analysis",
    "application_preparation",
    "expiry_checker",
    "auto_apply_pipeline",
)

DAILY_LIMITS: dict[str, dict[str, int]] = {
    "job_discovery": {"max_runs": 4, "max_items": 50},
    "job_analysis": {"max_runs": 24, "max_items": 100},
    "application_preparation": {"max_runs": 24, "max_items": 100},
    "expiry_checker": {"max_runs": 48, "max_items": 500},
    "auto_apply_pipeline": {"max_runs": 12, "max_items": 25},
}

# Default recency window for the auto-apply pipeline (hours).
AUTO_APPLY_RECENCY_HOURS = 168

MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.0
BACKOFF_FACTOR = 2.0
BACKOFF_CAP_SECONDS = 60.0


class WorkerServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def compute_backoff_seconds(attempt: int) -> float:
    """Exponential backoff for retry attempt N (1-indexed), capped."""
    if attempt < 1:
        attempt = 1
    delay = BACKOFF_BASE_SECONDS * (BACKOFF_FACTOR ** (attempt - 1))
    return min(delay, BACKOFF_CAP_SECONDS)


@dataclass
class WorkerContext:
    database: Session
    now: datetime
    sleep: Callable[[float], None]
    run_id: int
    worker_name: str
    limit: int
    # Counters are plain ints (not ORM attributes) so a mid-cycle
    # session rollback after a failed item cannot expire and reset them.
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    retries: int = 0
    audit_entries: list[AuditLogEntry] = field(default_factory=list)

    def audit(
        self,
        action: str,
        message: str,
        *,
        level: str = "info",
        entity_type: str | None = None,
        entity_id: int | None = None,
    ) -> None:
        self.audit_entries.append(
            AuditLogEntry(
                worker_run_id=self.run_id,
                worker_name=self.worker_name,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                level=level,
                message=message[:2000],
                created_at=self.now,
            )
        )


def process_items(
    ctx: WorkerContext,
    items: list,
    handler: Callable[[object], str],
    *,
    action: str,
    entity_type: str,
    entity_id_of: Callable[[object], int],
) -> None:
    """Run handler over items with bounded retries and full auditing.

    A per-item failure is retried with exponential backoff up to
    MAX_ATTEMPTS and, if still failing, recorded — never raised — so one
    bad item cannot abort the cycle.
    """
    for item in items[: ctx.limit]:
        ctx.processed += 1
        entity_id = entity_id_of(item)
        attempt = 0
        while True:
            attempt += 1
            try:
                message = handler(item)
                ctx.succeeded += 1
                ctx.audit(
                    action,
                    message,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
                break
            except Exception as exc:  # noqa: BLE001 - recorded, not raised
                # Discard any partial, uncommitted work from the failed
                # handler so the session stays usable for retries and
                # subsequent items. Already-committed items are kept.
                ctx.database.rollback()
                if attempt < MAX_ATTEMPTS:
                    ctx.retries += 1
                    delay = compute_backoff_seconds(attempt)
                    ctx.audit(
                        f"{action}_retry",
                        (
                            f"Attempt {attempt} failed; retrying after "
                            f"{delay:g}s."
                        ),
                        level="warning",
                        entity_type=entity_type,
                        entity_id=entity_id,
                    )
                    ctx.sleep(delay)
                    continue
                ctx.failed += 1
                ctx.audit(
                    f"{action}_failed",
                    (
                        f"Failed after {MAX_ATTEMPTS} attempts: "
                        f"{_safe_error(exc)}"
                    ),
                    level="error",
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
                break


def _safe_error(exc: Exception) -> str:
    message = getattr(exc, "safe_message", None)
    if isinstance(message, str) and message:
        return message
    return exc.__class__.__name__


# --- Workers --------------------------------------------------------------


def worker_job_discovery(ctx: WorkerContext) -> None:
    """Enumerate compliant, fetch-eligible sources.

    Live network fetching is intentionally deferred in this
    environment; the worker records readiness so an operator (or a
    future live fetcher) can act, and never bypasses the compliance
    gate.
    """
    sources = list(
        ctx.database.scalars(
            select(JobSource)
            .where(
                JobSource.enabled.is_(True),
                JobSource.allowlisted.is_(True),
                JobSource.server_fetch_allowed.is_(True),
            )
            .order_by(JobSource.id.asc())
        ).all()
    )
    if not sources:
        ctx.audit(
            "discovery_scan",
            "No enabled, allowlisted, fetch-eligible sources found.",
        )
        return

    for source in sources[: ctx.limit]:
        ctx.processed += 1
        ctx.succeeded += 1
        ctx.audit(
            "discovery_ready",
            (
                f"Source '{source.display_name}' is compliant and "
                "fetch-eligible; live fetch is deferred in this "
                "environment."
            ),
            entity_type="job_source",
            entity_id=source.id,
        )


def worker_job_analysis(ctx: WorkerContext) -> None:
    profile = ctx.database.get(CandidateProfile, CANDIDATE_PROFILE_ID)
    if profile is None:
        ctx.audit(
            "analysis_skipped",
            "No candidate profile exists; analysis skipped.",
            level="warning",
        )
        return

    analyzed_ids = select(JobMatch.job_id).where(
        JobMatch.candidate_profile_id == CANDIDATE_PROFILE_ID
    )
    jobs = list(
        ctx.database.scalars(
            select(NormalizedJob)
            .where(
                NormalizedJob.lifecycle_status.in_(
                    ("discovered", "active")
                ),
                NormalizedJob.id.notin_(analyzed_ids),
            )
            .order_by(NormalizedJob.id.asc())
        ).all()
    )

    def handle(job: object) -> str:
        assert isinstance(job, NormalizedJob)
        match = analyze_job_match(
            job.id,
            ctx.database,
            candidate_profile_id=CANDIDATE_PROFILE_ID,
            today=ctx.now.date(),
        )
        return (
            f"Analyzed '{job.title}' — eligibility "
            f"{match.eligibility_status}, score {match.match_score}."
        )

    process_items(
        ctx,
        jobs,
        handle,
        action="analyze_job",
        entity_type="job",
        entity_id_of=lambda job: job.id,
    )


def worker_application_preparation(ctx: WorkerContext) -> None:
    profile = ctx.database.get(CandidateProfile, CANDIDATE_PROFILE_ID)
    if profile is None:
        ctx.audit(
            "preparation_skipped",
            "No candidate profile exists; preparation skipped.",
            level="warning",
        )
        return

    prepared_ids = select(ApplicationPackage.job_id)
    eligible_ids = select(JobMatch.job_id).where(
        JobMatch.eligibility_status.in_(
            ("eligible", "conditionally_eligible")
        ),
        JobMatch.candidate_profile_id == CANDIDATE_PROFILE_ID,
    )
    tailored_ids = select(JobTailoredCV.job_id)

    jobs = list(
        ctx.database.scalars(
            select(NormalizedJob)
            .where(
                NormalizedJob.id.in_(eligible_ids),
                NormalizedJob.id.in_(tailored_ids),
                NormalizedJob.id.notin_(prepared_ids),
            )
            .order_by(NormalizedJob.id.asc())
        ).all()
    )

    def handle(job: object) -> str:
        assert isinstance(job, NormalizedJob)
        package = prepare_application_package(
            job.id, ctx.database, profile.id
        )
        return (
            f"Prepared application package for '{job.title}' — "
            f"readiness {package.readiness_status}. Submission is "
            "never automated."
        )

    process_items(
        ctx,
        jobs,
        handle,
        action="prepare_application",
        entity_type="job",
        entity_id_of=lambda job: job.id,
    )


def worker_expiry_checker(ctx: WorkerContext) -> None:
    jobs = list(
        ctx.database.scalars(
            select(NormalizedJob)
            .where(
                NormalizedJob.expires_at.is_not(None),
                NormalizedJob.expires_at < ctx.now,
                NormalizedJob.lifecycle_status.in_(
                    ("discovered", "active", "possibly_stale")
                ),
            )
            .order_by(NormalizedJob.id.asc())
        ).all()
    )

    def handle(job: object) -> str:
        assert isinstance(job, NormalizedJob)
        job.lifecycle_status = "expired"
        job.updated_at = ctx.now
        ctx.database.commit()
        return f"Marked '{job.title}' as expired (past its deadline)."

    process_items(
        ctx,
        jobs,
        handle,
        action="expire_job",
        entity_type="job",
        entity_id_of=lambda job: job.id,
    )


def _target_role_tokens(profile: CandidateProfile) -> list[str]:
    tokens: list[str] = []
    for role in profile.target_roles or []:
        cleaned = normalize_token(role)
        if cleaned:
            tokens.append(cleaned)
    return tokens


def _job_matches_target(
    job: NormalizedJob,
    role_tokens: list[str],
) -> bool:
    haystack = normalize_token(
        f"{job.title} {job.normalized_title or ''}"
    )
    return any(token in haystack for token in role_tokens)


def worker_auto_apply_pipeline(ctx: WorkerContext) -> None:
    """Prepare applications for the latest jobs in the candidate's
    target field — never submitting.

    For each recent, target-matching, eligible job: ensure a match,
    ensure a tailored CV, prepare the application package, and emit a
    notification. Submission always remains a human step: this worker
    stops at a ready-to-review package and notifies the candidate.
    """
    from app.schemas.cv_version import CVMasterGenerationRequest
    from app.services.cv_tailoring import (
        CVTailoringError,
        generate_tailored_cv,
    )

    profile = ctx.database.get(CandidateProfile, CANDIDATE_PROFILE_ID)
    if profile is None:
        ctx.audit(
            "auto_apply_skipped",
            "No candidate profile exists; auto-apply skipped.",
            level="warning",
        )
        return

    role_tokens = _target_role_tokens(profile)
    if not role_tokens:
        ctx.audit(
            "auto_apply_skipped",
            "No target roles are set on the profile; set a target "
            "field to enable auto-apply.",
            level="warning",
        )
        return

    cutoff = ctx.now - timedelta(hours=AUTO_APPLY_RECENCY_HOURS)
    candidates = list(
        ctx.database.scalars(
            select(NormalizedJob)
            .where(
                NormalizedJob.lifecycle_status.in_(
                    ("discovered", "active")
                ),
                NormalizedJob.last_seen_at >= cutoff,
            )
            .order_by(NormalizedJob.last_seen_at.desc())
        ).all()
    )
    jobs = [
        job for job in candidates if _job_matches_target(job, role_tokens)
    ][: ctx.limit]

    for job in jobs:
        ctx.processed += 1
        try:
            match = analyze_job_match(
                job.id,
                ctx.database,
                candidate_profile_id=CANDIDATE_PROFILE_ID,
                today=ctx.now.date(),
            )
            if match.eligibility_status == "ineligible":
                ctx.audit(
                    "auto_apply_skip_ineligible",
                    f"'{job.title}' is not eligible; skipped.",
                    entity_type="job",
                    entity_id=job.id,
                )
                ctx.succeeded += 1
                continue

            if load_tailored_cv(job.id, ctx.database) is None:
                try:
                    generate_tailored_cv(
                        job.id,
                        CVMasterGenerationRequest(
                            idempotency_key=f"auto-apply-job{job.id}",
                        ),
                        ctx.database,
                        candidate_profile_id=CANDIDATE_PROFILE_ID,
                    )
                except CVTailoringError as exc:
                    create_notification(
                        ctx.database,
                        candidate_profile_id=profile.id,
                        category="manual_action_required",
                        subject=f"Action needed to apply: {job.title}",
                        body=(
                            f"CareerPilot could not tailor a CV for "
                            f"'{job.title}' at {job.employer_name}: "
                            f"{exc.safe_message} Please resolve this and "
                            "re-run, or prepare the application manually."
                        ),
                        related_job_id=job.id,
                        dedupe_key=f"manual_action_required:{job.id}",
                    )
                    ctx.audit(
                        "auto_apply_manual",
                        f"Tailoring blocked for '{job.title}': "
                        f"{exc.safe_message}",
                        level="warning",
                        entity_type="job",
                        entity_id=job.id,
                    )
                    ctx.succeeded += 1
                    continue

            package = prepare_application_package(
                job.id, ctx.database, profile.id
            )

            if package.readiness_status == (
                "ready_for_automatic_application"
            ):
                create_notification(
                    ctx.database,
                    candidate_profile_id=profile.id,
                    category="application_prepared",
                    subject=(
                        f"Ready to submit: {job.title} at "
                        f"{job.employer_name}"
                    ),
                    body=(
                        f"A tailored application for '{job.title}' at "
                        f"{job.employer_name} is prepared and ready for "
                        "your review. Submission is not automated — open "
                        "CareerPilot to review and submit it."
                    ),
                    related_job_id=job.id,
                    dedupe_key=f"application_prepared:{job.id}",
                )
                ctx.audit(
                    "auto_apply_prepared",
                    f"Prepared application for '{job.title}'.",
                    entity_type="job",
                    entity_id=job.id,
                )
            else:
                create_notification(
                    ctx.database,
                    candidate_profile_id=profile.id,
                    category="manual_action_required",
                    subject=f"Review needed: {job.title}",
                    body=(
                        f"The application for '{job.title}' at "
                        f"{job.employer_name} needs your attention "
                        f"(status: {package.readiness_status}). Open "
                        "CareerPilot to review it."
                    ),
                    related_job_id=job.id,
                    dedupe_key=(
                        f"manual_action_required:{job.id}:"
                        f"{package.readiness_status}"
                    ),
                )
                ctx.audit(
                    "auto_apply_review",
                    f"'{job.title}' prepared but needs review "
                    f"({package.readiness_status}).",
                    level="warning",
                    entity_type="job",
                    entity_id=job.id,
                )
            ctx.succeeded += 1
        except (
            JobMatchServiceError,
            ApplicationPackageServiceError,
        ) as exc:
            ctx.database.rollback()
            ctx.failed += 1
            ctx.audit(
                "auto_apply_failed",
                f"Auto-apply failed for '{job.title}': "
                f"{exc.safe_message}",
                level="error",
                entity_type="job",
                entity_id=job.id,
            )


WORKER_REGISTRY: dict[str, Callable[[WorkerContext], None]] = {
    "job_discovery": worker_job_discovery,
    "job_analysis": worker_job_analysis,
    "application_preparation": worker_application_preparation,
    "expiry_checker": worker_expiry_checker,
    "auto_apply_pipeline": worker_auto_apply_pipeline,
}


# --- Orchestration --------------------------------------------------------


def runs_today(
    worker_name: str,
    run_date: date,
    database: Session,
) -> int:
    return int(
        database.scalar(
            select(func.count())
            .select_from(WorkerRun)
            .where(
                WorkerRun.worker_name == worker_name,
                WorkerRun.run_date == run_date,
                WorkerRun.status != "skipped",
            )
        )
        or 0
    )


def finalize_status(ctx: "WorkerContext") -> str:
    if ctx.failed > 0 and ctx.succeeded == 0:
        return "failed"
    if ctx.failed > 0:
        return "partial"
    return "success"


def run_worker(
    worker_name: str,
    database: Session,
    *,
    now: datetime | None = None,
    sleep: Callable[[float], None] | None = None,
) -> WorkerRun:
    if worker_name not in WORKER_REGISTRY:
        raise WorkerServiceError(
            "Unknown worker.",
            status_code=404,
        )

    now = now or current_utc_time()
    sleep = sleep or (lambda _seconds: None)
    limits = DAILY_LIMITS[worker_name]
    today = now.date()

    run = WorkerRun(
        worker_name=worker_name,
        status="running",
        run_date=today,
        items_processed=0,
        items_succeeded=0,
        items_failed=0,
        retries=0,
        started_at=now,
        created_at=now,
    )

    if runs_today(worker_name, today, database) >= limits["max_runs"]:
        run.status = "skipped"
        run.finished_at = now
        database.add(run)
        database.commit()
        database.refresh(run)
        entry = AuditLogEntry(
            worker_run_id=run.id,
            worker_name=worker_name,
            action="daily_limit_reached",
            level="warning",
            message=(
                "Daily run limit reached; worker cycle skipped."
            ),
            created_at=now,
        )
        database.add(entry)
        database.commit()
        return run

    database.add(run)
    database.commit()
    database.refresh(run)

    ctx = WorkerContext(
        database=database,
        now=now,
        sleep=sleep,
        run_id=run.id,
        worker_name=worker_name,
        limit=limits["max_items"],
    )

    final_status = "failed"
    run_error: str | None = None
    try:
        WORKER_REGISTRY[worker_name](ctx)
        final_status = finalize_status(ctx)
    except Exception as exc:  # noqa: BLE001 - defensive top-level guard
        database.rollback()
        run_error = _safe_error(exc)[:1000]
        ctx.audit_entries.append(
            AuditLogEntry(
                worker_run_id=ctx.run_id,
                worker_name=worker_name,
                action="worker_error",
                level="error",
                message=f"Worker failed: {_safe_error(exc)}",
                created_at=now,
            )
        )

    # Re-fetch the run (it may have been expired by an item-level or the
    # defensive rollback) and write the final counters and status once.
    run = database.get(WorkerRun, ctx.run_id)
    if run is not None:
        run.status = final_status
        run.error = run_error
        run.items_processed = ctx.processed
        run.items_succeeded = ctx.succeeded
        run.items_failed = ctx.failed
        run.retries = ctx.retries
        run.finished_at = current_utc_time()

    for entry in ctx.audit_entries:
        database.add(entry)
    database.commit()
    if run is not None:
        database.refresh(run)
    return run


def run_all_workers(
    database: Session,
    *,
    now: datetime | None = None,
    sleep: Callable[[float], None] | None = None,
) -> list[WorkerRun]:
    now = now or current_utc_time()
    return [
        run_worker(name, database, now=now, sleep=sleep)
        for name in WORKER_ORDER
    ]


def worker_health(
    worker_name: str,
    database: Session,
    *,
    now: datetime | None = None,
) -> dict[str, object]:
    now = now or current_utc_time()
    last = database.scalar(
        select(WorkerRun)
        .where(WorkerRun.worker_name == worker_name)
        .order_by(WorkerRun.id.desc())
    )
    today_count = runs_today(worker_name, now.date(), database)
    max_runs = DAILY_LIMITS[worker_name]["max_runs"]

    if last is None:
        health = "never_run"
    elif last.status == "failed":
        health = "failed"
    elif last.status == "partial":
        health = "degraded"
    else:
        health = "healthy"

    return {
        "worker_name": worker_name,
        "health": health,
        "last_status": last.status if last else None,
        "last_run_at": last.started_at if last else None,
        "runs_today": today_count,
        "max_runs_per_day": max_runs,
        "daily_limit_reached": today_count >= max_runs,
    }


def all_worker_health(
    database: Session,
    *,
    now: datetime | None = None,
) -> list[dict[str, object]]:
    now = now or current_utc_time()
    return [
        worker_health(name, database, now=now) for name in WORKER_ORDER
    ]


def list_audit_log(
    database: Session,
    *,
    worker: str | None = None,
    level: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, object]:
    filters = []
    if worker is not None:
        filters.append(AuditLogEntry.worker_name == worker)
    if level is not None:
        filters.append(AuditLogEntry.level == level)

    total = int(
        database.scalar(
            select(func.count())
            .select_from(AuditLogEntry)
            .where(*filters)
        )
        or 0
    )
    items = list(
        database.scalars(
            select(AuditLogEntry)
            .where(*filters)
            .order_by(AuditLogEntry.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
