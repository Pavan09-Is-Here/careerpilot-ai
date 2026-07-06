"""Job-specific CV tailoring (Phase 6).

Deterministic tailoring over verified facts only. Tailoring may
reorder, select, and emphasize verified records — it never invents
experience, skills, dates, employers, metrics, or claims. The
professional summary is the candidate's own verbatim summary plus
one deterministic sentence listing verified skills that match the
job; nothing else is written.
"""

from datetime import date, datetime, timezone
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.cv_version import CVVersion
from app.models.experience import Experience
from app.models.job import JobSkillRequirement, NormalizedJob
from app.models.job_tailored_cv import JobTailoredCV
from app.models.project import Project
from app.models.skill import Skill
from app.schemas.cv_version import CVMasterGenerationRequest
from app.services.cv_version import CVVersionServiceError
from app.services.job_match import job_full_text, normalize_token
from app.services.verified_master_cv import (
    DEFAULT_CANDIDATE_PROFILE_ID,
    GENERATION_VERSION,
    GeneratedMasterCVResult,
    StoredGeneratedArtifact,
    build_master_cv_document,
    cleanup_stored_artifacts,
    list_cv_version_artifacts,
    mark_generation_failed,
    persist_generated_artifacts,
    preflight_pdf_text,
    render_docx,
    render_pdf,
    require_verified_candidate_profile,
    safe_download_filename,
    select_verified_records,
    validate_generation_parent,
    write_generated_artifact,
)


TAILORING_VERSION = "cv-tailoring-1"
MAX_SELECTED_EXPERIENCES = 5
MIN_SELECTED_EXPERIENCES = 3
MAX_SELECTED_PROJECTS = 5


class CVTailoringError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def extract_job_keywords(
    job: NormalizedJob,
    job_skills: list[JobSkillRequirement],
    verified_skills: list[Skill],
) -> set[str]:
    """Deterministic keyword set: structured job skills plus the
    candidate's verified skill names that literally appear in the
    posting text."""
    keywords = {
        normalize_token(requirement.skill_text)
        for requirement in job_skills
    }

    text = job_full_text(job)
    for skill in verified_skills:
        token = normalize_token(skill.name)
        if not token:
            continue
        pattern = r"(?<![a-z0-9])" + re.escape(token) + r"(?![a-z0-9])"
        if re.search(pattern, text):
            keywords.add(token)

    return keywords


def technology_tokens(values: list[str]) -> set[str]:
    return {
        normalize_token(value) for value in values if value.strip()
    }


def recency_key(record: Experience | Project) -> tuple[int, int]:
    end = getattr(record, "end_date", None)
    start = getattr(record, "start_date", None)
    end_ordinal = (end or date.max).toordinal()
    start_ordinal = (start or date.min).toordinal()
    return (end_ordinal, start_ordinal)


def select_relevant_experiences(
    experiences: list[Experience],
    keywords: set[str],
) -> tuple[list[Experience], list[str]]:
    scored = sorted(
        experiences,
        key=lambda record: (
            -len(technology_tokens(record.technologies) & keywords),
            tuple(-value for value in recency_key(record)),
        ),
    )
    relevant = [
        record
        for record in scored
        if technology_tokens(record.technologies) & keywords
    ][:MAX_SELECTED_EXPERIENCES]

    if len(relevant) < min(MIN_SELECTED_EXPERIENCES, len(experiences)):
        remaining = sorted(
            (
                record
                for record in experiences
                if record not in relevant
            ),
            key=lambda record: tuple(
                -value for value in recency_key(record)
            ),
        )
        needed = (
            min(MIN_SELECTED_EXPERIENCES, len(experiences))
            - len(relevant)
        )
        relevant.extend(remaining[:needed])

    notes = [
        (
            "Experience selection: "
            f"{len(relevant)} of {len(experiences)} verified "
            "experiences selected by technology overlap with job "
            "keywords; facts unchanged."
        ),
    ]
    return relevant, notes


def select_relevant_projects(
    projects: list[Project],
    keywords: set[str],
) -> list[Project]:
    scored = sorted(
        projects,
        key=lambda record: (
            -len(technology_tokens(record.technologies) & keywords),
            tuple(-value for value in recency_key(record)),
        ),
    )
    relevant = [
        record
        for record in scored
        if technology_tokens(record.technologies) & keywords
    ][:MAX_SELECTED_PROJECTS]

    if relevant:
        return relevant
    return scored[:MAX_SELECTED_PROJECTS]


def reorder_skills(
    skills: list[Skill],
    keywords: set[str],
) -> list[Skill]:
    matching = [
        skill
        for skill in skills
        if normalize_token(skill.name) in keywords
    ]
    others = [
        skill
        for skill in skills
        if normalize_token(skill.name) not in keywords
    ]
    return matching + others


def tailored_profile_copy(
    profile: CandidateProfile,
    matching_skills: list[Skill],
) -> CandidateProfile:
    """Transient copy with a deterministic, fact-only summary line.

    The original summary is kept verbatim; the only addition names
    verified skills that match the job. Never added to the session.
    """
    summary = (profile.professional_summary or "").strip()
    if matching_skills:
        names = ", ".join(
            sorted(
                {skill.name for skill in matching_skills},
                key=str.casefold,
            )
        )
        emphasis = (
            f"Verified skills relevant to this role: {names}."
        )
        summary = f"{summary} {emphasis}".strip()

    copy = CandidateProfile(
        full_name=profile.full_name,
        email=profile.email,
        phone=profile.phone,
        location=profile.location,
        professional_title=profile.professional_title,
        professional_summary=summary or None,
        linkedin_url=profile.linkedin_url,
        github_url=profile.github_url,
        portfolio_url=profile.portfolio_url,
    )
    copy.id = profile.id
    return copy


def find_parent_master_version(
    database: Session,
    candidate_profile_id: int,
) -> CVVersion:
    parent = database.scalars(
        select(CVVersion)
        .where(
            CVVersion.candidate_profile_id == candidate_profile_id,
            CVVersion.version_type == "verified_master",
            CVVersion.status == "ready",
        )
        .order_by(
            CVVersion.is_primary.desc(),
            CVVersion.id.desc(),
        )
    ).first()

    if parent is None:
        raise CVTailoringError(
            "Generate a verified master CV before tailoring.",
            status_code=400,
        )

    validate_generation_parent(parent)
    return parent


def scoped_generation_key(job_id: int, idempotency_key: str) -> str:
    return f"job{job_id}:{idempotency_key}"[:128]


def find_existing_tailored_generation(
    database: Session,
    *,
    candidate_profile_id: int,
    parent_version_id: int,
    generation_key: str,
) -> CVVersion | None:
    return database.scalars(
        select(CVVersion)
        .where(
            CVVersion.candidate_profile_id == candidate_profile_id,
            CVVersion.parent_version_id == parent_version_id,
            CVVersion.version_type == "tailored",
            CVVersion.generation_key == generation_key,
        )
        .order_by(CVVersion.id.desc())
    ).first()


def create_draft_tailored_version(
    database: Session,
    *,
    profile: CandidateProfile,
    parent: CVVersion,
    job: NormalizedJob,
    request: CVMasterGenerationRequest,
    source_summary: dict[str, int],
) -> CVVersion:
    now = current_utc_time()
    job_reference = (
        f"{job.employer_name} — {job.title} (#{job.id})"[:250]
    )
    version = CVVersion(
        candidate_profile_id=profile.id,
        source_document_id=None,
        parent_version_id=parent.id,
        version_type="tailored",
        status="draft",
        display_name=(
            request.display_name
            or f"{profile.full_name} CV — {job.title}"[:250]
        ),
        description=request.description,
        job_reference=job_reference,
        is_primary=False,
        storage_path=None,
        mime_type=None,
        file_size=None,
        sha256=None,
        generation_key=scoped_generation_key(
            job.id,
            request.idempotency_key,
        ),
        generation_version=f"{GENERATION_VERSION}+{TAILORING_VERSION}",
        source_summary=source_summary,
        generated_at=None,
        created_at=now,
        updated_at=now,
        archived_at=None,
    )

    try:
        database.add(version)
        database.commit()
        database.refresh(version)
    except Exception as exc:
        database.rollback()
        raise CVTailoringError(
            "Failed to create tailored CV version.",
            status_code=500,
        ) from exc

    return version


def link_tailored_cv(
    database: Session,
    job: NormalizedJob,
    version: CVVersion,
) -> None:
    now = current_utc_time()
    # One tailored CV per (job, candidate profile): scope the lookup
    # by the version owner so one candidate's regeneration can never
    # replace another candidate's link.
    link = database.scalar(
        select(JobTailoredCV)
        .join(
            CVVersion,
            JobTailoredCV.cv_version_id == CVVersion.id,
        )
        .where(
            JobTailoredCV.job_id == job.id,
            CVVersion.candidate_profile_id
            == version.candidate_profile_id,
        )
    )
    if link is None:
        link = JobTailoredCV(
            job_id=job.id,
            candidate_profile_id=version.candidate_profile_id,
            cv_version_id=version.id,
            created_at=now,
            updated_at=now,
        )
        database.add(link)
    else:
        link.cv_version_id = version.id
        link.candidate_profile_id = version.candidate_profile_id
        link.updated_at = now

    try:
        database.commit()
    except IntegrityError as exc:
        database.rollback()
        raise CVTailoringError(
            "Failed to link the tailored CV to the job.",
            status_code=409,
        ) from exc


def generate_tailored_cv(
    job_id: int,
    request: CVMasterGenerationRequest,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> GeneratedMasterCVResult:
    job = database.get(NormalizedJob, job_id)
    if job is None:
        raise CVTailoringError("Job was not found.", status_code=404)

    try:
        profile = require_verified_candidate_profile(
            database,
            candidate_profile_id,
        )
    except CVVersionServiceError as exc:
        raise CVTailoringError(
            exc.safe_message,
            status_code=exc.status_code,
        ) from exc

    parent = find_parent_master_version(
        database,
        candidate_profile_id,
    )

    stored_key = scoped_generation_key(
        job.id,
        request.idempotency_key,
    )
    existing = find_existing_tailored_generation(
        database,
        candidate_profile_id=candidate_profile_id,
        parent_version_id=parent.id,
        generation_key=stored_key,
    )
    if existing is not None:
        return GeneratedMasterCVResult(
            version=existing,
            artifacts=list_cv_version_artifacts(
                existing.id,
                database,
                candidate_profile_id=candidate_profile_id,
            ),
            created=False,
        )

    (
        education_records,
        experiences,
        projects,
        skills,
        certifications,
    ) = select_verified_records(database, candidate_profile_id)

    job_skills = list(
        database.scalars(
            select(JobSkillRequirement).where(
                JobSkillRequirement.job_id == job.id
            )
        ).all()
    )
    keywords = extract_job_keywords(job, job_skills, skills)

    selected_experiences, _ = select_relevant_experiences(
        experiences,
        keywords,
    )
    selected_projects = select_relevant_projects(projects, keywords)
    ordered_skills = reorder_skills(skills, keywords)
    matching_skills = [
        skill
        for skill in skills
        if normalize_token(skill.name) in keywords
    ]
    presentation_profile = tailored_profile_copy(
        profile,
        matching_skills,
    )

    try:
        document_data = build_master_cv_document(
            presentation_profile,
            education_records=education_records,
            experiences=selected_experiences,
            projects=selected_projects,
            skills=ordered_skills,
            certifications=certifications,
        )
    except CVVersionServiceError as exc:
        raise CVTailoringError(
            exc.safe_message,
            status_code=exc.status_code,
        ) from exc

    version = create_draft_tailored_version(
        database,
        profile=profile,
        parent=parent,
        job=job,
        request=request,
        source_summary=document_data.source_summary,
    )
    stored: list[StoredGeneratedArtifact] = []

    try:
        preflight_pdf_text(document_data)
        stored.append(
            write_generated_artifact(
                "docx",
                safe_download_filename(
                    profile.full_name,
                    version.id,
                    "docx",
                ),
                lambda path: render_docx(document_data, path),
            )
        )
        stored.append(
            write_generated_artifact(
                "pdf",
                safe_download_filename(
                    profile.full_name,
                    version.id,
                    "pdf",
                ),
                lambda path: render_pdf(document_data, path),
            )
        )
    except CVVersionServiceError as exc:
        cleanup_stored_artifacts(stored)
        mark_generation_failed(version.id, database)
        raise CVTailoringError(
            exc.safe_message,
            status_code=exc.status_code,
        ) from exc
    except Exception as exc:
        cleanup_stored_artifacts(stored)
        mark_generation_failed(version.id, database)
        raise CVTailoringError(
            "Failed to generate tailored CV artifacts.",
            status_code=500,
        ) from exc

    try:
        artifacts = persist_generated_artifacts(
            version,
            stored,
            database,
            request=request,
            profile=profile,
        )
    except CVVersionServiceError as exc:
        raise CVTailoringError(
            exc.safe_message,
            status_code=exc.status_code,
        ) from exc

    link_tailored_cv(database, job, version)

    return GeneratedMasterCVResult(
        version=version,
        artifacts=artifacts,
        created=True,
    )


def get_tailored_cv_or_404(
    job_id: int,
    database: Session,
    *,
    candidate_profile_id: int = DEFAULT_CANDIDATE_PROFILE_ID,
) -> GeneratedMasterCVResult:
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
        raise CVTailoringError(
            "No tailored CV exists for this job. Tailor it first.",
            status_code=404,
        )

    version = database.get(CVVersion, link.cv_version_id)
    if (
        version is None
        or version.candidate_profile_id != candidate_profile_id
    ):
        raise CVTailoringError(
            "Tailored CV version was not found.",
            status_code=404,
        )

    return GeneratedMasterCVResult(
        version=version,
        artifacts=list_cv_version_artifacts(
            version.id,
            database,
            candidate_profile_id=candidate_profile_id,
        ),
        created=False,
    )
