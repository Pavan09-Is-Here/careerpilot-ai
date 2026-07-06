"""Tests for notifications, the submitted trigger, and the safe
auto-apply pipeline (which never submits)."""

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.application_answer import ApplicationAnswer
from app.models.candidate_profile import CandidateProfile
from app.models.cv_version import CVVersion
from app.models.cv_version_artifact import CVVersionArtifact
from app.models.job import NormalizedJob
from app.models.job_match import JobMatch
from app.models.job_tailored_cv import JobTailoredCV
from app.models.notification import Notification
from app.schemas.job import (
    JobCompensationCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)
from app.services.application import track_application, update_application
from app.schemas.application import ApplicationUpdate
from app.services.job import create_job_source, create_normalized_job
from app.services.notification import (
    create_notification,
    deliver_pending,
    list_notifications,
)
from app.services.worker import run_worker

from tests.conftest import Account


NOW = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter() -> None:
    # Registration reuses the login rate limiter; reset it so repeated
    # account registration across tests does not trip the 429 guard.
    from app.api.routes.auth import login_rate_limiter

    login_rate_limiter.reset()


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_profile(database: Session, **overrides: object) -> CandidateProfile:
    values: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "work_authorization": "UK citizen",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": [],
        "target_roles": ["Platform Engineer"],
        "preferred_locations": [],
        "salary_currency": "GBP",
        "minimum_match_score": 50,
        "auto_apply_enabled": False,
        "facts_verified": True,
    }
    values.update(overrides)
    profile = CandidateProfile(**values)
    database.add(profile)
    database.commit()
    return profile


def make_job(
    database: Session,
    *,
    title: str = "Platform Engineer",
    last_seen_at: datetime = NOW,
    with_salary: bool = False,
) -> NormalizedJob:
    source = create_job_source(
        JobSourceCreate(
            source_key=f"source-{uuid4().hex[:12]}",
            display_name="Example Robotics",
            source_category="provider_api",
        ),
        database,
    )
    compensations = []
    if with_salary:
        compensations = [
            JobCompensationCreate(
                min_amount=Decimal("70000"),
                max_amount=Decimal("90000"),
                currency="GBP",
                compensation_period="yearly",
                source_text="70000-90000 GBP",
            )
        ]
    job = create_normalized_job(
        NormalizedJobCreate(
            job_source_id=source.id,
            source_job_id=f"job-{uuid4().hex[:16]}",
            source_url=f"https://jobs.example.com/{uuid4().hex}",
            employer_name="Example Robotics",
            title=title,
            normalized_title=title.casefold(),
            content_hash=content_hash(),
            normalization_version="notif-test",
        ),
        database,
        compensations=compensations,
    )
    job.last_seen_at = last_seen_at
    database.add(job)
    database.commit()
    database.refresh(job)
    return job


def add_match(database, job, profile, *, eligibility="eligible") -> None:
    database.add(
        JobMatch(
            job_id=job.id,
            candidate_profile_id=profile.id,
            match_score=80,
            eligibility_status=eligibility,
            blocker_reason=None,
            explanation="t",
            algorithm_version="match-algorithm-1",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    database.commit()


def add_tailored_cv(database, job, profile) -> None:
    version = CVVersion(
        candidate_profile_id=profile.id,
        source_document_id=None,
        parent_version_id=None,
        version_type="tailored",
        status="ready",
        display_name="Tailored CV",
        description=None,
        job_reference="ref",
        is_primary=False,
        storage_path=None,
        mime_type=None,
        file_size=None,
        sha256=None,
        created_at=NOW,
        updated_at=NOW,
        archived_at=None,
    )
    database.add(version)
    database.commit()
    database.refresh(version)
    for artifact_type in ("docx", "pdf"):
        database.add(
            CVVersionArtifact(
                cv_version_id=version.id,
                artifact_type=artifact_type,
                mime_type="application/octet-stream",
                safe_filename=f"cv.{artifact_type}",
                storage_path=f"/tmp/{uuid4().hex}.{artifact_type}",
                file_size=1024,
                sha256=content_hash(),
                page_count=1 if artifact_type == "pdf" else None,
                renderer_version="test",
                content_version="test",
                created_at=NOW,
            )
        )
    database.add(
        JobTailoredCV(
            job_id=job.id,
            candidate_profile_id=version.candidate_profile_id,
            cv_version_id=version.id,
            created_at=NOW,
            updated_at=NOW,
        )
    )
    database.commit()


def add_all_answers(database, candidate_profile_id: int = 1) -> None:
    def add(cat, sensitive=False):
        database.add(
            ApplicationAnswer(
                candidate_profile_id=candidate_profile_id,
                category=cat,
                question_label=f"{cat}?",
                answer_text=f"Verified {cat}.",
                verified=True,
                manually_confirmed=sensitive,
                requires_manual_confirmation=sensitive,
                created_at=NOW,
                updated_at=NOW,
            )
        )
    add("work_authorization", sensitive=True)
    add("availability")
    add("sponsorship", sensitive=True)
    add("expected_salary")
    add("relocation")
    add("notice_period")
    database.commit()


# --- Notification service -------------------------------------------------


def test_create_and_dedupe_notification(db_session: Session) -> None:
    profile = make_profile(db_session)
    first = create_notification(
        db_session,
        candidate_profile_id=profile.id,
        category="application_submitted",
        subject="You applied",
        body="body",
        dedupe_key="k1",
    )
    assert first is not None
    assert first.recipient == "candidate@example.com"
    assert first.status == "pending"

    dup = create_notification(
        db_session,
        candidate_profile_id=profile.id,
        category="application_submitted",
        subject="You applied again",
        body="body",
        dedupe_key="k1",
    )
    assert dup.id == first.id  # deduped, not a new row
    assert (
        list_notifications(
            db_session, candidate_profile_id=profile.id
        )["total"]
        == 1
    )


def test_deliver_without_smtp_leaves_pending(db_session: Session) -> None:
    profile = make_profile(db_session)
    create_notification(
        db_session,
        candidate_profile_id=profile.id,
        category="application_prepared",
        subject="Ready",
        body="body",
    )
    result = deliver_pending(db_session, Settings())  # no SMTP host set
    assert result["skipped"] == 1
    assert result["sent"] == 0
    assert (
        list_notifications(
            db_session,
            candidate_profile_id=profile.id,
            status="pending",
        )["total"]
        == 1
    )


def test_no_recipient_records_nothing(db_session: Session) -> None:
    # Missing profile -> no recipient email -> nothing recorded.
    result = create_notification(
        db_session,
        candidate_profile_id=999999,
        category="application_prepared",
        subject="Ready",
        body="body",
    )
    assert result is None


# --- Submitted trigger ----------------------------------------------------


def test_marking_submitted_notifies(db_session: Session) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    app_id = track_application(
        job.id, db_session, candidate_profile_id=profile.id
    ).id

    update_application(
        app_id,
        ApplicationUpdate(status="ready_to_apply"),
        db_session,
        candidate_profile_id=profile.id,
    )
    update_application(
        app_id,
        ApplicationUpdate(status="submitted", confirmation_number="C-9"),
        db_session,
        candidate_profile_id=profile.id,
    )

    notes = list_notifications(
        db_session,
        candidate_profile_id=profile.id,
        category="application_submitted",
    )
    assert notes["total"] == 1
    body = notes["items"][0].body
    assert "C-9" in body
    assert "Platform Engineer" in notes["items"][0].subject


# --- Auto-apply pipeline (never submits) ----------------------------------


def test_auto_apply_prepares_and_notifies(db_session: Session) -> None:
    profile = make_profile(db_session, minimum_salary=None)
    job = make_job(db_session, title="Platform Engineer", with_salary=True)
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)  # skip real CV generation
    add_all_answers(db_session, candidate_profile_id=profile.id)

    run = run_worker("auto_apply_pipeline", db_session, now=NOW)
    assert run.status in {"success", "partial"}
    assert run.items_processed == 1

    prepared = list_notifications(
        db_session,
        candidate_profile_id=profile.id,
        category="application_prepared",
    )
    assert prepared["total"] == 1
    assert "Ready to submit" in prepared["items"][0].subject

    # The pipeline never submits: no submitted notification, no run.
    assert (
        list_notifications(
            db_session,
            candidate_profile_id=profile.id,
            category="application_submitted",
        )["total"]
        == 0
    )


def test_auto_apply_skips_non_target_jobs(db_session: Session) -> None:
    profile = make_profile(db_session, target_roles=["Data Scientist"])
    job = make_job(db_session, title="Platform Engineer")
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)
    add_all_answers(db_session, candidate_profile_id=profile.id)

    run = run_worker("auto_apply_pipeline", db_session, now=NOW)
    assert run.items_processed == 0
    assert (
        list_notifications(
            db_session, candidate_profile_id=profile.id
        )["total"]
        == 0
    )


def test_auto_apply_without_target_roles_warns(db_session: Session) -> None:
    make_profile(db_session, target_roles=[])
    run = run_worker("auto_apply_pipeline", db_session, now=NOW)
    assert run.items_processed == 0


# --- API ------------------------------------------------------------------


def test_notifications_api(
    client: TestClient, db_session: Session, account: Account
) -> None:
    # Registration already creates the caller's profile (with an email),
    # so seed the notification against the authenticated account's profile.
    create_notification(
        db_session,
        candidate_profile_id=account.profile_id,
        category="manual_action_required",
        subject="Action needed",
        body="body",
    )
    unauthenticated = client.get(
        "/api/notifications", params={"category": "manual_action_required"}
    )
    assert unauthenticated.status_code == 401

    listing = client.get(
        "/api/notifications",
        params={"category": "manual_action_required"},
        headers=account.headers,
    )
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    deliver = client.post(
        "/api/notifications/deliver", headers=account.headers
    )
    assert deliver.status_code == 200
    assert deliver.json()["skipped"] == 1
