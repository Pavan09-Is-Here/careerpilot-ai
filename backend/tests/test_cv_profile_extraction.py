"""Tests for CV -> candidate-detail extraction and autofill.

Everything extracted from a CV is unverified and, for sensitive or
dated data, routed to manual review — never invented, never verified.
A profile row must exist before a document can be uploaded (documents
FK to the profile), so this feature fills an existing profile.
"""

from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.document import Document
from app.models.skill import Skill


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


def seed_profile(database: Session, **overrides: object) -> CandidateProfile:
    values: dict[str, object] = {
        "id": 1,
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
    profile = CandidateProfile(**values)
    database.add(profile)
    database.commit()
    database.refresh(profile)
    return profile


def make_document(
    database: Session,
    *,
    extracted_text: str | None = CV_TEXT,
    extraction_status: str = "completed",
) -> Document:
    token = uuid4().hex
    document = Document(
        candidate_profile_id=1,
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
) -> None:
    seed_profile(db_session)
    document = make_document(db_session)

    response = client.get(
        f"/api/documents/{document.id}/profile-suggestion"
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

    manual_categories = {m["category"] for m in body["manual_review"]}
    assert "education" in manual_categories
    assert "work_experience" in manual_categories


def test_preview_requires_extracted_text(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)
    document = make_document(
        db_session,
        extraction_status="pending",
        extracted_text=None,
    )
    response = client.get(
        f"/api/documents/{document.id}/profile-suggestion"
    )
    assert response.status_code == 400


# --- Apply ----------------------------------------------------------------


def test_apply_fills_placeholder_profile_unverified(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)
    document = make_document(db_session)

    response = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
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
    profile = db_session.get(CandidateProfile, 1)
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
) -> None:
    seed_profile(
        db_session,
        full_name="Existing Name",
        email="existing@example.com",
        facts_verified=True,
    )
    document = make_document(db_session)

    first = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
    ).json()
    assert "full_name" in first["skipped_existing_fields"]
    assert "professional_title" in first["applied_fields"]

    db_session.expire_all()
    profile = db_session.get(CandidateProfile, 1)
    assert profile.full_name == "Existing Name"
    # Introducing unverified CV data resets verification.
    assert profile.facts_verified is False

    client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={"overwrite": True},
    )
    db_session.expire_all()
    assert db_session.get(CandidateProfile, 1).full_name == "Jane Doe"


def test_apply_include_sensitive(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)
    document = make_document(db_session)

    client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={"include_sensitive": True},
    )
    db_session.expire_all()
    profile = db_session.get(CandidateProfile, 1)
    assert profile.phone is not None
    assert profile.location is not None


def test_apply_dedupes_existing_skills(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_profile(db_session)
    db_session.add(
        Skill(
            candidate_profile_id=1,
            name="Python",
            proficiency="Advanced",
            verified=True,
        )
    )
    db_session.commit()
    document = make_document(db_session)

    body = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
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
) -> None:
    seed_profile(db_session, full_name="Set Name", email="set@example.com")
    document = make_document(
        db_session,
        extracted_text="SKILLS\nPython, Docker\n",
    )
    body = client.post(
        f"/api/documents/{document.id}/apply-profile-suggestion",
        json={},
    ).json()
    assert set(body["added_skills"]) == {"Python", "Docker"}
