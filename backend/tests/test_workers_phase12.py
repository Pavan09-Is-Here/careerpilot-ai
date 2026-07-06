"""Phase 12 — Background Automation worker tests."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.job import NormalizedJob
from app.models.job_match import JobMatch
from app.models.worker import AuditLogEntry, WorkerRun
from app.schemas.job import JobSourceCreate, NormalizedJobCreate
from app.services import worker as worker_service
from app.services.job import create_job_source, create_normalized_job
from app.services.worker import (
    DAILY_LIMITS,
    compute_backoff_seconds,
    list_audit_log,
    run_all_workers,
    run_worker,
    worker_health,
)


NOW = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_profile(database: Session) -> CandidateProfile:
    profile = CandidateProfile(
        full_name="Test Candidate",
        email="candidate@example.com",
        requires_sponsorship=False,
        willing_to_relocate=False,
        preferred_work_modes=[],
        target_roles=[],
        preferred_locations=[],
        salary_currency="GBP",
        minimum_match_score=50,
        auto_apply_enabled=False,
        facts_verified=True,
    )
    database.add(profile)
    database.commit()
    return profile


def make_job(database: Session, **overrides: object) -> NormalizedJob:
    source = create_job_source(
        JobSourceCreate(
            source_key=f"source-{uuid4().hex[:12]}",
            display_name="Example Robotics",
            source_category="provider_api",
        ),
        database,
    )
    payload: dict[str, object] = {
        "job_source_id": source.id,
        "source_job_id": f"job-{uuid4().hex[:16]}",
        "source_url": f"https://jobs.example.com/{uuid4().hex}",
        "employer_name": "Example Robotics",
        "title": "Platform Engineer",
        "content_hash": content_hash(),
        "normalization_version": "phase12-test",
    }
    payload.update(overrides)
    return create_normalized_job(
        NormalizedJobCreate(**payload),
        database,
    )


# --- Backoff --------------------------------------------------------------


def test_compute_backoff_is_exponential_and_capped() -> None:
    assert compute_backoff_seconds(1) == 1.0
    assert compute_backoff_seconds(2) == 2.0
    assert compute_backoff_seconds(3) == 4.0
    assert compute_backoff_seconds(10) == 60.0  # capped
    assert compute_backoff_seconds(0) == 1.0


# --- Expiry checker -------------------------------------------------------


def test_expiry_checker_marks_expired_and_audits(
    db_session: Session,
) -> None:
    past = NOW - timedelta(days=1)
    future = NOW + timedelta(days=5)
    expired_job = make_job(
        db_session,
        expires_at=past,
        lifecycle_status="active",
    )
    fresh_job = make_job(
        db_session,
        expires_at=future,
        lifecycle_status="active",
    )

    run = run_worker("expiry_checker", db_session, now=NOW)

    assert run.status == "success"
    assert run.items_processed == 1
    assert run.items_succeeded == 1

    db_session.expire_all()
    assert db_session.get(NormalizedJob, expired_job.id).lifecycle_status == (
        "expired"
    )
    assert db_session.get(NormalizedJob, fresh_job.id).lifecycle_status == (
        "active"
    )

    audit = list_audit_log(db_session, worker="expiry_checker")
    assert audit["total"] >= 1


# --- Analysis worker ------------------------------------------------------


def test_analysis_worker_creates_matches(db_session: Session) -> None:
    make_profile(db_session)
    job = make_job(db_session, lifecycle_status="active")

    run = run_worker("job_analysis", db_session, now=NOW)

    assert run.status == "success"
    assert run.items_processed == 1
    match = db_session.scalar(
        JobMatch.__table__.select().where(JobMatch.job_id == job.id)
    )
    assert match is not None


def test_analysis_worker_skips_without_profile(
    db_session: Session,
) -> None:
    make_job(db_session, lifecycle_status="active")
    run = run_worker("job_analysis", db_session, now=NOW)
    assert run.status == "success"
    assert run.items_processed == 0

    audit = list_audit_log(
        db_session, worker="job_analysis", level="warning"
    )
    assert audit["total"] >= 1


# --- Retry / graceful failure ---------------------------------------------


def test_worker_retries_transient_failures(
    db_session: Session,
    monkeypatch,
) -> None:
    make_profile(db_session)
    make_job(db_session, lifecycle_status="active")

    calls = {"n": 0}
    real = worker_service.analyze_job_match

    def flaky(job_id, database, *, candidate_profile_id, today=None):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("transient")
        return real(
            job_id,
            database,
            candidate_profile_id=candidate_profile_id,
            today=today,
        )

    monkeypatch.setattr(worker_service, "analyze_job_match", flaky)
    sleeps: list[float] = []

    run = run_worker(
        "job_analysis",
        db_session,
        now=NOW,
        sleep=sleeps.append,
    )

    assert run.items_succeeded == 1
    assert run.retries == 1
    assert sleeps == [1.0]  # one backoff of base seconds


def test_worker_records_failure_after_max_attempts(
    db_session: Session,
    monkeypatch,
) -> None:
    make_profile(db_session)
    make_job(db_session, lifecycle_status="active")

    def always_fail(job_id, database, *, today=None):
        raise RuntimeError("permanent")

    monkeypatch.setattr(
        worker_service, "analyze_job_match", always_fail
    )

    run = run_worker(
        "job_analysis",
        db_session,
        now=NOW,
        sleep=lambda _s: None,
    )

    assert run.status == "failed"
    assert run.items_failed == 1
    errors = list_audit_log(
        db_session, worker="job_analysis", level="error"
    )
    assert errors["total"] >= 1


# --- Daily limits ---------------------------------------------------------


def test_daily_limit_skips_further_runs(db_session: Session) -> None:
    make_profile(db_session)
    max_runs = DAILY_LIMITS["job_discovery"]["max_runs"]

    last = None
    for _ in range(max_runs):
        last = run_worker("job_discovery", db_session, now=NOW)
        assert last.status != "skipped"

    skipped = run_worker("job_discovery", db_session, now=NOW)
    assert skipped.status == "skipped"

    audit = list_audit_log(
        db_session, worker="job_discovery", level="warning"
    )
    assert any(
        entry.action == "daily_limit_reached" for entry in audit["items"]
    )


# --- run_all + never submits ----------------------------------------------


def test_run_all_workers_covers_registry(db_session: Session) -> None:
    make_profile(db_session)
    make_job(db_session, lifecycle_status="active")

    runs = run_all_workers(db_session, now=NOW)
    worker_names = {run.worker_name for run in runs}
    assert worker_names == set(worker_service.WORKER_ORDER)
    # No submission worker exists in the registry.
    assert "submit" not in " ".join(worker_service.WORKER_REGISTRY)


# --- API endpoints --------------------------------------------------------


def test_start_status_and_audit_endpoints(
    auth_client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    make_job(db_session, lifecycle_status="active")

    started = auth_client.post(
        "/api/workers/start",
        json={"worker": "job_analysis"},
    )
    assert started.status_code == 201
    runs = started.json()["runs"]
    assert len(runs) == 1
    assert runs[0]["worker_name"] == "job_analysis"

    status = auth_client.get("/api/workers/status")
    assert status.status_code == 200
    workers = {w["worker_name"]: w for w in status.json()["workers"]}
    assert workers["job_analysis"]["health"] in {"healthy", "degraded"}
    assert workers["expiry_checker"]["health"] == "never_run"

    audit = auth_client.get(
        "/api/audit-log",
        params={"worker": "job_analysis"},
    )
    assert audit.status_code == 200
    assert audit.json()["total"] >= 1


def test_start_unknown_worker_404(auth_client: TestClient) -> None:
    response = auth_client.post(
        "/api/workers/start",
        json={"worker": "not_a_worker"},
    )
    # Rejected by schema validation (422) before reaching the service.
    assert response.status_code == 422
