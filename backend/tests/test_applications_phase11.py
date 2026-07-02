"""Phase 11 — Application Tracking Dashboard tests."""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.cv_version import CVVersion
from app.models.job import NormalizedJob
from app.models.job_match import JobMatch
from app.models.job_tailored_cv import JobTailoredCV
from app.schemas.job import JobSourceCreate, NormalizedJobCreate
from app.services.application import (
    ApplicationServiceError,
    derive_initial_status,
    track_application,
    validate_transition,
)
from app.services.job import create_job_source, create_normalized_job


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_profile(database: Session, **overrides: object) -> CandidateProfile:
    values: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": [],
        "target_roles": [],
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
    database.refresh(profile)
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
        "normalization_version": "phase11-test",
    }
    payload.update(overrides)
    return create_normalized_job(
        NormalizedJobCreate(**payload),
        database,
    )


def add_match(
    database: Session,
    job: NormalizedJob,
    profile: CandidateProfile,
    *,
    eligibility_status: str = "eligible",
) -> None:
    now = datetime.now(timezone.utc)
    database.add(
        JobMatch(
            job_id=job.id,
            candidate_profile_id=profile.id,
            match_score=80,
            eligibility_status=eligibility_status,
            blocker_reason=None,
            explanation="t",
            algorithm_version="match-algorithm-1",
            created_at=now,
            updated_at=now,
        )
    )
    database.commit()


def add_tailored_cv(
    database: Session,
    job: NormalizedJob,
    profile: CandidateProfile,
) -> CVVersion:
    now = datetime.now(timezone.utc)
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
        created_at=now,
        updated_at=now,
        archived_at=None,
    )
    database.add(version)
    database.commit()
    database.refresh(version)
    database.add(
        JobTailoredCV(
            job_id=job.id,
            cv_version_id=version.id,
            created_at=now,
            updated_at=now,
        )
    )
    database.commit()
    return version


# --- Status derivation ----------------------------------------------------


def test_derive_status_discovered(db_session: Session) -> None:
    make_profile(db_session)
    job = make_job(db_session)
    assert derive_initial_status(job.id, db_session) == "discovered"


def test_derive_status_matched_and_not_eligible(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    assert derive_initial_status(job.id, db_session) == "matched"

    job2 = make_job(db_session)
    add_match(db_session, job2, profile, eligibility_status="ineligible")
    assert derive_initial_status(job2.id, db_session) == "not_eligible"


def test_derive_status_cv_generated(db_session: Session) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)
    assert derive_initial_status(job.id, db_session) == "cv_generated"


# --- Transitions ----------------------------------------------------------


def test_valid_and_invalid_transitions() -> None:
    validate_transition("submitted", "interview")
    validate_transition("matched", "matched")  # no-op
    validate_transition("applying", "withdrawn")  # withdraw allowed

    with pytest.raises(ApplicationServiceError):
        validate_transition("discovered", "offer")
    with pytest.raises(ApplicationServiceError):
        validate_transition("rejected", "interview")
    with pytest.raises(ApplicationServiceError):
        validate_transition("withdrawn", "applying")


# --- Track / list ---------------------------------------------------------


def test_track_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)

    first = client.post(f"/api/jobs/{job.id}/track")
    assert first.status_code == 201
    body = first.json()
    assert body["status"] == "matched"
    assert body["job_id"] == job.id

    second = client.post(f"/api/jobs/{job.id}/track")
    assert second.status_code == 201
    assert second.json()["id"] == body["id"]


def test_track_missing_job_404(client: TestClient) -> None:
    response = client.post("/api/jobs/999/track")
    assert response.status_code == 404


def test_list_and_filter_by_status(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    job1 = make_job(db_session)
    add_match(db_session, job1, profile)
    job2 = make_job(db_session)
    add_match(db_session, job2, profile, eligibility_status="ineligible")

    track_application(job1.id, db_session)
    track_application(job2.id, db_session)

    all_apps = client.get("/api/applications")
    assert all_apps.status_code == 200
    assert len(all_apps.json()) == 2

    filtered = client.get(
        "/api/applications", params={"status": "not_eligible"}
    )
    assert len(filtered.json()) == 1
    assert filtered.json()[0]["status"] == "not_eligible"


# --- Update / notes / follow-up / timeline --------------------------------


def test_update_status_transition_and_autofill_applied_at(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    app_id = track_application(job.id, db_session).id

    # matched -> ready_to_apply -> submitted
    client.put(
        f"/api/applications/{app_id}",
        json={"status": "ready_to_apply"},
    )
    submitted = client.put(
        f"/api/applications/{app_id}",
        json={"status": "submitted", "confirmation_number": "C-1"},
    )
    assert submitted.status_code == 200
    body = submitted.json()
    assert body["status"] == "submitted"
    assert body["applied_at"] is not None
    assert body["confirmation_number"] == "C-1"


def test_update_invalid_transition_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    app_id = track_application(job.id, db_session).id

    response = client.put(
        f"/api/applications/{app_id}",
        json={"status": "offer"},
    )
    assert response.status_code == 400


def test_notes_follow_up_and_timeline(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    app_id = track_application(job.id, db_session).id

    note = client.post(
        f"/api/applications/{app_id}/notes",
        json={"text": "Recruiter reached out."},
    )
    assert note.status_code == 201
    assert len(note.json()["notes"]) == 1

    follow = client.post(
        f"/api/applications/{app_id}/follow-up",
        json={"description": "Send thank-you", "due_date": "2026-07-10"},
    )
    assert follow.status_code == 201
    assert follow.json()["follow_ups"][0]["description"] == (
        "Send thank-you"
    )

    detail = client.get(f"/api/applications/{app_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert detail_body["job"]["employer_name"] == "Example Robotics"
    labels = [entry["label"] for entry in detail_body["timeline"]]
    assert "Application tracked" in labels
    assert "Note added" in labels
    assert "Follow-up scheduled" in labels


def test_empty_note_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    app_id = track_application(job.id, db_session).id

    response = client.post(
        f"/api/applications/{app_id}/notes",
        json={"text": "   "},
    )
    assert response.status_code == 422


def test_get_missing_application_404(client: TestClient) -> None:
    response = client.get("/api/applications/999")
    assert response.status_code == 404
