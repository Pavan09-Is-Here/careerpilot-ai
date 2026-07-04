"""Tests for CV -> candidate-detail extraction and autofill.

Everything extracted from a CV is unverified and, for sensitive or
dated data, routed to manual review — never invented, never verified.
A profile row must exist before a document can be uploaded (documents
FK to the profile), so this feature fills an existing profile.
"""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.certification import Certification
from app.models.document import Document
from app.models.education import Education
from app.models.experience import Experience
from app.models.project import Project
from app.models.skill import Skill
from tests.conftest import Account


CV_TEXT = """Jane Doe
Senior Software Engineer
London, UK
jane.doe@example.com
+44 20 7946 0000
linkedin.com/in/janedoe
github.com/janedoe

SUMMARY
Experienced backend engineer focused on Python and distributed systems.

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes

WORK EXPERIENCE
Acme Corp - Senior Engineer (2020 - Present)
Built scalable services.

EDUCATION
BSc Computer Science, Example University (2015 - 2018)
"""


# A richer CV that exercises every structured category, including
# entries that are intentionally missing required fields so they must
# fall back to manual review instead of being fabricated into records.
RICH_CV_TEXT = """Alex Rivers
Backend Engineer
alex.rivers@example.com

SUMMARY
Backend engineer.

SKILLS
Python, Go

WORK EXPERIENCE
Globex Ltd - Backend Engineer (Jun 2019 - Dec 2022)
Owned the billing service.
Improved throughput.

Freelance work here and there

EDUCATION
MSc Distributed Systems, North University (2017 - 2019)

Some study, no dates and no institution

PROJECTS
Ledger Engine
A double-entry accounting engine for internal billing.
Technologies: Python, PostgreSQL

Nameless idea

CERTIFICATIONS
AWS Certified Solutions Architect - Amazon Web Services (2021)

Random course with no issuer 2020
"""


@pytest.fixture(autouse=True)
def _reset_login_rate_limiter() -> None:
    from app.api.routes.auth import login_rate_limiter

    login_rate_limiter.reset()


def seed_profile(
    database: Session,
    account: Account,
    **overrides: object,
) -> CandidateProfile:
    """Reset the authenticated account's own profile to a known baseline.

    Registration already creates the caller's profile, so instead of
    inserting a second row we mutate the existing one into the placeholder
    state these tests rely on.
    """
    values: dict[str, object] = {
        "full_name": "",
        "email": "",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": [],
        "target_roles": [],
        "preferred_locations": [],
        "salary_currency": "GBP",
        "minimum_match_score": 50,
        "auto_apply_enabled": False,
        "facts_verified": False,
    }
    values.update(overrides)
    profile = database.get(CandidateProfile, account.profile_id)
    assert profile is not None
    for key, value in values.items():
        setattr(profile, key, value)
    database.commit()
    database.refresh(profile)
    return profile


def make_document(
    database: Session,
    account: Account,
    *,
    extracted_text: str | None = CV_TEXT,
    extraction_status: str = "completed",
) -> Document:
    token = uuid4().hex
    document = Document(
        candidate_profile_id=account.profile_id,
        original_filename=f"cv-{token}.pdf",
        stored_filename=f"{token}.pdf",
        file_extension=".pdf",
        media_type="application/pdf",
        size_bytes=256,
        sha256_hash=sha256(token.encode()).hexdigest(),
        document_type="original_cv",
        upload_status="validated",
        is_primary=True,
        extraction_status=extraction_status,
        extracted_text=extracted_text,
        extracted_at=datetime.now(timezone.utc),
        page_count=1,
        extracted_character_count=len(extracted_text or ""),
    )
    database.add(document)
    database.commit()
    database.refresh(document)
    return document


# --- Preview --------------------------------------------------------------


def test_profile_suggestion_preview(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(db_session, account)

    response = client.get(
        f"/api/documents/{document.id}/profile-suggestion",
        headers=account.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is False

    fields = {f["field"]: f for f in body["fields"]}
    assert fields["full_name"]["value"] == "Jane Doe"
    assert fields["email"]["value"] == "jane.doe@example.com"
    assert "engineer" in fields["professional_title"]["value"].lower()
    assert "Python" in fields["professional_summary"]["value"]
    assert "linkedin.com" in fields["linkedin_url"]["value"]
    assert "github.com" in fields["github_url"]["value"]

    # Sensitive personal fields are flagged for manual review.
    assert fields["phone"]["sensitive"] is True
    assert fields["phone"]["auto_fill"] is False
    assert fields["location"]["sensitive"] is True
    assert fields["full_name"]["auto_fill"] is True

    skill_names = {s["name"] for s in body["skills"]}
    assert {"Python", "FastAPI", "PostgreSQL"}.issubset(skill_names)

    # The clean single-entry education/experience now parse into
    # structured drafts rather than a raw manual-review dump.
    assert len(body["education"]) == 1
    assert body["education"][0]["institution"] == "Example University"
    assert body["education"][0]["degree"] == "BSc Computer Science"
    assert body["education"][0]["start_date"] == "2015-01-01"
    assert len(body["experience"]) == 1
    assert body["experience"][0]["company"] == "Acme Corp"
    assert body["experience"][0]["job_title"] == "Senior Engineer"
    assert body["experience"][0]["is_current"] is True


def test_preview_requires_extracted_text(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(
        db_session,
        account,
        extraction_status="pending",
        extracted_text=None,
    )
    response = client.get(
        f"/api/documents/{document.id}/profile-suggestion",
        headers=account.headers,
    )
    assert response.status_code == 400


def test_preview_requires_authentication(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(db_session, account)

    response = client.get(
        f"/api/documents/{document.id}/profile-suggestion"
    )
    assert response.status_code == 401


# --- Apply ----------------------------------------------------------------


def test_apply_fills_placeholder_profile_unverified(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(db_session, account)

    response = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
        headers=account.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["verified"] is False
    assert "full_name" in body["applied_fields"]
    assert "email" in body["applied_fields"]
    assert "professional_summary" in body["applied_fields"]
    assert len(body["added_skills"]) >= 4
    assert any(item.get("field") == "phone" for item in body["manual_review"])

    db_session.expire_all()
    profile = db_session.get(CandidateProfile, account.profile_id)
    assert profile.full_name == "Jane Doe"
    assert profile.email == "jane.doe@example.com"
    assert profile.facts_verified is False  # never auto-verified
    assert profile.phone is None  # sensitive -> not auto-filled
    assert profile.professional_summary is not None

    skills = db_session.query(Skill).all()
    assert len(skills) >= 4
    assert all(skill.verified is False for skill in skills)


def test_apply_skips_existing_then_overwrites(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(
        db_session,
        account,
        full_name="Existing Name",
        email="existing@example.com",
        facts_verified=True,
    )
    document = make_document(db_session, account)

    first = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
        headers=account.headers,
    ).json()
    assert "full_name" in first["skipped_existing_fields"]
    assert "professional_title" in first["applied_fields"]

    db_session.expire_all()
    profile = db_session.get(CandidateProfile, account.profile_id)
    assert profile.full_name == "Existing Name"
    # Introducing unverified CV data resets verification.
    assert profile.facts_verified is False

    client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={"overwrite": True},
        headers=account.headers,
    )
    db_session.expire_all()
    assert (
        db_session.get(CandidateProfile, account.profile_id).full_name
        == "Jane Doe"
    )


def test_apply_include_sensitive(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(db_session, account)

    client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={"include_sensitive": True},
        headers=account.headers,
    )
    db_session.expire_all()
    profile = db_session.get(CandidateProfile, account.profile_id)
    assert profile.phone is not None
    assert profile.location is not None


def test_apply_dedupes_existing_skills(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    db_session.add(
        Skill(
            candidate_profile_id=account.profile_id,
            name="Python",
            proficiency="Advanced",
            verified=True,
        )
    )
    db_session.commit()
    document = make_document(db_session, account)

    body = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
        headers=account.headers,
    ).json()
    assert "Python" not in body["added_skills"]

    db_session.expire_all()
    pythons = (
        db_session.query(Skill).filter(Skill.name == "Python").all()
    )
    assert len(pythons) == 1  # not duplicated


def test_apply_skills_only_when_no_profile_fields(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(
        db_session,
        account,
        full_name="Set Name",
        email="set@example.com",
    )
    document = make_document(
        db_session,
        account,
        extracted_text="SKILLS\nPython, Docker\n",
    )
    body = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
        headers=account.headers,
    ).json()
    assert set(body["added_skills"]) == {"Python", "Docker"}


# --- Structured history extraction ---------------------------------------


def test_structured_preview_extracts_all_categories(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(
        db_session, account, extracted_text=RICH_CV_TEXT
    )

    body = client.get(
        f"/api/documents/{document.id}/profile-suggestion",
        headers=account.headers,
    ).json()

    edu = body["education"]
    assert len(edu) == 1
    assert edu[0]["degree"] == "MSc Distributed Systems"
    assert edu[0]["institution"] == "North University"
    assert edu[0]["start_date"] == "2017-01-01"
    assert edu[0]["end_date"] == "2019-12-31"

    exp = body["experience"]
    assert len(exp) == 1
    assert exp[0]["company"] == "Globex Ltd"
    assert exp[0]["job_title"] == "Backend Engineer"
    assert exp[0]["start_date"] == "2019-06-01"
    assert exp[0]["end_date"] == "2022-12-01"
    assert exp[0]["is_current"] is False

    projects = body["projects"]
    assert len(projects) == 1
    assert projects[0]["name"] == "Ledger Engine"
    assert "accounting engine" in projects[0]["description"]
    assert "Python" in projects[0]["technologies"]

    certs = body["certifications"]
    assert len(certs) == 1
    assert certs[0]["name"] == "AWS Certified Solutions Architect"
    assert certs[0]["issuing_organization"] == "Amazon Web Services"
    assert certs[0]["issue_date"] == "2021-01-01"

    # Every structured entry carries an evidence snippet.
    for section in ("education", "experience", "projects", "certifications"):
        for entry in body[section]:
            assert entry["evidence"]


def test_incomplete_entries_fall_back_to_manual_review(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    """Entries missing required fields are never fabricated into records."""
    seed_profile(db_session, account)
    document = make_document(
        db_session, account, extracted_text=RICH_CV_TEXT
    )

    body = client.get(
        f"/api/documents/{document.id}/profile-suggestion",
        headers=account.headers,
    ).json()

    manual = {m["category"]: m for m in body["manual_review"]}
    # The junk entries in each section are surfaced for manual review.
    assert "education" in manual
    assert "Some study" in manual["education"]["content"]
    assert "work_experience" in manual
    assert "Freelance" in manual["work_experience"]["content"]
    assert "projects" in manual
    assert "Nameless idea" in manual["projects"]["content"]
    assert "certifications" in manual
    assert "Random course" in manual["certifications"]["content"]


def test_apply_creates_unverified_structured_records(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(
        db_session, account, extracted_text=RICH_CV_TEXT
    )

    body = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
        headers=account.headers,
    ).json()

    assert len(body["added_education"]) == 1
    assert len(body["added_experience"]) == 1
    assert len(body["added_projects"]) == 1
    assert len(body["added_certifications"]) == 1

    db_session.expire_all()

    educations = (
        db_session.query(Education)
        .filter(Education.candidate_profile_id == account.profile_id)
        .all()
    )
    assert len(educations) == 1
    assert educations[0].institution == "North University"
    assert educations[0].degree == "MSc Distributed Systems"
    assert educations[0].verified is False

    experiences = (
        db_session.query(Experience)
        .filter(Experience.candidate_profile_id == account.profile_id)
        .all()
    )
    assert len(experiences) == 1
    assert experiences[0].company == "Globex Ltd"
    assert experiences[0].verified is False

    projects = (
        db_session.query(Project)
        .filter(Project.candidate_profile_id == account.profile_id)
        .all()
    )
    assert len(projects) == 1
    assert projects[0].name == "Ledger Engine"
    assert projects[0].description
    assert projects[0].verified is False

    certs = (
        db_session.query(Certification)
        .filter(Certification.candidate_profile_id == account.profile_id)
        .all()
    )
    assert len(certs) == 1
    assert certs[0].issuing_organization == "Amazon Web Services"
    assert certs[0].verified is False

    # Introducing unverified structured drafts resets verification.
    profile = db_session.get(CandidateProfile, account.profile_id)
    assert profile.facts_verified is False


def test_apply_opt_out_flags_skip_categories(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(
        db_session, account, extracted_text=RICH_CV_TEXT
    )

    body = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={
            "apply_education": False,
            "apply_experience": False,
            "apply_projects": False,
            "apply_certifications": False,
        },
        headers=account.headers,
    ).json()

    assert body["added_education"] == []
    assert body["added_experience"] == []
    assert body["added_projects"] == []
    assert body["added_certifications"] == []

    db_session.expire_all()
    assert db_session.query(Education).count() == 0
    assert db_session.query(Experience).count() == 0
    assert db_session.query(Project).count() == 0
    assert db_session.query(Certification).count() == 0


def test_apply_dedupes_structured_records(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    seed_profile(db_session, account)
    document = make_document(
        db_session, account, extracted_text=RICH_CV_TEXT
    )

    first = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
        headers=account.headers,
    ).json()
    assert len(first["added_education"]) == 1

    second = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
        headers=account.headers,
    ).json()
    assert second["added_education"] == []
    assert second["added_experience"] == []
    assert second["added_projects"] == []
    assert second["added_certifications"] == []

    db_session.expire_all()
    assert db_session.query(Education).count() == 1
    assert db_session.query(Experience).count() == 1
    assert db_session.query(Project).count() == 1
    assert db_session.query(Certification).count() == 1


def test_no_fabrication_when_history_absent(
    client: TestClient,
    db_session: Session,
    account: Account,
) -> None:
    """A CV with no dated history creates no structured records."""
    seed_profile(db_session, account)
    document = make_document(
        db_session,
        account,
        extracted_text=(
            "Sam Vector\n"
            "Engineer\n"
            "sam.vector@example.com\n\n"
            "SKILLS\nPython, Rust\n"
        ),
    )

    body = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
        headers=account.headers,
    ).json()

    assert body["added_education"] == []
    assert body["added_experience"] == []
    assert body["added_projects"] == []
    assert body["added_certifications"] == []

    db_session.expire_all()
    assert db_session.query(Education).count() == 0
    assert db_session.query(Experience).count() == 0
    assert db_session.query(Project).count() == 0
    assert db_session.query(Certification).count() == 0
