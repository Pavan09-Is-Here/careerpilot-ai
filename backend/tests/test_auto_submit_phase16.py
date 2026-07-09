"""Phase 16 — One-click auto-apply tests.

The auto_submit driver may only start with the candidate's explicit
per-job consent, never pre-acknowledges safety gates, pauses (and
records a notification) whenever the candidate is needed, and submits
only through a source-permitted adapter. Where no adapter exists the
run ends exactly like manual assist: paused at the submission gate.
"""

from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.api.routes.auth import login_rate_limiter
from app.models.application_run import ApplicationRun
from app.models.job import NormalizedJob
from app.models.notification import Notification
from app.schemas.job import (
    JobCompensationCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)
from app.services.application_package import prepare_application_package
from app.services.application_run import (
    ApplicationRunServiceError,
    resume_application_run,
    start_application_run,
)
from app.services.job import create_job_source, create_normalized_job
from app.services.submission import (
    SubmissionResult,
    register_submission_driver,
)
from tests.conftest import Account
from tests.test_application_runs_phase10 import (
    add_answer,
    add_match,
    add_tailored_cv,
    content_hash,
    make_profile,
)


CONSENT = ["legal_declaration", "submission_confirmation"]


@pytest.fixture(autouse=True)
def _reset_auth_rate_limiter() -> None:
    login_rate_limiter.reset()


def make_job(
    database: Session,
    *,
    provider_type: str = "greenhouse",
    **overrides: object,
) -> NormalizedJob:
    source = create_job_source(
        JobSourceCreate(
            source_key=f"source-{uuid4().hex[:12]}",
            display_name="Example Robotics",
            source_category="provider_api",
            provider_type=provider_type,
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
        "normalization_version": "phase16-test",
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


def prepare_ready_job(
    database: Session,
    account: Account,
    *,
    provider_type: str = "greenhouse",
    with_manual_answer: bool = False,
    job_description: str | None = None,
) -> NormalizedJob:
    """A job with match, tailored CV, verified answers, and a prepared
    package — everything short of starting the run."""
    profile = make_profile(database, account)
    overrides: dict[str, object] = {}
    if job_description is not None:
        overrides["description_text"] = job_description
    job = make_job(
        database,
        provider_type=provider_type,
        **overrides,
    )
    add_match(database, job, profile)
    add_tailored_cv(database, job, profile)
    # Required plus recommended categories, so the package has no
    # risk warnings and is 'ready_for_automatic_application'.
    for category in (
        "work_authorization",
        "availability",
        "sponsorship",
        "expected_salary",
        "relocation",
        "notice_period",
    ):
        add_answer(
            database,
            category,
            candidate_profile_id=profile.id,
        )
    if with_manual_answer:
        # A sensitive/legal answer that must never be auto-filled.
        add_answer(
            database,
            "other",
            candidate_profile_id=profile.id,
            requires_manual_confirmation=True,
        )
    prepare_application_package(job.id, database, profile.id)
    return job


def notifications_for(
    database: Session,
    category: str,
) -> list[Notification]:
    return list(
        database.query(Notification)
        .filter(Notification.category == category)
        .all()
    )


# --- Consent ----------------------------------------------------------------


def test_auto_submit_requires_explicit_consent(
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    with pytest.raises(ApplicationRunServiceError) as excinfo:
        start_application_run(
            job.id,
            db_session,
            account.profile_id,
            driver="auto_submit",
            acknowledged_gates=["legal_declaration"],
        )
    assert excinfo.value.status_code == 400
    assert "acknowledging" in excinfo.value.safe_message


def test_safety_gates_cannot_be_pre_acknowledged(
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    with pytest.raises(ApplicationRunServiceError) as excinfo:
        start_application_run(
            job.id,
            db_session,
            account.profile_id,
            driver="auto_submit",
            acknowledged_gates=CONSENT + ["captcha"],
        )
    assert excinfo.value.status_code == 400
    assert "Safety gates" in excinfo.value.safe_message


def test_unknown_driver_rejected(
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    with pytest.raises(ApplicationRunServiceError):
        start_application_run(
            job.id,
            db_session,
            account.profile_id,
            driver="playwright_stealth",
        )


def test_api_rejects_unknown_acknowledged_gate(
    auth_client,
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    response = auth_client.post(
        f"/api/jobs/{job.id}/apply",
        json={
            "driver": "auto_submit",
            "acknowledged_gates": CONSENT + ["captcha"],
        },
    )
    assert response.status_code == 422


# --- Unsupported source: pause at submission gate ---------------------------


def test_auto_submit_unsupported_source_pauses_and_notifies(
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    run = start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )
    assert run.status == "paused_for_gate"
    assert run.pause_reason == "submission_confirmation"
    assert run.driver == "auto_submit"
    assert run.consented_at is not None
    assert run.submission_method is None
    gate_state = {g["code"]: g["acknowledged"] for g in run.gates}
    assert gate_state["legal_declaration"] is True
    assert gate_state["submission_confirmation"] is False
    notices = notifications_for(db_session, "manual_action_required")
    assert len(notices) == 1
    assert job.title in notices[0].subject
    # No SMTP configured in tests: recorded, not sent, never lost.
    assert notices[0].status == "pending"


def test_manual_resume_after_unsupported_records_manual_method(
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    run = start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )
    resumed = resume_application_run(
        run.id,
        "CONF-123",
        db_session,
        account.profile_id,
    )
    assert resumed.status == "submitted"
    assert resumed.submission_method == "manual"
    assert resumed.confirmation_number == "CONF-123"
    assert len(
        notifications_for(db_session, "application_submitted")
    ) == 1


# --- Permitted adapter: automatic submission ---------------------------------


def test_auto_submit_with_permitted_adapter_submits_and_notifies(
    db_session: Session,
    account: Account,
) -> None:
    def driver(job, package, fill_plan, database) -> SubmissionResult:
        assert any(f["field"] == "email" for f in fill_plan)
        return SubmissionResult(
            status="submitted",
            method="test_api",
            confirmation_number="API-42",
        )

    unregister = register_submission_driver("greenhouse", driver)
    try:
        job = prepare_ready_job(db_session, account)
        run = start_application_run(
            job.id,
            db_session,
            account.profile_id,
            driver="auto_submit",
            acknowledged_gates=CONSENT,
        )
    finally:
        unregister()

    assert run.status == "submitted"
    assert run.submission_method == "test_api"
    assert run.confirmation_number == "API-42"
    assert run.submitted_at is not None
    gate_state = {g["code"]: g["acknowledged"] for g in run.gates}
    assert all(gate_state.values())
    notices = notifications_for(db_session, "application_submitted")
    assert len(notices) == 1
    assert "API-42" in notices[0].body


def test_adapter_failure_is_contained_and_pauses(
    db_session: Session,
    account: Account,
) -> None:
    def driver(job, package, fill_plan, database) -> SubmissionResult:
        raise RuntimeError("provider exploded")

    unregister = register_submission_driver("greenhouse", driver)
    try:
        job = prepare_ready_job(db_session, account)
        run = start_application_run(
            job.id,
            db_session,
            account.profile_id,
            driver="auto_submit",
            acknowledged_gates=CONSENT,
        )
    finally:
        unregister()

    assert run.status == "paused_for_gate"
    assert run.pause_reason == "submission_confirmation"
    assert run.error is not None
    assert "provider exploded" not in run.error  # safe message only


# --- Candidate-required pauses ----------------------------------------------


def test_manual_fields_block_automatic_submission(
    db_session: Session,
    account: Account,
) -> None:
    def driver(job, package, fill_plan, database) -> SubmissionResult:
        raise AssertionError(
            "Submission must never be attempted with manual fields."
        )

    unregister = register_submission_driver("greenhouse", driver)
    try:
        job = prepare_ready_job(
            db_session,
            account,
            with_manual_answer=True,
        )
        # The sensitive answer makes the package 'needs_user_review';
        # the candidate reviews and confirms it, but the sensitive
        # entry itself must still block automatic submission.
        from app.models.application_package import ApplicationPackage

        package = (
            db_session.query(ApplicationPackage)
            .filter(ApplicationPackage.job_id == job.id)
            .one()
        )
        package.user_confirmed = True
        db_session.commit()
        run = start_application_run(
            job.id,
            db_session,
            account.profile_id,
            driver="auto_submit",
            acknowledged_gates=CONSENT,
        )
    finally:
        unregister()

    assert run.status == "paused_for_gate"
    assert run.pause_reason == "manual_fields_required"
    assert run.manual_fields
    notices = notifications_for(db_session, "manual_action_required")
    assert len(notices) == 1
    assert "other" in notices[0].body


def test_captcha_blocker_pauses_auto_run(
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(
        db_session,
        account,
        job_description=(
            "Great role. A CAPTCHA challenge protects the application "
            "form."
        ),
    )
    run = start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )
    assert run.status == "paused_for_gate"
    assert run.pause_reason == "captcha"
    gate_state = {g["code"]: g["acknowledged"] for g in run.gates}
    assert gate_state["captcha"] is False
    notices = notifications_for(db_session, "manual_action_required")
    assert len(notices) == 1


# --- Package readiness rules -------------------------------------------------


def test_needs_user_review_is_never_skipped(
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    from app.models.application_package import ApplicationPackage

    package = (
        db_session.query(ApplicationPackage)
        .filter(ApplicationPackage.job_id == job.id)
        .one()
    )
    package.readiness_status = "needs_user_review"
    package.user_confirmed = False
    db_session.commit()

    with pytest.raises(ApplicationRunServiceError) as excinfo:
        start_application_run(
            job.id,
            db_session,
            account.profile_id,
            driver="auto_submit",
            acknowledged_gates=CONSENT,
        )
    assert excinfo.value.status_code == 409


def test_consent_confirms_ready_package(
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    from app.models.application_package import ApplicationPackage

    package = (
        db_session.query(ApplicationPackage)
        .filter(ApplicationPackage.job_id == job.id)
        .one()
    )
    package.readiness_status = "ready_for_automatic_application"
    package.user_confirmed = False
    db_session.commit()

    run = start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )
    db_session.refresh(package)
    assert package.user_confirmed is True
    assert run.status == "paused_for_gate"  # unsupported source


def test_auto_reprepares_stale_blocked_package(
    db_session: Session,
    account: Account,
) -> None:
    """A package stuck in 'blocked_by_missing_information' from an
    earlier attempt must not block one-click apply forever: once the
    missing verified data exists, the auto chain re-prepares it."""
    profile = make_profile(db_session, account)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)

    # First preparation happens with NO verified answers on file, so
    # the package is blocked by missing information.
    stale = prepare_application_package(
        job.id, db_session, profile.id
    )
    assert stale.readiness_status == "blocked_by_missing_information"

    # The candidate then adds the required (and recommended) verified
    # answers — exactly the fix the blocked panel asks for.
    for category in (
        "work_authorization",
        "availability",
        "sponsorship",
        "expected_salary",
        "relocation",
        "notice_period",
    ):
        add_answer(
            db_session,
            category,
            candidate_profile_id=profile.id,
        )

    run = start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )

    db_session.refresh(stale)
    assert stale.readiness_status == (
        "ready_for_automatic_application"
    )
    assert run.status == "paused_for_gate"  # unsupported source
    assert run.pause_reason == "submission_confirmation"


def test_auto_never_resets_confirmed_reviewable_package(
    db_session: Session,
    account: Account,
) -> None:
    """Re-preparation must not touch a reviewable package the
    candidate already confirmed — their confirmation stands."""
    from app.models.application_package import ApplicationPackage

    job = prepare_ready_job(db_session, account)
    package = (
        db_session.query(ApplicationPackage)
        .filter(ApplicationPackage.job_id == job.id)
        .one()
    )
    package.readiness_status = "needs_user_review"
    package.user_confirmed = True
    db_session.commit()

    run = start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )
    db_session.refresh(package)
    assert package.user_confirmed is True
    assert run.status == "paused_for_gate"


def test_auto_builds_full_cv_lineage_from_uploaded_document(
    db_session: Session,
    account: Account,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """With only an uploaded CV document on file (no versions at
    all), one-click apply builds original -> parsed -> verified
    master -> tailored CV automatically and proceeds."""
    from app.models.cv_version import CVVersion
    from app.models.document import Document
    from app.models.skill import Skill
    from datetime import datetime, timezone

    monkeypatch.setenv(
        "CAREERPILOT_GENERATED_CV_STORAGE_DIR",
        str(tmp_path / "generated"),
    )

    profile = make_profile(db_session, account)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    for category in (
        "work_authorization",
        "availability",
        "sponsorship",
        "expected_salary",
        "relocation",
        "notice_period",
    ):
        add_answer(
            db_session,
            category,
            candidate_profile_id=profile.id,
        )
    # A verified skill so the master CV has vault content.
    db_session.add(
        Skill(
            candidate_profile_id=profile.id,
            name="Python",
            proficiency="advanced",
            verified=True,
        )
    )
    # The uploaded CV document — the only CV artifact on file.
    db_session.add(
        Document(
            candidate_profile_id=profile.id,
            original_filename="cv.pdf",
            stored_filename="stored-cv.pdf",
            file_extension=".pdf",
            media_type="application/pdf",
            size_bytes=100,
            sha256_hash="a" * 64,
            document_type="original_cv",
            upload_status="validated",
            is_primary=True,
        )
    )
    db_session.commit()

    now = datetime.now(timezone.utc)
    assert now is not None  # keep import used for clarity

    run = start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )

    types = {
        version.version_type
        for version in db_session.query(CVVersion).all()
    }
    assert {
        "original",
        "parsed",
        "verified_master",
        "tailored",
    }.issubset(types)
    assert run.status == "paused_for_gate"  # unsupported source
    assert run.pause_reason == "submission_confirmation"

    # The self-referential CV lineage (parent_version_id) prevents a
    # clean drop_all teardown on SQLite; clear the rows explicitly,
    # mirroring the Phase 6 suite's cleanup pattern.
    from sqlalchemy import text

    db_session.rollback()
    db_session.execute(text("PRAGMA foreign_keys=OFF"))
    for table_name in (
        "application_runs",
        "application_packages",
        "job_tailored_cvs",
        "cv_version_artifacts",
        "cv_versions",
        "documents",
    ):
        db_session.execute(text(f"DELETE FROM {table_name}"))
    db_session.commit()
    db_session.execute(text("PRAGMA foreign_keys=ON"))


def test_auto_apply_without_uploaded_cv_gives_clear_error(
    db_session: Session,
    account: Account,
) -> None:
    profile = make_profile(db_session, account)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    for category in ("work_authorization", "availability"):
        add_answer(
            db_session,
            category,
            candidate_profile_id=profile.id,
        )

    with pytest.raises(ApplicationRunServiceError) as excinfo:
        start_application_run(
            job.id,
            db_session,
            account.profile_id,
            driver="auto_submit",
            acknowledged_gates=CONSENT,
        )
    assert excinfo.value.status_code == 409
    assert "Upload your CV" in excinfo.value.safe_message


def test_auto_apply_sets_tailored_cv_as_primary(
    db_session: Session,
    account: Account,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    """Every application follows the same process: the CV tailored for
    the job becomes the candidate's primary tailored CV automatically."""
    from app.models.cv_version import CVVersion
    from app.models.document import Document
    from app.models.skill import Skill

    monkeypatch.setenv(
        "CAREERPILOT_GENERATED_CV_STORAGE_DIR",
        str(tmp_path / "generated"),
    )

    profile = make_profile(db_session, account)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    for category in (
        "work_authorization",
        "availability",
        "sponsorship",
        "expected_salary",
        "relocation",
        "notice_period",
    ):
        add_answer(
            db_session,
            category,
            candidate_profile_id=profile.id,
        )
    db_session.add(
        Skill(
            candidate_profile_id=profile.id,
            name="Python",
            proficiency="advanced",
            verified=True,
        )
    )
    db_session.add(
        Document(
            candidate_profile_id=profile.id,
            original_filename="cv.pdf",
            stored_filename="stored-cv.pdf",
            file_extension=".pdf",
            media_type="application/pdf",
            size_bytes=100,
            sha256_hash="a" * 64,
            document_type="original_cv",
            upload_status="validated",
            is_primary=True,
        )
    )
    db_session.commit()

    start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )

    tailored = (
        db_session.query(CVVersion)
        .filter(
            CVVersion.candidate_profile_id == profile.id,
            CVVersion.version_type == "tailored",
        )
        .one()
    )
    assert tailored.is_primary is True

    from sqlalchemy import text

    db_session.rollback()
    db_session.execute(text("PRAGMA foreign_keys=OFF"))
    for table_name in (
        "application_runs",
        "application_packages",
        "job_tailored_cvs",
        "cv_version_artifacts",
        "cv_versions",
        "documents",
    ):
        db_session.execute(text(f"DELETE FROM {table_name}"))
    db_session.commit()
    db_session.execute(text("PRAGMA foreign_keys=ON"))


def test_auto_prepares_missing_package(
    db_session: Session,
    account: Account,
) -> None:
    """With match and tailored CV present but no package, one-click
    apply prepares the package itself."""
    profile = make_profile(db_session, account)
    job = make_job(db_session)
    add_match(db_session, job, profile)
    add_tailored_cv(db_session, job, profile)
    for category in (
        "work_authorization",
        "availability",
        "sponsorship",
        "expected_salary",
        "relocation",
        "notice_period",
    ):
        add_answer(
            db_session,
            category,
            candidate_profile_id=profile.id,
        )

    run = start_application_run(
        job.id,
        db_session,
        account.profile_id,
        driver="auto_submit",
        acknowledged_gates=CONSENT,
    )
    assert run.application_package_id is not None
    assert run.status == "paused_for_gate"


# --- Manual assist unchanged --------------------------------------------------


def test_manual_assist_default_unchanged(
    auth_client,
    db_session: Session,
    account: Account,
) -> None:
    job = prepare_ready_job(db_session, account)
    from app.models.application_package import ApplicationPackage

    package = (
        db_session.query(ApplicationPackage)
        .filter(ApplicationPackage.job_id == job.id)
        .one()
    )
    package.user_confirmed = True
    db_session.commit()

    response = auth_client.post(f"/api/jobs/{job.id}/apply")
    assert response.status_code == 201
    body = response.json()
    assert body["driver"] == "manual_assist"
    assert body["consented_at"] is None
    assert body["submission_method"] is None
    assert body["status"] == "paused_for_gate"
    run = db_session.get(ApplicationRun, body["id"])
    assert run is not None
    assert run.consented_at is None
