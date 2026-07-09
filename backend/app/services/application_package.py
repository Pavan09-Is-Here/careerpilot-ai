"""Application preparation and package assembly (Phase 9).

Assembles a single reviewable application package per job from work
already produced by earlier phases: the verified match report
(Phase 5), the tailored CV (Phase 6), the salary recommendation
(Phase 7), and verified application answers (Phase 8). It adds a
deterministic, verified-fact-only cover letter and a readiness
assessment.

Safety-first by construction:
- No candidate information is fabricated. The cover letter is built
  only from the candidate's own verified summary, a verified company
  interest answer, and verified skills that the posting explicitly
  lists.
- Preparation never generates missing pieces (match, CV, answers);
  their absence is reported as missing information, never invented.
- A package is never marked ready when a safety blocker (CAPTCHA,
  MFA, assessment), a hard ineligibility, or missing required
  information is present. Confirmation and submission stay deliberate
  human actions.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application_answer import ApplicationAnswer
from app.models.application_package import ApplicationPackage
from app.models.candidate_profile import CandidateProfile
from app.models.cv_version import CVVersion
from app.models.cv_version_artifact import CVVersionArtifact
from app.models.job import JobSkillRequirement, NormalizedJob
from app.models.job_match import JobMatch
from app.models.job_tailored_cv import JobTailoredCV
from app.schemas.application_package import ApplicationPackageUpdate
from app.services.job_match import job_full_text, normalize_token
from app.services.salary import SalaryServiceError, recommend_salary


ASSEMBLY_VERSION = "application-package-1"

REQUIRED_ANSWER_CATEGORIES = (
    "work_authorization",
    "availability",
)
RECOMMENDED_ANSWER_CATEGORIES = (
    "sponsorship",
    "expected_salary",
    "relocation",
    "notice_period",
)

CAPTCHA_KEYWORDS = (
    "captcha",
    "recaptcha",
    "hcaptcha",
    "i am not a robot",
    "prove you are human",
    "prove you're human",
)
MFA_KEYWORDS = (
    "multi-factor",
    "multifactor",
    "two-factor",
    "two factor",
    "2fa",
    "one-time passcode",
    "one time passcode",
    "verification code",
    "authenticator app",
)
ASSESSMENT_KEYWORDS = (
    "coding assessment",
    "coding challenge",
    "coding test",
    "online assessment",
    "take-home",
    "take home assignment",
    "hackerrank",
    "codesignal",
    "codility",
    "skills assessment",
    "timed assessment",
    "aptitude test",
    "psychometric",
    "technical screen test",
)

# Highest precedence first.
BLOCKED_STATUS_BY_CODE = {
    "captcha": "blocked_by_captcha",
    "mfa": "blocked_by_mfa",
    "assessment": "blocked_by_assessment",
}


class ApplicationPackageServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


# --- Data gathering -------------------------------------------------------


def get_job_or_404(job_id: int, database: Session) -> NormalizedJob:
    job = database.get(NormalizedJob, job_id)
    if job is None:
        raise ApplicationPackageServiceError(
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
        raise ApplicationPackageServiceError(
            "Create the candidate profile before preparing "
            "applications.",
            status_code=404,
        )
    return profile


def load_job_match(
    job_id: int,
    database: Session,
    candidate_profile_id: int,
) -> JobMatch | None:
    return database.scalar(
        select(JobMatch).where(
            JobMatch.job_id == job_id,
            JobMatch.candidate_profile_id == candidate_profile_id,
        )
    )


def load_tailored_cv(
    job_id: int,
    database: Session,
    candidate_profile_id: int,
) -> tuple[CVVersion, list[CVVersionArtifact]] | None:
    link = database.scalar(
        select(JobTailoredCV)
        .join(
            CVVersion,
            JobTailoredCV.cv_version_id == CVVersion.id,
        )
        .where(
            JobTailoredCV.job_id == job_id,
            CVVersion.candidate_profile_id == candidate_profile_id,
        )
    )
    if link is None:
        return None

    version = database.get(CVVersion, link.cv_version_id)
    if version is None:
        return None

    artifacts = list(
        database.scalars(
            select(CVVersionArtifact)
            .where(CVVersionArtifact.cv_version_id == version.id)
            .order_by(CVVersionArtifact.artifact_type.asc())
        ).all()
    )
    return version, artifacts


def load_answers(
    database: Session,
    candidate_profile_id: int,
) -> list[ApplicationAnswer]:
    return list(
        database.scalars(
            select(ApplicationAnswer)
            .where(
                ApplicationAnswer.candidate_profile_id
                == candidate_profile_id
            )
            .order_by(
                ApplicationAnswer.category.asc(),
                ApplicationAnswer.id.asc(),
            )
        ).all()
    )


def matched_verified_skill_names(
    job: NormalizedJob,
    database: Session,
    candidate_profile_id: int,
) -> list[str]:
    """Verified skill names — of THIS candidate only — that the
    posting explicitly lists as structured skill requirements.
    Exact, deterministic overlap — no fuzzy analogies, no invented
    skills, never another profile's skills."""
    from app.models.skill import Skill

    job_skill_tokens = {
        normalize_token(requirement.skill_text)
        for requirement in database.scalars(
            select(JobSkillRequirement).where(
                JobSkillRequirement.job_id == job.id
            )
        ).all()
    }
    if not job_skill_tokens:
        return []

    names: list[str] = []
    seen: set[str] = set()
    for skill in database.scalars(
        select(Skill).where(
            Skill.verified.is_(True),
            Skill.candidate_profile_id == candidate_profile_id,
        )
    ).all():
        token = normalize_token(skill.name)
        if token in job_skill_tokens and token not in seen:
            seen.add(token)
            names.append(skill.name)
    return sorted(names, key=str.casefold)


# --- Cover letter (verified facts only) -----------------------------------


def verified_company_interest_answer(
    answers: list[ApplicationAnswer],
) -> ApplicationAnswer | None:
    for answer in answers:
        if answer.category == "company_interest" and answer.verified:
            return answer
    return None


def _current_role_phrase(
    database: Session,
    candidate_profile_id: int,
) -> str | None:
    """A short 'title at company' phrase from the most recent verified
    experience, used to open the letter. Verified facts only."""
    from app.models.experience import Experience

    experience = database.scalar(
        select(Experience)
        .where(
            Experience.candidate_profile_id == candidate_profile_id,
            Experience.verified.is_(True),
        )
        .order_by(
            Experience.is_current.desc(),
            Experience.start_date.desc(),
            Experience.id.desc(),
        )
    )
    if experience is None:
        return None

    title = normalize_token_display(experience.job_title)
    company = normalize_token_display(experience.company)
    if title and company:
        return f"{title} at {company}"
    return title or company


def normalize_token_display(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    return value.strip()


def build_cover_letter(
    profile: CandidateProfile,
    job: NormalizedJob,
    matched_skills: list[str],
    company_interest: ApplicationAnswer | None,
    *,
    database: Session | None = None,
    candidate_profile_id: int | None = None,
) -> str | None:
    """A structured, professional cover letter assembled strictly from
    verified content: a clear opening tied to the role, the candidate's
    verified summary and current role, a targeted skills paragraph, an
    optional company-interest paragraph, and a courteous close. Returns
    None when the profile is not verified. Nothing is invented — every
    sentence is built from fields the candidate has verified."""
    if not profile.facts_verified:
        return None

    role_phrase: str | None = None
    if database is not None and candidate_profile_id is not None:
        role_phrase = _current_role_phrase(
            database, candidate_profile_id
        )

    paragraphs: list[str] = [f"Dear {job.employer_name} Hiring Team,"]

    opening = (
        f"I am writing to apply for the {job.title} role at "
        f"{job.employer_name}."
    )
    if role_phrase:
        opening += (
            f" I currently work as {role_phrase}, and I believe my "
            "verified background is a strong match for what this "
            "position requires."
        )
    paragraphs.append(opening)

    summary = (profile.professional_summary or "").strip()
    if summary:
        paragraphs.append(summary)

    if matched_skills:
        names = ", ".join(matched_skills)
        if len(matched_skills) == 1:
            paragraphs.append(
                f"The role calls for {names}, which is one of my "
                "verified skills."
            )
        else:
            paragraphs.append(
                "This role's requirements line up directly with my "
                f"verified skills, including {names}."
            )

    if company_interest is not None:
        interest = company_interest.answer_text.strip()
        if interest:
            paragraphs.append(interest)

    paragraphs.append(
        "I would welcome the opportunity to discuss how I can "
        f"contribute to {job.employer_name}. Thank you for your "
        "time and consideration."
    )

    paragraphs.append("Sincerely,")
    paragraphs.append(profile.full_name)

    return "\n\n".join(paragraphs)


# --- Safety blockers ------------------------------------------------------


def detect_safety_blockers(
    job: NormalizedJob,
) -> list[dict[str, str]]:
    text = job_full_text(job)
    blockers: list[dict[str, str]] = []

    if any(keyword in text for keyword in CAPTCHA_KEYWORDS):
        blockers.append(
            {
                "code": "captcha",
                "detail": (
                    "The posting references a CAPTCHA or human "
                    "verification step. This must be completed "
                    "manually."
                ),
            }
        )
    if any(keyword in text for keyword in MFA_KEYWORDS):
        blockers.append(
            {
                "code": "mfa",
                "detail": (
                    "The posting references multi-factor or code-based "
                    "verification. This must be completed manually."
                ),
            }
        )
    if any(keyword in text for keyword in ASSESSMENT_KEYWORDS):
        blockers.append(
            {
                "code": "assessment",
                "detail": (
                    "The posting references a skills assessment or "
                    "test. This must be completed by the candidate."
                ),
            }
        )

    return blockers


# --- Readiness determination ----------------------------------------------


def determine_readiness(
    *,
    profile: CandidateProfile,
    job: NormalizedJob,
    match: JobMatch | None,
    tailored: tuple[CVVersion, list[CVVersionArtifact]] | None,
    answers: list[ApplicationAnswer],
    salary_basis: str,
    salary_below_minimum: bool,
    blockers: list[dict[str, str]],
) -> tuple[str, list[str], list[str]]:
    """Return (readiness_status, risk_warnings, missing_items).

    Deterministic precedence:
      not_eligible > captcha > mfa > assessment >
      missing_information > needs_user_review > ready.
    """
    missing: list[str] = []
    risks: list[str] = []

    if not profile.facts_verified:
        missing.append(
            "verified candidate profile (mark profile facts as "
            "verified)"
        )

    # Job lifecycle is advisory, never a hard block on its own.
    if job.lifecycle_status in {"expired", "removed", "unavailable"}:
        risks.append(
            "The job posting lifecycle status is "
            f"'{job.lifecycle_status}'; confirm the role is still "
            "open before applying."
        )
    elif job.lifecycle_status == "possibly_stale":
        risks.append(
            "The job posting may be stale; confirm the role is still "
            "open before applying."
        )

    # Match report.
    if match is None:
        missing.append("job match analysis (analyze the job first)")
    elif match.eligibility_status == "conditionally_eligible":
        risks.append(
            "The match is conditional: "
            + (match.blocker_reason or "manual review recommended.")
        )

    # Tailored CV with both artifacts, ready.
    if tailored is None:
        missing.append(
            "tailored CV (tailor the CV for this job first)"
        )
    else:
        version, artifacts = tailored
        artifact_types = {
            artifact.artifact_type for artifact in artifacts
        }
        if version.status != "ready" or not {
            "docx",
            "pdf",
        }.issubset(artifact_types):
            missing.append(
                "tailored CV DOCX and PDF artifacts (regenerate the "
                "tailored CV)"
            )

    # Required and recommended verified answers.
    verified_categories = {
        answer.category for answer in answers if answer.verified
    }
    for category in REQUIRED_ANSWER_CATEGORIES:
        if category not in verified_categories:
            missing.append(
                f"verified '{category}' application answer"
            )
    for category in RECOMMENDED_ANSWER_CATEGORIES:
        if category not in verified_categories:
            risks.append(
                f"No verified '{category}' answer is on file; add "
                "one if the application asks."
            )

    # Sensitive answers awaiting explicit confirmation.
    for answer in answers:
        if (
            answer.requires_manual_confirmation
            and not answer.manually_confirmed
        ):
            risks.append(
                f"The '{answer.category}' answer is sensitive or a "
                "legal declaration and needs manual confirmation "
                "before submission."
            )

    # Salary advisories (never hard blocks).
    if salary_basis == "insufficient_data":
        risks.append(
            "No advertised salary data is available; the salary "
            "answer is generic."
        )
    if salary_below_minimum:
        risks.append(
            "The advertised maximum is below your declared minimum "
            "salary (shown for your review only)."
        )

    # Precedence.
    if match is not None and match.eligibility_status == "ineligible":
        return "not_eligible", risks, missing

    blocker_codes = {blocker["code"] for blocker in blockers}
    for code in ("captcha", "mfa", "assessment"):
        if code in blocker_codes:
            return BLOCKED_STATUS_BY_CODE[code], risks, missing

    if missing:
        return "blocked_by_missing_information", risks, missing

    if risks:
        return "needs_user_review", risks, missing

    return "ready_for_automatic_application", risks, missing


# --- Assembly -------------------------------------------------------------


def prepare_application_package(
    job_id: int,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationPackage:
    job = get_job_or_404(job_id, database)
    profile = require_profile(database, candidate_profile_id)

    match = load_job_match(job.id, database, candidate_profile_id)
    tailored = load_tailored_cv(
        job.id,
        database,
        candidate_profile_id,
    )
    answers = load_answers(database, candidate_profile_id)

    try:
        salary = recommend_salary(
            job.id,
            database,
            candidate_profile_id=candidate_profile_id,
        )
    except SalaryServiceError as exc:
        raise ApplicationPackageServiceError(
            exc.safe_message,
            status_code=exc.status_code,
        ) from exc

    blockers = detect_safety_blockers(job)
    matched_skills = matched_verified_skill_names(
        job,
        database,
        candidate_profile_id,
    )
    company_interest = verified_company_interest_answer(answers)
    cover_letter = build_cover_letter(
        profile,
        job,
        matched_skills,
        company_interest,
        database=database,
        candidate_profile_id=candidate_profile_id,
    )

    readiness, risks, missing = determine_readiness(
        profile=profile,
        job=job,
        match=match,
        tailored=tailored,
        answers=answers,
        salary_basis=salary.basis,
        salary_below_minimum=salary.below_declared_minimum,
        blockers=blockers,
    )

    now = current_utc_time()
    package = database.scalar(
        select(ApplicationPackage).where(
            ApplicationPackage.job_id == job.id,
            ApplicationPackage.candidate_profile_id == profile.id,
        )
    )
    if package is None:
        package = ApplicationPackage(
            job_id=job.id,
            candidate_profile_id=profile.id,
            created_at=now,
        )
        database.add(package)

    package.readiness_status = readiness
    package.cover_letter_text = cover_letter
    package.blockers = blockers
    package.risk_warnings = risks
    package.missing_items = missing
    package.assembly_version = ASSEMBLY_VERSION
    package.prepared_at = now
    # Re-preparation invalidates any prior confirmation; user notes
    # are preserved.
    package.user_confirmed = False
    package.updated_at = now

    try:
        database.commit()
        database.refresh(package)
    except IntegrityError as exc:
        database.rollback()
        raise ApplicationPackageServiceError(
            "Application package could not be saved.",
            status_code=409,
        ) from exc

    return package


def get_package_or_404(
    job_id: int,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationPackage:
    package = database.scalar(
        select(ApplicationPackage).where(
            ApplicationPackage.job_id == job_id,
            ApplicationPackage.candidate_profile_id
            == candidate_profile_id,
        )
    )
    if package is None:
        raise ApplicationPackageServiceError(
            "No application package exists for this job. Prepare it "
            "first.",
            status_code=404,
        )
    return package


def update_application_package(
    job_id: int,
    data: ApplicationPackageUpdate,
    database: Session,
    candidate_profile_id: int,
) -> ApplicationPackage:
    package = get_package_or_404(
        job_id,
        database,
        candidate_profile_id,
    )

    if data.user_confirmed and package.readiness_status not in {
        "ready_for_automatic_application",
        "needs_user_review",
    }:
        raise ApplicationPackageServiceError(
            "This package cannot be confirmed while it is "
            f"'{package.readiness_status}'. Resolve blockers and "
            "re-prepare first.",
        )

    package.user_confirmed = data.user_confirmed
    package.user_notes = data.user_notes
    package.updated_at = current_utc_time()

    database.commit()
    database.refresh(package)
    return package


# --- Response composition -------------------------------------------------


def build_job_summary(job: NormalizedJob) -> dict[str, object]:
    return {
        "id": job.id,
        "title": job.title,
        "employer_name": job.employer_name,
        "source_url": job.source_url,
        "lifecycle_status": job.lifecycle_status,
        "remote_mode": job.remote_mode,
        "employment_type": job.employment_type,
    }


def build_match_summary(match: JobMatch | None) -> dict[str, object] | None:
    if match is None:
        return None
    return {
        "match_score": match.match_score,
        "eligibility_status": match.eligibility_status,
        "blocker_reason": match.blocker_reason,
    }


def build_cv_summary(
    tailored: tuple[CVVersion, list[CVVersionArtifact]] | None,
) -> dict[str, object] | None:
    if tailored is None:
        return None
    version, artifacts = tailored
    return {
        "cv_version_id": version.id,
        "status": version.status,
        "artifacts": [
            {
                "artifact_type": artifact.artifact_type,
                "safe_filename": artifact.safe_filename,
                "file_size": artifact.file_size,
                "page_count": artifact.page_count,
            }
            for artifact in artifacts
        ],
    }


def build_answer_summaries(
    answers: list[ApplicationAnswer],
) -> list[dict[str, object]]:
    return [
        {
            "id": answer.id,
            "category": answer.category,
            "question_label": answer.question_label,
            "verified": answer.verified,
            "requires_manual_confirmation": (
                answer.requires_manual_confirmation
            ),
            "manually_confirmed": answer.manually_confirmed,
        }
        for answer in answers
    ]


def build_salary_summary(
    job_id: int,
    database: Session,
    candidate_profile_id: int,
) -> dict[str, object] | None:
    try:
        salary = recommend_salary(
            job_id,
            database,
            candidate_profile_id=candidate_profile_id,
        )
    except SalaryServiceError:
        return None
    return {
        "currency": salary.currency,
        "minimum": salary.minimum,
        "maximum": salary.maximum,
        "midpoint": salary.midpoint,
        "confidence": salary.confidence,
        "basis": salary.basis,
        "safe_answer": salary.safe_answer,
        "below_declared_minimum": salary.below_declared_minimum,
    }


def build_package_response(
    package: ApplicationPackage,
    database: Session,
    candidate_profile_id: int,
) -> dict[str, object]:
    job = get_job_or_404(package.job_id, database)
    match = load_job_match(job.id, database, candidate_profile_id)
    tailored = load_tailored_cv(
        job.id,
        database,
        candidate_profile_id,
    )
    answers = load_answers(database, candidate_profile_id)

    return {
        "job_id": package.job_id,
        "readiness_status": package.readiness_status,
        "prepared_at": package.prepared_at,
        "assembly_version": package.assembly_version,
        "user_confirmed": package.user_confirmed,
        "user_notes": package.user_notes,
        "cover_letter_text": package.cover_letter_text,
        "blockers": list(package.blockers),
        "risk_warnings": list(package.risk_warnings),
        "missing_items": list(package.missing_items),
        "job": build_job_summary(job),
        "match": build_match_summary(match),
        "tailored_cv": build_cv_summary(tailored),
        "verified_answers": build_answer_summaries(answers),
        "salary": build_salary_summary(
            job.id,
            database,
            candidate_profile_id,
        ),
    }
