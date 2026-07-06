"""Deterministic job matching and eligibility (Phase 5).

Rule-based, versioned, and fully explainable. Only verified vault
records count as confirmed evidence. Components without enough data
score None and are excluded from the weighted overall score —
missing data is flagged for manual review, never counted against
the candidate. Ineligibility requires an explicit contradiction
between a candidate declaration and explicit job text.
"""

from datetime import date, datetime, timezone
import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.education import Education
from app.models.experience import Experience
from app.models.job import (
    JobLocation,
    JobSkillRequirement,
    NormalizedJob,
)
from app.models.job_match import JobMatch
from app.models.project import Project
from app.models.skill import Skill


ALGORITHM_VERSION = "match-algorithm-1"
COMPONENT_WEIGHTS = {
    "skills_match": 20,
    "experience_match": 30,
    "education_match": 15,
    "projects_match": 15,
    "location_match": 10,
    "work_auth_match": 10,
}
YEARS_RE = re.compile(r"(\d{1,2})\s*\+?\s*years?", re.IGNORECASE)
MAX_REQUIRED_YEARS = 20
EDUCATION_TIERS = (
    ("phd", 3),
    ("doctorate", 3),
    ("doctoral", 3),
    ("master", 2),
    ("msc", 2),
    ("mba", 2),
    ("bachelor", 1),
    ("bsc", 1),
    ("undergraduate", 1),
    ("degree", 1),
)
NEGATIVE_SPONSORSHIP_PHRASES = (
    "no sponsorship",
    "not sponsor",
    "cannot sponsor",
    "can't sponsor",
    "unable to sponsor",
    "without sponsorship",
    "sponsorship is not available",
    "sponsorship not available",
    "no visa sponsorship",
)
POSITIVE_SPONSORSHIP_PHRASES = (
    "sponsorship available",
    "sponsorship is available",
    "will sponsor",
    "visa sponsorship offered",
    "we sponsor",
    "provides sponsorship",
    "provide visa sponsorship",
)
MAX_EXPLANATION_CHARS = 8000


class JobMatchServiceError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.safe_message = message
        self.status_code = status_code


def current_utc_time() -> datetime:
    return datetime.now(timezone.utc)


def normalize_token(value: str) -> str:
    return value.strip().casefold()


def job_full_text(job: NormalizedJob) -> str:
    parts = [
        job.description_text,
        job.responsibilities_text,
        job.required_qualifications_text,
        job.preferred_qualifications_text,
    ]
    return "\n".join(part for part in parts if part).casefold()


class ComponentResult:
    def __init__(
        self,
        score: int | None,
        lines: list[str],
        review_reasons: list[str] | None = None,
    ) -> None:
        self.score = score
        self.lines = lines
        self.review_reasons = review_reasons or []


def score_skills(
    verified_skills: list[Skill],
    job_skills: list[JobSkillRequirement],
) -> ComponentResult:
    if not job_skills:
        return ComponentResult(
            None,
            [
                "Skills: the job posting lists no structured skill "
                "requirements; component not scored.",
            ],
        )

    skill_names = {
        normalize_token(skill.name) for skill in verified_skills
    }
    total_weight = 0.0
    matched_weight = 0.0
    matched: list[str] = []
    missing: list[str] = []

    for requirement in job_skills:
        weight = (
            1.0
            if requirement.requirement_type == "required"
            else 0.5
        )
        total_weight += weight
        if normalize_token(requirement.skill_text) in skill_names:
            matched_weight += weight
            matched.append(requirement.skill_text)
        else:
            missing.append(requirement.skill_text)

    score = round(100 * matched_weight / total_weight)
    lines = [
        (
            "Skills: matched "
            f"{len(matched)} of {len(job_skills)} listed skill "
            f"requirements against verified skills "
            f"(score {score})."
        ),
    ]
    if matched:
        lines.append(f"Skills matched: {', '.join(sorted(matched))}.")
    if missing:
        lines.append(
            "Skills not found in the verified vault: "
            f"{', '.join(sorted(missing))}."
        )
    return ComponentResult(score, lines)


def merge_experience_years(
    experiences: list[Experience],
    today: date,
) -> float:
    intervals = sorted(
        (
            experience.start_date,
            experience.end_date or today,
        )
        for experience in experiences
    )
    total_days = 0
    current_start: date | None = None
    current_end: date | None = None

    for start, end in intervals:
        if end < start:
            continue
        if current_start is None or current_end is None:
            current_start, current_end = start, end
            continue
        if start <= current_end:
            if end > current_end:
                current_end = end
            continue
        total_days += (current_end - current_start).days
        current_start, current_end = start, end

    if current_start is not None and current_end is not None:
        total_days += (current_end - current_start).days

    return total_days / 365.25


def extract_required_years(job: NormalizedJob) -> int | None:
    sources = [
        job.required_qualifications_text,
        job.description_text,
    ]
    found: list[int] = []
    for text in sources:
        if not text:
            continue
        found.extend(
            int(match) for match in YEARS_RE.findall(text)
        )

    valid = [
        years for years in found if 0 < years <= MAX_REQUIRED_YEARS
    ]
    if not valid:
        return None
    return max(valid)


def score_experience(
    verified_experiences: list[Experience],
    job: NormalizedJob,
    today: date,
) -> ComponentResult:
    required_years = extract_required_years(job)
    if required_years is None:
        return ComponentResult(
            None,
            [
                "Experience: no explicit years-of-experience "
                "requirement found in the posting; component not "
                "scored.",
            ],
        )

    if not verified_experiences:
        return ComponentResult(
            None,
            [
                (
                    "Experience: the posting asks for "
                    f"{required_years}+ years but the vault has no "
                    "verified experience records; flagged for "
                    "manual review."
                ),
            ],
            review_reasons=[
                "verified work experience records are missing",
            ],
        )

    candidate_years = merge_experience_years(
        verified_experiences,
        today,
    )
    score = min(
        100,
        round(100 * candidate_years / required_years),
    )
    return ComponentResult(
        score,
        [
            (
                "Experience: "
                f"{candidate_years:.1f} verified years against a "
                f"stated {required_years}+ year requirement "
                f"(score {score})."
            ),
        ],
    )


def education_tier(text: str) -> int:
    lowered = text.casefold()
    best = 0
    for keyword, tier in EDUCATION_TIERS:
        if keyword in lowered and tier > best:
            best = tier
    return best


def score_education(
    verified_education: list[Education],
    job: NormalizedJob,
) -> ComponentResult:
    requirement_text = " ".join(
        part
        for part in (
            job.required_qualifications_text,
            job.preferred_qualifications_text,
        )
        if part
    )
    required_tier = (
        education_tier(requirement_text) if requirement_text else 0
    )
    if required_tier == 0:
        return ComponentResult(
            None,
            [
                "Education: no explicit degree requirement found in "
                "the posting; component not scored.",
            ],
        )

    if not verified_education:
        return ComponentResult(
            None,
            [
                "Education: the posting states a degree requirement "
                "but the vault has no verified education records; "
                "flagged for manual review.",
            ],
            review_reasons=[
                "verified education records are missing",
            ],
        )

    candidate_tier = max(
        education_tier(
            f"{record.degree} {record.field_of_study or ''}"
        )
        for record in verified_education
    )
    if candidate_tier >= required_tier:
        return ComponentResult(
            100,
            [
                "Education: verified education meets or exceeds the "
                "stated degree requirement (score 100).",
            ],
        )

    return ComponentResult(
        50,
        [
            "Education: verified education is below the stated "
            "degree requirement (score 50); review recommended.",
        ],
    )


def score_projects(
    verified_projects: list[Project],
    job_skills: list[JobSkillRequirement],
) -> ComponentResult:
    if not job_skills:
        return ComponentResult(
            None,
            [
                "Projects: the job posting lists no structured skill "
                "requirements to compare projects against; component "
                "not scored.",
            ],
        )

    if not verified_projects:
        return ComponentResult(
            None,
            [
                "Projects: the vault has no verified projects; "
                "component not scored.",
            ],
        )

    job_skill_tokens = {
        normalize_token(skill.skill_text) for skill in job_skills
    }
    covered: set[str] = set()
    matching_projects: list[str] = []

    for project in verified_projects:
        technologies = {
            normalize_token(technology)
            for technology in project.technologies
        }
        overlap = technologies & job_skill_tokens
        if overlap:
            covered |= overlap
            matching_projects.append(project.name)

    score = round(100 * len(covered) / len(job_skill_tokens))
    lines = [
        (
            "Projects: verified projects cover "
            f"{len(covered)} of {len(job_skill_tokens)} listed "
            f"skill requirements (score {score})."
        ),
    ]
    if matching_projects:
        lines.append(
            "Relevant projects: "
            f"{', '.join(sorted(matching_projects))}."
        )
    return ComponentResult(score, lines)


def score_location(
    profile: CandidateProfile,
    job: NormalizedJob,
    job_locations: list[JobLocation],
) -> ComponentResult:
    preferred_modes = {
        normalize_token(mode)
        for mode in profile.preferred_work_modes
    }
    if job.remote_mode == "remote" and "remote" in preferred_modes:
        return ComponentResult(
            100,
            [
                "Location: the job is remote and remote work is a "
                "stated preference (score 100).",
            ],
        )

    location_texts = [
        location.raw_location_text
        for location in job_locations
        if location.raw_location_text
    ]
    candidate_places = [
        normalize_token(place)
        for place in (
            *profile.preferred_locations,
            *( [profile.location] if profile.location else [] ),
        )
        if place
    ]

    if not location_texts:
        return ComponentResult(
            None,
            [
                "Location: the posting provides no structured "
                "location data; component not scored.",
            ],
        )

    if not candidate_places and not preferred_modes:
        return ComponentResult(
            None,
            [
                "Location: the profile lists no location or work "
                "mode preferences; component not scored.",
            ],
        )

    for text in location_texts:
        lowered = text.casefold()
        for place in candidate_places:
            if place and place in lowered:
                return ComponentResult(
                    100,
                    [
                        (
                            "Location: job location "
                            f"'{text}' matches a stated candidate "
                            "location (score 100)."
                        ),
                    ],
                )

    if profile.willing_to_relocate:
        return ComponentResult(
            75,
            [
                "Location: no direct location match, but the "
                "candidate is willing to relocate (score 75).",
            ],
            review_reasons=["relocation would be required"],
        )

    return ComponentResult(
        0,
        [
            "Location: no location match and the candidate has not "
            "declared willingness to relocate (score 0).",
        ],
    )


def score_work_authorization(
    profile: CandidateProfile,
    job: NormalizedJob,
) -> tuple[ComponentResult, str | None]:
    """Returns (component, hard_blocker_reason_or_None)."""
    if profile.work_authorization is None:
        return (
            ComponentResult(
                None,
                [
                    "Work authorization: not declared in the "
                    "profile; component not scored and flagged for "
                    "manual review.",
                ],
                review_reasons=[
                    "work authorization is not declared",
                ],
            ),
            None,
        )

    sponsorship_text = (
        job.source_sponsorship_visa_text or ""
    ).casefold()

    if not profile.requires_sponsorship:
        return (
            ComponentResult(
                100,
                [
                    "Work authorization: the candidate declares no "
                    "sponsorship requirement (score 100).",
                ],
            ),
            None,
        )

    if any(
        phrase in sponsorship_text
        for phrase in NEGATIVE_SPONSORSHIP_PHRASES
    ):
        return (
            ComponentResult(
                0,
                [
                    "Work authorization: the candidate requires "
                    "sponsorship and the posting explicitly states "
                    "sponsorship is not offered (score 0).",
                ],
            ),
            (
                "The candidate requires sponsorship and the posting "
                "explicitly states sponsorship is not offered."
            ),
        )

    if any(
        phrase in sponsorship_text
        for phrase in POSITIVE_SPONSORSHIP_PHRASES
    ):
        return (
            ComponentResult(
                100,
                [
                    "Work authorization: sponsorship is required and "
                    "the posting states sponsorship is available "
                    "(score 100).",
                ],
                review_reasons=[
                    "sponsorship is required and offered; confirm "
                    "details",
                ],
            ),
            None,
        )

    return (
        ComponentResult(
            50,
            [
                "Work authorization: sponsorship is required and "
                "the posting does not state a sponsorship policy "
                "(score 50); flagged for manual review.",
            ],
            review_reasons=[
                "sponsorship policy of the employer is unknown",
            ],
        ),
        None,
    )


def compute_overall_score(
    components: dict[str, ComponentResult],
) -> int | None:
    weighted_sum = 0.0
    weight_total = 0.0

    for name, component in components.items():
        if component.score is None:
            continue
        weight = COMPONENT_WEIGHTS[name]
        weighted_sum += component.score * weight
        weight_total += weight

    if weight_total == 0:
        return None
    return round(weighted_sum / weight_total)


def analyze_job_match(
    job_id: int,
    database: Session,
    *,
    candidate_profile_id: int,
    today: date | None = None,
) -> JobMatch:
    job = database.get(NormalizedJob, job_id)
    if job is None:
        raise JobMatchServiceError(
            "Job was not found.",
            status_code=404,
        )

    profile = database.get(CandidateProfile, candidate_profile_id)
    if profile is None:
        raise JobMatchServiceError(
            "Candidate profile was not found.",
            status_code=404,
        )

    evaluation_date = today or current_utc_time().date()

    # Only THIS candidate's verified facts may inform the match.
    verified_skills = list(
        database.scalars(
            select(Skill).where(
                Skill.verified.is_(True),
                Skill.candidate_profile_id == profile.id,
            )
        ).all()
    )
    verified_experiences = list(
        database.scalars(
            select(Experience).where(
                Experience.verified.is_(True),
                Experience.candidate_profile_id == profile.id,
            )
        ).all()
    )
    verified_education = list(
        database.scalars(
            select(Education).where(
                Education.verified.is_(True),
                Education.candidate_profile_id == profile.id,
            )
        ).all()
    )
    verified_projects = list(
        database.scalars(
            select(Project).where(
                Project.verified.is_(True),
                Project.candidate_profile_id == profile.id,
            )
        ).all()
    )
    job_skills = list(
        database.scalars(
            select(JobSkillRequirement).where(
                JobSkillRequirement.job_id == job.id
            )
        ).all()
    )
    job_locations = list(
        database.scalars(
            select(JobLocation).where(JobLocation.job_id == job.id)
        ).all()
    )

    work_auth_component, hard_blocker = score_work_authorization(
        profile,
        job,
    )
    components = {
        "skills_match": score_skills(verified_skills, job_skills),
        "experience_match": score_experience(
            verified_experiences,
            job,
            evaluation_date,
        ),
        "education_match": score_education(verified_education, job),
        "projects_match": score_projects(
            verified_projects,
            job_skills,
        ),
        "location_match": score_location(
            profile,
            job,
            job_locations,
        ),
        "work_auth_match": work_auth_component,
    }

    review_reasons: list[str] = []
    for component in components.values():
        review_reasons.extend(component.review_reasons)

    if hard_blocker is not None:
        eligibility_status = "ineligible"
        blocker_reason: str | None = hard_blocker
    elif review_reasons:
        eligibility_status = "conditionally_eligible"
        blocker_reason = "Manual review required: " + "; ".join(
            review_reasons
        )
    else:
        eligibility_status = "eligible"
        blocker_reason = None

    explanation_lines = [
        f"Algorithm {ALGORITHM_VERSION}: deterministic, rule-based "
        "scoring over verified vault records only. Components "
        "without enough data are excluded from the weighted score, "
        "never counted against the candidate.",
    ]
    for component in components.values():
        explanation_lines.extend(component.lines)
    explanation = "\n".join(explanation_lines)[:MAX_EXPLANATION_CHARS]

    now = current_utc_time()
    match = database.scalar(
        select(JobMatch).where(
            JobMatch.job_id == job.id,
            JobMatch.candidate_profile_id == profile.id,
        )
    )
    if match is None:
        match = JobMatch(
            job_id=job.id,
            candidate_profile_id=profile.id,
            created_at=now,
        )
        database.add(match)

    match.match_score = compute_overall_score(components)
    match.skills_match = components["skills_match"].score
    match.experience_match = components["experience_match"].score
    match.education_match = components["education_match"].score
    match.projects_match = components["projects_match"].score
    match.location_match = components["location_match"].score
    match.work_auth_match = components["work_auth_match"].score
    match.eligibility_status = eligibility_status
    match.blocker_reason = blocker_reason
    match.explanation = explanation
    match.algorithm_version = ALGORITHM_VERSION
    match.updated_at = now

    try:
        database.commit()
        database.refresh(match)
    except IntegrityError as exc:
        database.rollback()
        raise JobMatchServiceError(
            "Job match could not be saved.",
            status_code=409,
        ) from exc

    return match


def get_job_match_or_404(
    job_id: int,
    database: Session,
    *,
    candidate_profile_id: int,
) -> JobMatch:
    match = database.scalar(
        select(JobMatch).where(
            JobMatch.job_id == job_id,
            JobMatch.candidate_profile_id == candidate_profile_id,
        )
    )
    if match is None:
        raise JobMatchServiceError(
            "Job match was not found. Analyze the job first.",
            status_code=404,
        )
    return match
