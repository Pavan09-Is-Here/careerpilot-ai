"""Browser-assisted application workflow (Phase 10).

Human-in-the-loop assistance, never autonomous submission. The
workflow maps application form fields to verified vault data and
enforces mandatory safety pauses. It never bypasses CAPTCHA, MFA,
bot detection, rate limits, access controls, or terms of service,
and it never submits an application on its own: the candidate
performs every gated step (CAPTCHA, MFA, assessments, legal
declarations) and the final irreversible submission, then records
the confirmation number so the run can track it.

The live browser driver (e.g. Playwright) is intentionally abstracted
and deferred: the default 'manual_assist' driver plans and pauses
only. Any future live driver must route through these same gates and
must not bypass site protections.

Phase 16 adds the 'auto_submit' driver: one explicit per-job consent
action from the candidate (acknowledging the legal declarations and
the irreversible submission) lets the run prepare everything and, ONLY
where the job's source offers a permitted submission channel, submit
through it. CAPTCHA/MFA/assessment gates, sensitive answers, and
missing required answers always pause the run and notify the candidate
by email; they are never bypassed. Where no permitted channel exists
the run pauses at the submission gate for the candidate to submit
manually — exactly like manual assist.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.application_package import ApplicationPackage
from app.models.application_run import ApplicationRun
from app.models.candidate_profile import CandidateProfile
from app.models.job import NormalizedJob
from app.schemas.cv_version import CVMasterGenerationRequest
from app.services.application_package import (
    ApplicationPackageServiceError,
    load_answers,
    load_job_match,
    load_tailored_cv,
    prepare_application_package,
)
from app.services.cv_tailoring import CVTailoringError, generate_tailored_cv
from app.services.job_match import JobMatchServiceError, analyze_job_match
from app.services.notification import (
    create_notification,
    send_email_best_effort,
    smtp_configured,
)
from app.services.submission import attempt_submission


WORKFLOW_VERSION = "browser-assist-1"
PREVIEW_LIMIT = 200

TERMINAL_STATUSES = frozenset({"submitted", "cancelled", "failed"})

REQUIRED_ANSWER_CATEGORIES = ("work_authorization", "availability")
AUTOFILL_ANSWER_CATEGORIES = (
    "availability",
    "notice_period",
    "relocation",
    "remote_preference",
    "expected_salary",
    "company_interest",
)

# Deterministic gate precedence. Safety gates first, the irreversible
# submission always last.
GATE_ORDER = (
    "captcha",
    "mfa",
    "assessment",
    "legal_declaration",
    "submission_confirmation",
)

GATE_DETAILS = {
    "captcha": (
        "A CAPTCHA or human-verification challenge is present. Solve "
        "it yourself in the browser; the tool will not bypass it."
    ),
    "mfa": (
        "Multi-factor or code-based verification is required. Complete "
        "it yourself; the tool will not circumvent it."
    ),
    "assessment": (
        "A skills assessment or test is required. Complete it "
        "yourself; the tool will not take it for you."
    ),
    "legal_declaration": (
        "Legal declarations and consent (such as work authorization "
        "and background-check consent) must be reviewed and confirmed "
        "by you before submission."
    ),
    "submission_confirmation": (
        "Final submission is irreversible and must be performed by "
        "you. After submitting, provide the confirmation number to "
        "record it."
    ),
}

RUN_DRIVERS = ("manual_assist", "auto_submit")

# Gates the candidate must explicitly acknowledge in the apply action
# itself before an auto-submit run may start. This is the recorded
# consent: without it the run is rejected, and it never covers safety
# gates (CAPTCHA/MFA/assessment), which cannot be pre-acknowledged.
AUTO_CONSENT_GATES = frozenset(
    {"legal_declaration", "submission_confirmation"}
)

# Safety gates that always pause an auto-submit run for the candidate.
SAFETY_GATES = frozenset({"captcha", "mfa", "assessment"})

# Package readiness states that may never begin an application run.
REJECTED_READINESS = frozenset(
    {"not_eligible", "blocked_by_missing_information"}
)
# Readiness states that require explicit package confirmation first.
CONFIRMATION_REQUIRED_READINESS = frozenset(
    {"ready_for_automatic_application", "needs_user_review"}
)


class ApplicationRunServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def bounded(text: str) -> str:
    return text.strip()[:PREVIEW_LIMIT]


# --- Fill plan ------------------------------------------------------------


def build_fill_plan_and_manual(
    profile: CandidateProfile,
    package: ApplicationPackage,
    database: Session,
    candidate_profile_id: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    answers = load_answers(database, candidate_profile_id)
    tailored = load_tailored_cv(package.job_id, database)

    fill_plan: list[dict[str, object]] = []
    manual_fields: list[dict[str, object]] = []

    # Verified profile identity fields.
    fill_plan.append(
        {
            "field": "full_name",
            "field_type": "text",
            "source": "profile",
            "action": "autofill",
            "preview": bounded(profile.full_name),
        }
    )
    fill_plan.append(
        {
            "field": "email",
            "field_type": "email",
            "source": "profile",
            "action": "autofill",
            "preview": bounded(profile.email),
        }
    )
    if profile.phone:
        fill_plan.append(
            {
                "field": "phone",
                "field_type": "text",
                "source": "profile",
                "action": "autofill",
                "preview": bounded(profile.phone),
            }
        )

    verified_by_category: dict[str, list] = {}
    for answer in answers:
        verified_by_category.setdefault(answer.category, []).append(
            answer
        )

    # Auto-fillable, non-sensitive verified answers only.
    for category in AUTOFILL_ANSWER_CATEGORIES:
        for answer in verified_by_category.get(category, []):
            if answer.verified and not answer.requires_manual_confirmation:
                fill_plan.append(
                    {
                        "field": category,
                        "field_type": "text",
                        "source": "answer_vault",
                        "action": "autofill",
                        "preview": bounded(answer.answer_text),
                    }
                )

    # Cover letter and CV attachment.
    if package.cover_letter_text:
        fill_plan.append(
            {
                "field": "cover_letter",
                "field_type": "textarea",
                "source": "application_package",
                "action": "autofill",
                "preview": bounded(package.cover_letter_text),
            }
        )
    if tailored is not None:
        _version, artifacts = tailored
        pdf = next(
            (a for a in artifacts if a.artifact_type == "pdf"),
            None,
        )
        if pdf is not None:
            fill_plan.append(
                {
                    "field": "resume",
                    "field_type": "file",
                    "source": "tailored_cv",
                    "action": "attach_file_manually",
                    "preview": pdf.safe_filename,
                }
            )

    # Sensitive/legal answers are never auto-filled: flag for review.
    for answer in answers:
        if answer.requires_manual_confirmation:
            manual_fields.append(
                {
                    "field": answer.category,
                    "reason": (
                        "Legal or sensitive declaration — review and "
                        "confirm before submission; never auto-filled."
                    ),
                }
            )

    # Missing required answers must be provided manually.
    verified_categories = {
        answer.category for answer in answers if answer.verified
    }
    for category in REQUIRED_ANSWER_CATEGORIES:
        if category not in verified_categories:
            manual_fields.append(
                {
                    "field": category,
                    "reason": (
                        "No verified answer on file — provide this "
                        "manually."
                    ),
                }
            )

    return fill_plan, manual_fields


# --- Gates ----------------------------------------------------------------


def build_gates(
    package: ApplicationPackage,
) -> list[dict[str, object]]:
    blocker_codes = {
        blocker.get("code") for blocker in package.blockers
    }

    gates: list[dict[str, object]] = []
    for code in GATE_ORDER:
        include = False
        if code in {"captcha", "mfa", "assessment"}:
            include = code in blocker_codes
        else:
            # legal_declaration and submission_confirmation always apply.
            include = True

        if include:
            gates.append(
                {
                    "code": code,
                    "detail": GATE_DETAILS[code],
                    "acknowledged": False,
                }
            )
    return gates


def first_unacknowledged_gate(
    gates: list[dict[str, object]],
) -> dict[str, object] | None:
    for gate in gates:
        if not gate.get("acknowledged"):
            return gate
    return None


# --- Workflow -------------------------------------------------------------


def get_job_or_404(job_id: int, database: Session) -> NormalizedJob:
    job = database.get(NormalizedJob, job_id)
    if job is None:
        raise ApplicationRunServiceError(
            "Job was not found.",
            status_code=404,
        )
    return job


def require_profile(
    database: Session,
    candidate_profile_id: int,
) -> CandidateProfile:
    profile = database.get(CandidateProfile, candidate_profile_id)
    if profile is None:
        raise ApplicationRunServiceError(
            "Create the candidate profile before applying.",
            status_code=404,
        )
    return profile


def active_run_for_job(
    job_id: int,
    database: Session,
) -> ApplicationRun | None:
    return database.scalar(
        select(ApplicationRun)
        .where(
            ApplicationRun.job_id == job_id,
            ApplicationRun.status == "paused_for_gate",
        )
        .order_by(ApplicationRun.id.desc())
    )


def _ensure_package_ready(
    job: NormalizedJob,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationPackage:
    """Auto-prepare chain for one-click apply: analyze the match,
    tailor the CV, and prepare the package when missing. Every step
    uses the existing verified-facts services — nothing is fabricated,
    and an unverified profile still fails CV tailoring as always.
    """
    if load_job_match(job.id, database, candidate_profile_id) is None:
        try:
            analyze_job_match(
                job.id,
                database,
                candidate_profile_id=candidate_profile_id,
            )
        except JobMatchServiceError as exc:
            raise ApplicationRunServiceError(
                exc.safe_message,
                status_code=exc.status_code,
            ) from exc

    if load_tailored_cv(job.id, database) is None:
        request = CVMasterGenerationRequest(
            idempotency_key=(
                f"auto-apply-job-{job.id}-profile-{candidate_profile_id}"
            ),
        )
        try:
            generate_tailored_cv(
                job.id,
                request,
                database,
                candidate_profile_id=candidate_profile_id,
            )
        except CVTailoringError as exc:
            raise ApplicationRunServiceError(
                exc.safe_message,
                status_code=exc.status_code,
            ) from exc

    package = database.scalar(
        select(ApplicationPackage).where(
            ApplicationPackage.job_id == job.id
        )
    )
    if package is None:
        try:
            package = prepare_application_package(
                job.id,
                database,
                candidate_profile_id,
            )
        except ApplicationPackageServiceError as exc:
            raise ApplicationRunServiceError(
                exc.safe_message,
                status_code=exc.status_code,
            ) from exc
    return package


def notify_run_event(
    database: Session,
    settings: Settings | None,
    run: ApplicationRun,
    job: NormalizedJob,
    *,
    event: str,
    subject: str,
    body: str,
) -> None:
    """Record a notification for a run event and attempt immediate
    best-effort email delivery. Never raises: a notification problem
    must not fail the application run.
    """
    category = (
        "application_submitted"
        if event == "submitted"
        else "manual_action_required"
    )
    notification = create_notification(
        database,
        candidate_profile_id=run.candidate_profile_id,
        category=category,
        subject=subject,
        body=body,
        related_job_id=job.id,
        dedupe_key=f"application-run-{run.id}-{event}",
    )
    if (
        notification is None
        or notification.status != "pending"
        or settings is None
        or not smtp_configured(settings)
    ):
        return
    delivered = send_email_best_effort(
        notification.recipient,
        notification.subject,
        notification.body,
        settings,
    )
    if delivered:
        notification.status = "sent"
        notification.sent_at = current_utc_time()
    else:
        notification.status = "failed"
        notification.error = "SMTP delivery failed; see server logs."
    database.commit()


def _manual_fields_summary(
    manual_fields: list[dict[str, object]],
) -> str:
    lines = [
        f"- {field.get('field')}: {field.get('reason')}"
        for field in manual_fields
    ]
    return "\n".join(lines)


def _progress_auto_submit(
    run: ApplicationRun,
    job: NormalizedJob,
    package: ApplicationPackage,
    database: Session,
    settings: Settings | None,
) -> ApplicationRun:
    """Progress a freshly created auto-submit run as far as safety
    allows: pause on safety gates or manual fields, otherwise attempt
    submission through a source-permitted channel.
    """
    gates = [dict(gate) for gate in run.gates]
    current = first_unacknowledged_gate(gates)

    if current is not None and current["code"] in SAFETY_GATES:
        notify_run_event(
            database,
            settings,
            run,
            job,
            event="action_required",
            subject=f"Action needed to apply: {job.title}",
            body=(
                f"Your application for '{job.title}' is prepared but "
                f"paused: {GATE_DETAILS[current['code']]} Open "
                "CareerPilot to continue."
            ),
        )
        return run

    if run.manual_fields:
        run.pause_reason = "manual_fields_required"
        run.updated_at = current_utc_time()
        database.commit()
        database.refresh(run)
        notify_run_event(
            database,
            settings,
            run,
            job,
            event="action_required",
            subject=f"Manual entries needed to apply: {job.title}",
            body=(
                f"Your application for '{job.title}' is prepared, but "
                "these entries need you before submission:\n"
                f"{_manual_fields_summary(run.manual_fields)}\n\n"
                "Complete them, submit, and record the confirmation "
                "number in CareerPilot."
            ),
        )
        return run

    # No safety gate and nothing manual: attempt permitted submission.
    result = attempt_submission(job, package, run.fill_plan, database)
    now = current_utc_time()

    if result.status == "submitted":
        for gate in gates:
            if gate["code"] == "submission_confirmation":
                gate["acknowledged"] = True
        run.gates = gates
        run.status = "submitted"
        run.pause_reason = None
        run.submitted_at = now
        run.confirmation_number = result.confirmation_number
        run.submission_method = result.method
        run.attempts += 1
        run.updated_at = now
        database.commit()
        database.refresh(run)
        notify_run_event(
            database,
            settings,
            run,
            job,
            event="submitted",
            subject=f"Application submitted: {job.title}",
            body=(
                f"Your application for '{job.title}' was submitted "
                f"via the '{result.method}' channel."
                + (
                    f" Confirmation: {result.confirmation_number}."
                    if result.confirmation_number
                    else ""
                )
            ),
        )
        return run

    # Unsupported or failed: pause at the submission gate for the
    # candidate — identical to the manual-assist ending.
    if result.status == "failed":
        run.error = result.detail[:1000]
    run.pause_reason = "submission_confirmation"
    run.updated_at = now
    database.commit()
    database.refresh(run)
    notify_run_event(
        database,
        settings,
        run,
        job,
        event="action_required",
        subject=f"Ready to submit: {job.title}",
        body=(
            f"Your application for '{job.title}' is fully prepared. "
            f"{result.detail} Open CareerPilot for the prefilled "
            "details, submit, and record the confirmation number."
        ),
    )
    return run


def start_application_run(
    job_id: int,
    database: Session,
    candidate_profile_id: int,
    *,
    driver: str = "manual_assist",
    acknowledged_gates: list[str] | None = None,
    settings: Settings | None = None,
) -> ApplicationRun:
    if driver not in RUN_DRIVERS:
        raise ApplicationRunServiceError(
            "Unknown application driver.",
        )

    auto = driver == "auto_submit"
    acknowledged = set(acknowledged_gates or [])

    if auto and not AUTO_CONSENT_GATES.issubset(acknowledged):
        raise ApplicationRunServiceError(
            "Automatic application requires explicitly acknowledging "
            "the legal declarations and the irreversible submission.",
        )
    if acknowledged - AUTO_CONSENT_GATES:
        raise ApplicationRunServiceError(
            "Safety gates cannot be pre-acknowledged.",
        )

    job = get_job_or_404(job_id, database)
    profile = require_profile(database, candidate_profile_id)

    if auto:
        package = _ensure_package_ready(
            job,
            database,
            candidate_profile_id,
        )
    else:
        package = database.scalar(
            select(ApplicationPackage).where(
                ApplicationPackage.job_id == job.id
            )
        )
        if package is None:
            raise ApplicationRunServiceError(
                "Prepare the application package before applying.",
                status_code=409,
            )

    if package.readiness_status in REJECTED_READINESS:
        raise ApplicationRunServiceError(
            "This application cannot start while the package is "
            f"'{package.readiness_status}'. Resolve it and re-prepare "
            "first.",
            status_code=409,
        )

    if (
        package.readiness_status in CONFIRMATION_REQUIRED_READINESS
        and not package.user_confirmed
    ):
        if auto and package.readiness_status == (
            "ready_for_automatic_application"
        ):
            # The apply action itself is the explicit confirmation for
            # a package the system judged ready. 'needs_user_review'
            # is never skipped: the candidate must review it first.
            package.user_confirmed = True
            database.commit()
        else:
            raise ApplicationRunServiceError(
                "Confirm the application package before applying.",
                status_code=409,
            )

    existing = active_run_for_job(job.id, database)
    if existing is not None:
        return existing

    fill_plan, manual_fields = build_fill_plan_and_manual(
        profile,
        package,
        database,
        candidate_profile_id,
    )
    gates = build_gates(package)

    now = current_utc_time()
    if auto:
        # Recorded consent covers the legal-declaration review only;
        # safety gates and the actual submission are handled below.
        for gate in gates:
            if gate["code"] == "legal_declaration":
                gate["acknowledged"] = True

    current = first_unacknowledged_gate(gates)
    run = ApplicationRun(
        job_id=job.id,
        candidate_profile_id=profile.id,
        application_package_id=package.id,
        status="paused_for_gate",
        pause_reason=current["code"] if current else None,
        gates=gates,
        fill_plan=fill_plan,
        manual_fields=manual_fields,
        confirmation_number=None,
        submitted_at=None,
        consented_at=now if auto else None,
        submission_method=None,
        error=None,
        attempts=0,
        driver=driver,
        workflow_version=WORKFLOW_VERSION,
        created_at=now,
        updated_at=now,
    )
    database.add(run)
    database.commit()
    database.refresh(run)

    if auto:
        return _progress_auto_submit(
            run,
            job,
            package,
            database,
            settings,
        )
    return run


def get_run_or_404(
    run_id: int,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationRun:
    run = database.get(ApplicationRun, run_id)
    if run is None or run.candidate_profile_id != candidate_profile_id:
        raise ApplicationRunServiceError(
            "Application run was not found.",
            status_code=404,
        )
    return run


def resume_application_run(
    run_id: int,
    confirmation_number: str | None,
    database: Session,
    candidate_profile_id: int,
    *,
    settings: Settings | None = None,
) -> ApplicationRun:
    run = get_run_or_404(run_id, database, candidate_profile_id)

    if run.status in TERMINAL_STATUSES:
        raise ApplicationRunServiceError(
            f"This run is '{run.status}' and cannot be resumed.",
            status_code=409,
        )

    gates = [dict(gate) for gate in run.gates]
    current = first_unacknowledged_gate(gates)
    if current is None:
        raise ApplicationRunServiceError(
            "There is no pending step to resume.",
            status_code=409,
        )

    now = current_utc_time()

    if current["code"] == "submission_confirmation":
        if not confirmation_number:
            raise ApplicationRunServiceError(
                "Provide the confirmation number from the submission "
                "you completed. The tool never submits on your behalf.",
            )
        current["acknowledged"] = True
        run.gates = gates
        run.confirmation_number = confirmation_number
        run.submitted_at = now
        run.status = "submitted"
        run.submission_method = "manual"
        run.pause_reason = None
    else:
        current["acknowledged"] = True
        run.gates = gates
        nxt = first_unacknowledged_gate(gates)
        run.pause_reason = nxt["code"] if nxt else None
        run.status = "paused_for_gate"

    run.attempts += 1
    run.updated_at = now
    database.commit()
    database.refresh(run)

    if run.status == "submitted":
        job = database.get(NormalizedJob, run.job_id)
        if job is not None:
            notify_run_event(
                database,
                settings,
                run,
                job,
                event="submitted",
                subject=f"Application submitted: {job.title}",
                body=(
                    f"Your application for '{job.title}' was "
                    "submitted (recorded confirmation: "
                    f"{run.confirmation_number})."
                ),
            )
    return run


def cancel_application_run(
    run_id: int,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationRun:
    run = get_run_or_404(run_id, database, candidate_profile_id)

    if run.status in TERMINAL_STATUSES:
        raise ApplicationRunServiceError(
            f"This run is already '{run.status}'.",
            status_code=409,
        )

    run.status = "cancelled"
    run.pause_reason = None
    run.updated_at = current_utc_time()
    database.commit()
    database.refresh(run)
    return run
