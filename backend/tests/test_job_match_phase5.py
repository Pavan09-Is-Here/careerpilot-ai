from datetime import date
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.education import Education
from app.models.experience import Experience
from app.models.job import NormalizedJob
from app.models.job_match import JobMatch
from app.models.project import Project
from app.models.skill import Skill
from app.schemas.job import (
    JobLocationCreate,
    JobSkillRequirementCreate,
    JobSourceCreate,
    NormalizedJobCreate,
)
from app.services.job import create_job_source, create_normalized_job
from app.services.job_match import (
    ALGORITHM_VERSION,
    JobMatchServiceError,
    analyze_job_match,
    merge_experience_years,
)


PHASE45_HEAD = "e1f2a3b4c5d6"
PHASE5_HEAD = "f2a3b4c5d6e7"
TODAY = date(2026, 7, 2)


def content_hash(seed: str | None = None) -> str:
    return sha256((seed or uuid4().hex).encode()).hexdigest()


def make_profile(
    database: Session,
    **overrides: object,
) -> CandidateProfile:
    values: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "location": "London",
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
    profile = CandidateProfile(**values)
    database.add(profile)
    database.commit()
    database.refresh(profile)
    return profile


def add_skill(
    database: Session,
    profile: CandidateProfile,
    name: str,
    *,
    verified: bool = True,
) -> Skill:
    skill = Skill(
        candidate_profile_id=profile.id,
        name=name,
        proficiency="advanced",
        verified=verified,
    )
    database.add(skill)
    database.commit()
    return skill


def add_experience(
    database: Session,
    profile: CandidateProfile,
    start: date,
    end: date | None,
    *,
    verified: bool = True,
) -> Experience:
    experience = Experience(
        candidate_profile_id=profile.id,
        company="Example Corp",
        job_title="Engineer",
        start_date=start,
        end_date=end,
        is_current=end is None,
        responsibilities=[],
        achievements=[],
        technologies=[],
        verified=verified,
    )
    database.add(experience)
    database.commit()
    return experience


def add_education(
    database: Session,
    profile: CandidateProfile,
    degree: str,
    *,
    verified: bool = True,
) -> Education:
    education = Education(
        candidate_profile_id=profile.id,
        institution="Example University",
        degree=degree,
        start_date=date(2015, 9, 1),
        end_date=date(2018, 6, 30),
        is_current=False,
        verified=verified,
    )
    database.add(education)
    database.commit()
    return education


def add_project(
    database: Session,
    profile: CandidateProfile,
    technologies: list[str],
    *,
    verified: bool = True,
) -> Project:
    project = Project(
        candidate_profile_id=profile.id,
        name=f"Project {uuid4().hex[:6]}",
        description="A verified project.",
        technologies=technologies,
        features=[],
        achievements=[],
        verified=verified,
    )
    database.add(project)
    database.commit()
    return project


def make_job(
    database: Session,
    *,
    skills: list[tuple[str, str]] | None = None,
    locations: list[str] | None = None,
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
        "content_hash": content_hash(),
        "normalization_version": "phase5-test",
    }
    payload.update(overrides)
    return create_normalized_job(
        NormalizedJobCreate(**payload),
        database,
        locations=[
            JobLocationCreate(raw_location_text=text)
            for text in (locations or [])
        ],
        skill_requirements=[
            JobSkillRequirementCreate(
                skill_text=name,
                requirement_type=requirement_type,
            )
            for name, requirement_type in (skills or [])
        ],
    )


def analyze(
    database: Session,
    job: NormalizedJob,
) -> JobMatch:
    return analyze_job_match(job.id, database, today=TODAY)


def test_analyze_requires_job_and_profile(db_session: Session) -> None:
    with pytest.raises(JobMatchServiceError) as missing_job:
        analyze_job_match(987654, db_session)
    assert missing_job.value.status_code == 404

    job = make_job(db_session)
    with pytest.raises(JobMatchServiceError) as missing_profile:
        analyze_job_match(job.id, db_session)
    assert missing_profile.value.status_code == 404


def test_skills_component_scores_verified_matches(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_skill(db_session, profile, "Python")
    add_skill(db_session, profile, "Terraform", verified=False)
    job = make_job(
        db_session,
        skills=[("Python", "required"), ("Terraform", "required")],
    )

    match = analyze(db_session, job)

    assert match.skills_match == 50
    assert "Terraform" in match.explanation
    assert match.algorithm_version == ALGORITHM_VERSION


def test_preferred_skills_weigh_less_than_required(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_skill(db_session, profile, "Python")
    job = make_job(
        db_session,
        skills=[("Python", "required"), ("Go", "preferred")],
    )

    match = analyze(db_session, job)

    assert match.skills_match == 67


def test_missing_job_skills_leave_component_unscored(
    db_session: Session,
) -> None:
    make_profile(db_session)
    job = make_job(db_session)

    match = analyze(db_session, job)

    assert match.skills_match is None
    assert match.projects_match is None


def test_experience_component_uses_verified_years(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_experience(
        db_session,
        profile,
        date(2020, 7, 1),
        None,
    )
    job = make_job(
        db_session,
        required_qualifications_text=(
            "At least 3 years of backend engineering experience."
        ),
    )

    match = analyze(db_session, job)

    assert match.experience_match == 100


def test_experience_partial_score_when_below_requirement(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_experience(
        db_session,
        profile,
        date(2024, 7, 1),
        None,
    )
    job = make_job(
        db_session,
        required_qualifications_text="Requires 10+ years experience.",
    )

    match = analyze(db_session, job)

    assert match.experience_match == 20


def test_overlapping_experience_is_not_double_counted() -> None:
    class Interval:
        def __init__(self, start: date, end: date | None) -> None:
            self.start_date = start
            self.end_date = end

    years = merge_experience_years(
        [
            Interval(date(2020, 1, 1), date(2022, 1, 1)),
            Interval(date(2021, 1, 1), date(2023, 1, 1)),
        ],  # type: ignore[arg-type]
        date(2026, 7, 2),
    )

    assert 2.9 < years < 3.1


def test_education_meets_requirement(db_session: Session) -> None:
    profile = make_profile(db_session)
    add_education(db_session, profile, "BSc Computer Science")
    job = make_job(
        db_session,
        required_qualifications_text=(
            "Bachelor degree in a related field required."
        ),
    )

    match = analyze(db_session, job)

    assert match.education_match == 100


def test_education_below_requirement_scores_half(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_education(db_session, profile, "BSc Computer Science")
    job = make_job(
        db_session,
        required_qualifications_text="PhD required.",
    )

    match = analyze(db_session, job)

    assert match.education_match == 50


def test_missing_education_records_flag_review_not_zero(
    db_session: Session,
) -> None:
    make_profile(db_session)
    job = make_job(
        db_session,
        required_qualifications_text="Master degree required.",
    )

    match = analyze(db_session, job)

    assert match.education_match is None
    assert match.eligibility_status == "conditionally_eligible"
    assert match.blocker_reason is not None
    assert "education" in match.blocker_reason


def test_projects_component_covers_job_skills(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_project(db_session, profile, ["Python", "PostgreSQL"])
    job = make_job(
        db_session,
        skills=[("Python", "required"), ("Go", "required")],
    )

    match = analyze(db_session, job)

    assert match.projects_match == 50


def test_location_remote_preference_matches_remote_job(
    db_session: Session,
) -> None:
    make_profile(db_session)
    job = make_job(db_session, remote_mode="remote")

    match = analyze(db_session, job)

    assert match.location_match == 100


def test_location_no_match_without_relocation_scores_zero(
    db_session: Session,
) -> None:
    make_profile(
        db_session,
        preferred_work_modes=["onsite"],
        preferred_locations=["London"],
        location="London",
    )
    job = make_job(db_session, locations=["Tokyo, Japan"])

    match = analyze(db_session, job)

    assert match.location_match == 0


def test_location_relocation_willingness_scores_partial(
    db_session: Session,
) -> None:
    make_profile(
        db_session,
        willing_to_relocate=True,
        preferred_work_modes=["onsite"],
    )
    job = make_job(db_session, locations=["Tokyo, Japan"])

    match = analyze(db_session, job)

    assert match.location_match == 75
    assert match.eligibility_status == "conditionally_eligible"


def test_explicit_sponsorship_refusal_is_ineligible(
    db_session: Session,
) -> None:
    make_profile(
        db_session,
        requires_sponsorship=True,
        work_authorization="Requires visa sponsorship",
    )
    job = make_job(
        db_session,
        source_sponsorship_visa_text=(
            "We are unable to sponsor visas for this role."
        ),
        remote_mode="remote",
    )

    match = analyze(db_session, job)

    assert match.eligibility_status == "ineligible"
    assert match.work_auth_match == 0
    assert match.blocker_reason is not None
    assert "sponsorship" in match.blocker_reason


def test_sponsorship_offered_is_conditional_not_blocked(
    db_session: Session,
) -> None:
    make_profile(
        db_session,
        requires_sponsorship=True,
        work_authorization="Requires visa sponsorship",
    )
    job = make_job(
        db_session,
        source_sponsorship_visa_text="Visa sponsorship available.",
        remote_mode="remote",
    )

    match = analyze(db_session, job)

    assert match.eligibility_status == "conditionally_eligible"
    assert match.work_auth_match == 100


def test_unknown_sponsorship_policy_is_conditional(
    db_session: Session,
) -> None:
    make_profile(
        db_session,
        requires_sponsorship=True,
        work_authorization="Requires visa sponsorship",
    )
    job = make_job(db_session, remote_mode="remote")

    match = analyze(db_session, job)

    assert match.eligibility_status == "conditionally_eligible"
    assert match.work_auth_match == 50


def test_undeclared_work_authorization_flags_review(
    db_session: Session,
) -> None:
    make_profile(db_session, work_authorization=None)
    job = make_job(db_session, remote_mode="remote")

    match = analyze(db_session, job)

    assert match.work_auth_match is None
    assert match.eligibility_status == "conditionally_eligible"


def test_fully_clear_profile_is_eligible(db_session: Session) -> None:
    profile = make_profile(db_session)
    add_skill(db_session, profile, "Python")
    job = make_job(
        db_session,
        skills=[("Python", "required")],
        remote_mode="remote",
    )

    match = analyze(db_session, job)

    assert match.eligibility_status == "eligible"
    assert match.blocker_reason is None


def test_overall_score_renormalizes_missing_components(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_skill(db_session, profile, "Python")
    job = make_job(
        db_session,
        skills=[("Python", "required")],
        remote_mode="remote",
    )

    match = analyze(db_session, job)

    # skills=100 (w20), location=100 (w10), work_auth=100 (w10);
    # experience/education/projects unscored.
    assert match.match_score == 100


def test_unverified_records_are_excluded(db_session: Session) -> None:
    profile = make_profile(db_session)
    add_skill(db_session, profile, "Python", verified=False)
    job = make_job(
        db_session,
        skills=[("Python", "required")],
        remote_mode="remote",
    )

    match = analyze(db_session, job)

    assert match.skills_match == 0


def test_reanalysis_updates_existing_match(db_session: Session) -> None:
    profile = make_profile(db_session)
    job = make_job(
        db_session,
        skills=[("Python", "required")],
        remote_mode="remote",
    )
    first = analyze(db_session, job)
    assert first.skills_match == 0

    add_skill(db_session, profile, "Python")
    second = analyze(db_session, job)

    assert second.id == first.id
    assert second.skills_match == 100
    matches = list(db_session.scalars(select(JobMatch.id)).all())
    assert len(matches) == 1


def test_analysis_does_not_modify_candidate_facts(
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_skill(db_session, profile, "Python")
    job = make_job(db_session, skills=[("Python", "required")])
    before = {
        "skills": db_session.scalar(
            select(Skill.name).where(
                Skill.candidate_profile_id == profile.id
            )
        ),
        "profile_updated": profile.updated_at,
    }

    analyze(db_session, job)

    db_session.refresh(profile)
    assert before["profile_updated"] == profile.updated_at
    assert (
        db_session.scalar(
            select(Skill.name).where(
                Skill.candidate_profile_id == profile.id
            )
        )
        == before["skills"]
    )


def test_analyze_and_match_endpoints(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    add_skill(db_session, profile, "Python")
    job = make_job(
        db_session,
        skills=[("Python", "required")],
        remote_mode="remote",
    )

    missing = client.get(f"/api/jobs/{job.id}/match")
    assert missing.status_code == 404

    analyzed = client.post(f"/api/jobs/{job.id}/analyze")
    assert analyzed.status_code == 201
    body = analyzed.json()
    assert body["eligibility_status"] == "eligible"
    assert body["match_score"] == 100
    assert ALGORITHM_VERSION in body["algorithm_version"]
    assert "deterministic" in body["explanation"]

    fetched = client.get(f"/api/jobs/{job.id}/match")
    assert fetched.status_code == 200
    assert fetched.json()["id"] == body["id"]

    unknown = client.post("/api/jobs/987654/analyze")
    assert unknown.status_code == 404


def test_match_response_has_no_internal_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    job = make_job(db_session)
    response = client.post(f"/api/jobs/{job.id}/analyze")

    body = response.json()
    forbidden_fragments = ("secret", "credential", "storage", "path")
    for key in body:
        for fragment in forbidden_fragments:
            assert fragment not in key.lower()


def test_phase5_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "phase5-migration.db"

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")

    command.upgrade(config, PHASE5_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    assert "job_matches" in set(inspect(engine).get_table_names())
    engine.dispose()

    command.downgrade(config, PHASE45_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    tables = set(inspect(engine).get_table_names())
    assert "job_matches" not in tables
    assert "saved_jobs" in tables
    engine.dispose()

    command.upgrade(config, PHASE5_HEAD)
    engine = create_engine(f"sqlite:///{migration_db}")
    assert "job_matches" in set(inspect(engine).get_table_names())
    engine.dispose()
