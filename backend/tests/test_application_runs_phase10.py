"""Phase 10 — Browser-assisted application workflow tests.

These verify the safety-first, human-in-the-loop workflow: fields are
mapped from verified data only, mandatory safety gates pause the run,
the tool never submits on its own, and submission is recorded only
when the candidate supplies the confirmation number.
"""

from datetime import datetime, timezone
from decimal import Decimal
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.application_answer import ApplicationAnswer
from app.models.candidate_profile import CandidateProfile
from app.models.cv_version import CVVersion
from app.models.cv_version_artifact import CVVersionArtifact
from app.models.job import NormalizedJob
from app.models.job_match import JobMatch
from app.models.job_tailored_cv import JobTailoredCV
from app.schemas.job import (
    JobCompensationCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)
from app.services.application_package import prepare_application_package
from app.services.application_run import (
    ApplicationRunServiceError,
    build_gates,
    start_application_run,
)
from app.services.job import create_job_source, create_normalized_job


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_profile(database: Session, **overrides: object) -> CandidateProfile:
    values: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "phone": "+44 20 7946 0000",
        "professional_title": "Platform Engineer",
        "professional_summary": "Verified engineer summary.",
        "work_authorization": "UK citizen",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": ["remote"],
        "target_roles": ["Platform Engineer"],
        "preferred_locations": ["London"],
        "minimum_salary": None,
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
        "normalized_title": "platform engineer",
        "content_hash": content_hash(),
        "normalization_version": "phase10-test",
    }
    payload.update(overrides)
    return create_normalized_job(
        NormalizedJobCreate(**payload),
        database,
        compensations=[
            JobCompensationCreate(
                min_amount=Decimal("70000"),
                max_amount=Decimal("90000"),
                currency="GBP",
                compensation_period="yearly",
                source_text="70000-90000 GBP",
            )
        ],
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
            explanation="test",
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
) -> None:
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
                created_at=now,
            )
        )
    database.add(
        JobTailoredCV(
            job_id=job.id,
            cv_version_id=version.id,
            created_at=now,
            updated_at=now,
        )
    )
    database.commit()


def add_answer(
    database: Session,
    category: str,
    *,
    verified: bool = True,
    requires_manual_confirmation: bool = False,
    manually_confirmed: bool = False,
) -> None:
    now = datetime.now(timezone.utc)
    database.add(
        ApplicationAnswer(
            candidate_profile_id=1,
            category=category,
            question_label=f"{category} question",
            answer_text=f"Verified {category} answer.",
            verified=verified,
            manually_confirmed=manually_confirmed,
            requires_manual_confirmation=requires_manual_confirmation,
            created_at=now,
            updated_at=now,
        )
    )
    database.commit()


def add_all_answers(database: Session) -> None:
    add_answer(
        database,
        "work_authorization",
        requires_manual_confirmation=True,
        manually_confirmed=True,
    )
    add_answer(database, "availability")
    add_answer(
        database,
        "sponsorship",
        requires_manual_confirmation=True,
        manually_confirmed=True,
    )
    add_answer(database, "expected_salary")
    add_answer(database, "relocation")
    add_answer(database, "notice_period")


def build_ready_confirmed_package(
    client: TestClient,
    db_session: Session,
    **job_overrides: object,
) -> NormalizedJob:
    profile = make_profile(db_session)
    job = make_job(db_session, **job_overrides)
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)
    add_all_answers(db_session)
    prepare_application_package(job.id, db_session)
    # Confirm the package (deliberate human action before applying).
    client.put(
        f"/api/jobs/{job.id}/application-package",
        json={"user_confirmed": True},
    )
    return job


# --- Preconditions --------------------------------------------------------


def test_apply_requires_package(db_session: Session) -> None:
    make_profile(db_session)
    job = make_job(db_session)
    with pytest.raises(ApplicationRunServiceError) as exc:
        start_application_run(job.id, db_session)
    assert exc.value.status_code == 409


def test_apply_requires_confirmation(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)
    add_all_answers(db_session)
    prepare_application_package(job.id, db_session)  # not confirmed

    with pytest.raises(ApplicationRunServiceError) as exc:
        start_application_run(job.id, db_session)
    assert exc.value.status_code == 409
    assert "confirm" in exc.value.safe_message.lower()


def test_apply_rejected_when_not_eligible(db_session: Session) -> None:
    profile = make_profile(db_session)
    job = make_job(db_session)
    add_match(db_session, job, profile, eligibility_status="ineligible")
    prepare_application_package(job.id, db_session)

    with pytest.raises(ApplicationRunServiceError) as exc:
        start_application_run(job.id, db_session)
    assert exc.value.status_code == 409


# --- Field mapping & gates ------------------------------------------------


def test_apply_builds_fill_plan_and_gates(
    client: TestClient,
    db_session: Session,
) -> None:
    job = build_ready_confirmed_package(client, db_session)

    response = client.post(f"/api/jobs/{job.id}/apply")
    assert response.status_code == 201
    body = response.json()

    assert body["status"] == "paused_for_gate"
    assert body["driver"] == "manual_assist"
    assert body["confirmation_number"] is None

    # Verified identity and non-sensitive answers are auto-filled.
    fill_fields = {f["field"] for f in body["fill_plan"]}
    assert {"full_name", "email", "availability"}.issubset(fill_fields)
    assert "resume" in fill_fields

    # Sensitive/legal answers are never auto-filled.
    assert "work_authorization" not in fill_fields
    manual = {f["field"] for f in body["manual_fields"]}
    assert "work_authorization" in manual

    # Legal declaration and submission gates always present.
    gate_codes = [g["code"] for g in body["gates"]]
    assert "legal_declaration" in gate_codes
    assert gate_codes[-1] == "submission_confirmation"
    assert body["pause_reason"] == "legal_declaration"


def test_captcha_gate_takes_priority(db_session: Session) -> None:
    from app.models.application_package import ApplicationPackage

    package = ApplicationPackage(
        job_id=1,
        candidate_profile_id=1,
        readiness_status="blocked_by_captcha",
        blockers=[{"code": "captcha", "detail": "x"}],
        risk_warnings=[],
        missing_items=[],
        assembly_version="test",
    )
    gates = build_gates(package)
    codes = [g["code"] for g in gates]
    assert codes[0] == "captcha"
    assert codes[-1] == "submission_confirmation"


def test_apply_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    job = build_ready_confirmed_package(client, db_session)

    first = client.post(f"/api/jobs/{job.id}/apply").json()
    second = client.post(f"/api/jobs/{job.id}/apply").json()
    assert first["id"] == second["id"]


# --- Resume / gate stepping (never auto-submits) --------------------------


def test_resume_steps_through_gates_and_records_submission(
    client: TestClient,
    db_session: Session,
) -> None:
    job = build_ready_confirmed_package(client, db_session)
    run = client.post(f"/api/jobs/{job.id}/apply").json()
    run_id = run["id"]
    assert run["pause_reason"] == "legal_declaration"

    # Acknowledge the legal declaration gate (handled by the human).
    after_legal = client.post(
        f"/api/application-runs/{run_id}/resume",
        json={},
    ).json()
    assert after_legal["status"] == "paused_for_gate"
    assert after_legal["pause_reason"] == "submission_confirmation"

    # At the submission gate, no confirmation number -> stays paused,
    # the tool never submits on its own.
    without_number = client.post(
        f"/api/application-runs/{run_id}/resume",
        json={},
    )
    assert without_number.status_code == 400

    still = client.get(f"/api/application-runs/{run_id}/status").json()
    assert still["status"] == "paused_for_gate"
    assert still["confirmation_number"] is None

    # Human submits externally and records the confirmation number.
    submitted = client.post(
        f"/api/application-runs/{run_id}/resume",
        json={"confirmation_number": "APP-12345"},
    ).json()
    assert submitted["status"] == "submitted"
    assert submitted["confirmation_number"] == "APP-12345"
    assert submitted["submitted_at"] is not None


def test_resume_after_submitted_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    job = build_ready_confirmed_package(client, db_session)
    run_id = client.post(f"/api/jobs/{job.id}/apply").json()["id"]
    client.post(f"/api/application-runs/{run_id}/resume", json={})
    client.post(
        f"/api/application-runs/{run_id}/resume",
        json={"confirmation_number": "APP-1"},
    )

    again = client.post(
        f"/api/application-runs/{run_id}/resume",
        json={"confirmation_number": "APP-2"},
    )
    assert again.status_code == 409


# --- Cancel ---------------------------------------------------------------


def test_cancel_run(
    client: TestClient,
    db_session: Session,
) -> None:
    job = build_ready_confirmed_package(client, db_session)
    run_id = client.post(f"/api/jobs/{job.id}/apply").json()["id"]

    cancelled = client.post(f"/api/application-runs/{run_id}/cancel").json()
    assert cancelled["status"] == "cancelled"

    resume = client.post(f"/api/application-runs/{run_id}/resume", json={})
    assert resume.status_code == 409


def test_status_missing_run_404(client: TestClient) -> None:
    response = client.get("/api/application-runs/999/status")
    assert response.status_code == 404
