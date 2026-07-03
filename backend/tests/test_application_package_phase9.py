"""Phase 9 — Application Preparation package tests."""

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
from app.models.skill import Skill
from app.schemas.job import (
    JobCompensationCreate,
    JobSkillRequirementCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)
from app.api.routes.auth import login_rate_limiter
from app.services.application_package import (
    ApplicationPackageServiceError,
    prepare_application_package,
)
from app.services.job import create_job_source, create_normalized_job
from tests.conftest import Account, register_account


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter() -> None:
    login_rate_limiter.reset()


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_profile(
    database: Session,
    account: Account,
    **overrides: object,
) -> CandidateProfile:
    """Return the account's own profile, applying any relied-on fields."""
    values: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "professional_title": "Platform Engineer",
        "professional_summary": "Verified engineer summary.",
        "work_authorization": "UK citizen",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": ["remote"],
        "target_roles": ["Platform Engineer"],
        "preferred_locations": ["London"],
        "salary_currency": "GBP",
        "minimum_match_score": 50,
        "auto_apply_enabled": False,
        "facts_verified": True,
    }
    values.update(overrides)
    profile = database.get(CandidateProfile, account.profile_id)
    assert profile is not None
    for key, value in values.items():
        setattr(profile, key, value)
    database.commit()
    database.refresh(profile)
    return profile


def make_job(
    database: Session,
    *,
    skills: list[tuple[str, str]] | None = None,
    compensations: list[JobCompensationCreate] | None = None,
    **overrides: object,
) -> NormalizedJob:
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
        "normalization_version": "phase9-test",
    }
    payload.update(overrides)
    return create_normalized_job(
        NormalizedJobCreate(**payload),
        database,
        compensations=compensations or [],
        skill_requirements=[
            JobSkillRequirementCreate(
                skill_text=name,
                requirement_type=requirement_type,
            )
            for name, requirement_type in (skills or [])
        ],
    )


def add_verified_skill(
    database: Session,
    profile: CandidateProfile,
    name: str,
) -> None:
    database.add(
        Skill(
            candidate_profile_id=profile.id,
            name=name,
            proficiency="advanced",
            verified=True,
        )
    )
    database.commit()


def add_match(
    database: Session,
    job: NormalizedJob,
    profile: CandidateProfile,
    *,
    eligibility_status: str = "eligible",
    match_score: int | None = 80,
    blocker_reason: str | None = None,
) -> JobMatch:
    now = datetime.now(timezone.utc)
    match = JobMatch(
        job_id=job.id,
        candidate_profile_id=profile.id,
        match_score=match_score,
        eligibility_status=eligibility_status,
        blocker_reason=blocker_reason,
        explanation="test match",
        algorithm_version="match-algorithm-1",
        created_at=now,
        updated_at=now,
    )
    database.add(match)
    database.commit()
    return match


def add_tailored_cv(
    database: Session,
    job: NormalizedJob,
    profile: CandidateProfile,
    *,
    status: str = "ready",
    artifact_types: tuple[str, ...] = ("docx", "pdf"),
) -> CVVersion:
    now = datetime.now(timezone.utc)
    version = CVVersion(
        candidate_profile_id=profile.id,
        source_document_id=None,
        parent_version_id=None,
        version_type="tailored",
        status=status,
        display_name="Tailored CV",
        description=None,
        job_reference=f"{job.employer_name} — {job.title}",
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

    for artifact_type in artifact_types:
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
    return version


def add_answer(
    database: Session,
    category: str,
    *,
    candidate_profile_id: int,
    verified: bool = True,
    requires_manual_confirmation: bool = False,
    manually_confirmed: bool = False,
) -> ApplicationAnswer:
    now = datetime.now(timezone.utc)
    answer = ApplicationAnswer(
        candidate_profile_id=candidate_profile_id,
        category=category,
        question_label=f"{category} question",
        answer_text=f"Verified {category} answer.",
        verified=verified,
        manually_confirmed=manually_confirmed,
        requires_manual_confirmation=requires_manual_confirmation,
        created_at=now,
        updated_at=now,
    )
    database.add(answer)
    database.commit()
    return answer


def add_all_answers(database: Session, candidate_profile_id: int) -> None:
    # Required.
    add_answer(
        database,
        "work_authorization",
        candidate_profile_id=candidate_profile_id,
        requires_manual_confirmation=True,
        manually_confirmed=True,
    )
    add_answer(
        database, "availability", candidate_profile_id=candidate_profile_id
    )
    # Recommended.
    add_answer(
        database,
        "sponsorship",
        candidate_profile_id=candidate_profile_id,
        requires_manual_confirmation=True,
        manually_confirmed=True,
    )
    add_answer(
        database,
        "expected_salary",
        candidate_profile_id=candidate_profile_id,
    )
    add_answer(
        database, "relocation", candidate_profile_id=candidate_profile_id
    )
    add_answer(
        database, "notice_period", candidate_profile_id=candidate_profile_id
    )


# --- Preconditions --------------------------------------------------------


def test_prepare_requires_job(
    db_session: Session,
    account: Account,
) -> None:
    with pytest.raises(ApplicationPackageServiceError) as exc:
        prepare_application_package(
            999, db_session, candidate_profile_id=account.profile_id
        )
    assert exc.value.status_code == 404


def test_prepare_requires_profile(
    db_session: Session,
    account: Account,
) -> None:
    job = make_job(db_session)
    # An authenticated caller whose profile row is absent yields a 404
    # rather than the legacy "create the profile first" 400 path.
    missing_profile_id = account.profile_id + 999
    with pytest.raises(ApplicationPackageServiceError) as exc:
        prepare_application_package(
            job.id, db_session, candidate_profile_id=missing_profile_id
        )
    assert exc.value.status_code == 404


# --- Readiness precedence -------------------------------------------------


def test_missing_information_when_nothing_assembled(
    db_session: Session,
    account: Account,
) -> None:
    make_profile(db_session, account)
    job = make_job(db_session)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "blocked_by_missing_information"
    joined = " ".join(package.missing_items)
    assert "job match" in joined
    assert "tailored CV" in joined
    assert "work_authorization" in joined
    assert "availability" in joined


def test_not_eligible_takes_precedence(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(db_session)
    add_match(db_session, job, profile, eligibility_status="ineligible")

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "not_eligible"


def test_blocked_by_captcha(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(
        db_session,
        description_text="Apply here; you must solve a reCAPTCHA.",
    )
    add_match(db_session, job, profile)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "blocked_by_captcha"
    assert any(b["code"] == "captcha" for b in package.blockers)


def test_blocked_by_mfa(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(
        db_session,
        description_text="You will receive a verification code (2FA).",
    )
    add_match(db_session, job, profile)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "blocked_by_mfa"


def test_blocked_by_assessment(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(
        db_session,
        description_text="Includes a timed HackerRank coding assessment.",
    )
    add_match(db_session, job, profile)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "blocked_by_assessment"


def test_captcha_precedes_assessment(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(
        db_session,
        description_text="Solve the captcha, then a coding assessment.",
    )
    add_match(db_session, job, profile)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "blocked_by_captcha"


def test_needs_user_review_with_risks(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(db_session, skills=[("Python", "required")])
    add_verified_skill(db_session, profile, "Python")
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)
    # Only required answers; recommended answers absent -> risks.
    add_answer(
        db_session,
        "work_authorization",
        candidate_profile_id=account.profile_id,
        requires_manual_confirmation=True,
        manually_confirmed=True,
    )
    add_answer(
        db_session, "availability", candidate_profile_id=account.profile_id
    )

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "needs_user_review"
    assert package.missing_items == []
    assert package.risk_warnings


def test_ready_for_automatic_application(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account, minimum_salary=None)
    job = make_job(
        db_session,
        skills=[("Python", "required")],
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
    add_verified_skill(db_session, profile, "Python")
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)
    add_all_answers(db_session, account.profile_id)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "ready_for_automatic_application"
    assert package.missing_items == []
    assert package.risk_warnings == []


def test_conditional_match_forces_review(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account, minimum_salary=None)
    job = make_job(
        db_session,
        compensations=[
            JobCompensationCreate(
                min_amount=Decimal("70000"),
                max_amount=Decimal("90000"),
                currency="GBP",
                compensation_period="yearly",
                source_text="range",
            )
        ],
    )
    add_match(
        db_session,
        job,
        profile,
        eligibility_status="conditionally_eligible",
        blocker_reason="Manual review required: sponsorship unknown",
    )
    add_tailored_cv(db_session, job, profile)
    add_all_answers(db_session, account.profile_id)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "needs_user_review"
    assert any("conditional" in r.lower() for r in package.risk_warnings)


def test_unverified_tailored_cv_is_missing(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    add_tailored_cv(
        db_session,
        job,
        profile,
        artifact_types=("docx",),
    )
    add_answer(
        db_session,
        "work_authorization",
        candidate_profile_id=account.profile_id,
        requires_manual_confirmation=True,
        manually_confirmed=True,
    )
    add_answer(
        db_session, "availability", candidate_profile_id=account.profile_id
    )

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.readiness_status == "blocked_by_missing_information"
    assert any("artifacts" in item for item in package.missing_items)


# --- Cover letter (verified facts only) -----------------------------------


def test_cover_letter_uses_verified_content(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(db_session, skills=[("Python", "required")])
    add_verified_skill(db_session, profile, "Python")
    add_answer(
        db_session,
        "company_interest",
        candidate_profile_id=account.profile_id,
    )
    add_match(db_session, job, profile)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    letter = package.cover_letter_text
    assert letter is not None
    assert "Example Robotics" in letter
    assert "Platform Engineer" in letter
    assert "Verified engineer summary." in letter
    assert "Verified company_interest answer." in letter
    assert "Python" in letter
    assert "Test Candidate" in letter


def test_cover_letter_none_when_profile_unverified(
    db_session: Session,
    account: Account,
) -> None:
    make_profile(db_session, account, facts_verified=False)
    job = make_job(db_session)

    package = prepare_application_package(
        job.id, db_session, candidate_profile_id=account.profile_id
    )

    assert package.cover_letter_text is None
    assert any(
        "verified candidate profile" in item
        for item in package.missing_items
    )


# --- API endpoints --------------------------------------------------------


def test_get_before_prepare_returns_404(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    make_profile(db_session, account)
    job = make_job(db_session)

    response = client.get(
        f"/api/jobs/{job.id}/application-package",
        headers=account.headers,
    )
    assert response.status_code == 404


def test_prepare_requires_authentication(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post("/api/jobs/1/prepare-application")
    assert response.status_code == 401


def test_prepare_and_get_roundtrip(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(db_session)
    add_match(db_session, job, profile)

    prepared = client.post(
        f"/api/jobs/{job.id}/prepare-application",
        headers=account.headers,
    )
    assert prepared.status_code == 201
    body = prepared.json()
    assert body["job_id"] == job.id
    assert body["job"]["employer_name"] == "Example Robotics"
    assert body["match"]["eligibility_status"] == "eligible"
    assert body["salary"] is not None

    fetched = client.get(
        f"/api/jobs/{job.id}/application-package",
        headers=account.headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["readiness_status"] == body["readiness_status"]


def test_confirm_blocked_package_rejected(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    make_profile(db_session, account)
    job = make_job(db_session)

    client.post(
        f"/api/jobs/{job.id}/prepare-application",
        headers=account.headers,
    )

    response = client.put(
        f"/api/jobs/{job.id}/application-package",
        json={"user_confirmed": True},
        headers=account.headers,
    )
    assert response.status_code == 400


def test_confirm_review_package_succeeds_and_reprepare_resets(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(db_session, skills=[("Python", "required")])
    add_verified_skill(db_session, profile, "Python")
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)
    add_answer(
        db_session,
        "work_authorization",
        candidate_profile_id=account.profile_id,
        requires_manual_confirmation=True,
        manually_confirmed=True,
    )
    add_answer(
        db_session, "availability", candidate_profile_id=account.profile_id
    )

    prepared = client.post(
        f"/api/jobs/{job.id}/prepare-application",
        headers=account.headers,
    )
    assert prepared.json()["readiness_status"] == "needs_user_review"

    confirmed = client.put(
        f"/api/jobs/{job.id}/application-package",
        json={"user_confirmed": True, "user_notes": "Looks good."},
        headers=account.headers,
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["user_confirmed"] is True
    assert confirmed.json()["user_notes"] == "Looks good."

    reprepared = client.post(
        f"/api/jobs/{job.id}/prepare-application",
        headers=account.headers,
    )
    assert reprepared.json()["user_confirmed"] is False
