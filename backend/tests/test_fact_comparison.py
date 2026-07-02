from datetime import date, datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api.routes import document as document_route
from app.models.candidate_profile import CandidateProfile
from app.models.certification import Certification
from app.models.cv_section import CVSection
from app.models.document import Document
from app.models.education import Education
from app.models.experience import Experience
from app.models.fact_comparison import (
    FactComparisonFinding,
    FactComparisonRun,
)
from app.models.project import Project
from app.models.skill import Skill


PREVIOUS_HEAD = "c4e7d9a1b2c3"
NEW_HEAD = "e5f6a7b8c9d0"
CURRENT_HEAD = "d6e7f8a9b0c1"


def profile_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "phone": "5550101234",
        "location": "New York, NY",
        "professional_title": "Backend Engineer",
        "professional_summary": "Verified backend engineer.",
        "linkedin_url": "https://www.linkedin.com/in/test-candidate/",
        "github_url": "https://github.com/testcandidate",
        "portfolio_url": "https://portfolio.example.com",
        "work_authorization": "Right to work confirmed",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": ["Remote"],
        "target_roles": ["Backend Engineer"],
        "preferred_locations": ["New York"],
        "minimum_salary": 50000,
        "salary_currency": "USD",
        "minimum_match_score": 85,
        "auto_apply_enabled": False,
        "facts_verified": True,
    }
    payload.update(overrides)
    return payload


def create_profile(
    client: TestClient,
    **overrides: object,
) -> dict[str, Any]:
    response = client.put("/api/profile", json=profile_payload(**overrides))
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def create_ready_document(
    database: Session,
    sections: list[tuple[str, str, str]],
    *,
    extraction_status: str = "completed",
    section_detection_status: str = "completed",
) -> Document:
    extracted_text = "\n\n".join(content for _, _, content in sections)
    digest = sha256(f"{extracted_text}-{uuid4().hex}".encode()).hexdigest()
    document = Document(
        candidate_profile_id=1,
        original_filename="synthetic-resume.pdf",
        stored_filename=f"{uuid4().hex}.pdf",
        file_extension=".pdf",
        media_type="application/pdf",
        size_bytes=len(extracted_text),
        sha256_hash=digest,
        document_type="original_cv",
        upload_status="validated",
        is_primary=False,
        extraction_status=extraction_status,
        extracted_text=extracted_text if extraction_status == "completed" else None,
        extraction_error=None,
        extracted_at=datetime.now(timezone.utc),
        page_count=1,
        extracted_character_count=len(extracted_text),
        section_detection_status=section_detection_status,
        section_detection_error=None,
        section_detected_at=datetime.now(timezone.utc),
        section_count=len(sections) if section_detection_status == "completed" else 0,
        section_detection_method="deterministic_section_detection_v1",
    )
    database.add(document)
    database.flush()

    cursor = 0
    for index, (section_type, title, content) in enumerate(sections):
        start = extracted_text.find(content, cursor)
        if start < 0:
            start = cursor
        end = start + len(content)
        cursor = end
        database.add(
            CVSection(
                document_id=document.id,
                section_order=index,
                section_type=section_type,
                title=title,
                start_char=start,
                end_char=end,
                content_text=content,
                confidence=0.9,
                detection_method="deterministic_section_detection_v1",
                created_at=datetime.now(timezone.utc),
            )
        )

    database.commit()
    database.refresh(document)
    return document


def add_education(
    database: Session,
    **overrides: object,
) -> Education:
    payload: dict[str, object] = {
        "candidate_profile_id": 1,
        "institution": "Example University",
        "degree": "BSc Computer Science",
        "field_of_study": "Computer Science",
        "start_date": date(2018, 9, 1),
        "end_date": date(2021, 6, 1),
        "grade": "First Class",
        "location": "New York",
        "description": None,
        "is_current": False,
        "verified": True,
    }
    payload.update(overrides)
    record = Education(**payload)
    database.add(record)
    database.commit()
    database.refresh(record)
    return record


def add_experience(
    database: Session,
    **overrides: object,
) -> Experience:
    payload: dict[str, object] = {
        "candidate_profile_id": 1,
        "company": "Example Ltd",
        "job_title": "Software Engineer",
        "employment_type": "Full-time",
        "location": "New York",
        "start_date": date(2020, 1, 1),
        "end_date": date(2022, 6, 1),
        "is_current": False,
        "description": None,
        "responsibilities": [],
        "achievements": [],
        "technologies": [],
        "verified": True,
    }
    payload.update(overrides)
    record = Experience(**payload)
    database.add(record)
    database.commit()
    database.refresh(record)
    return record


def add_project(
    database: Session,
    **overrides: object,
) -> Project:
    payload: dict[str, object] = {
        "candidate_profile_id": 1,
        "name": "CareerPilot",
        "role": "Developer",
        "project_type": "Web App",
        "description": "Synthetic verified project.",
        "start_date": date(2023, 1, 1),
        "end_date": date(2023, 6, 1),
        "is_current": False,
        "project_url": "https://example.com/careerpilot",
        "github_url": "https://github.com/example/careerpilot",
        "technologies": ["Python", "FastAPI"],
        "features": [],
        "achievements": [],
        "verified": True,
    }
    payload.update(overrides)
    record = Project(**payload)
    database.add(record)
    database.commit()
    database.refresh(record)
    return record


def add_skill(
    database: Session,
    **overrides: object,
) -> Skill:
    payload: dict[str, object] = {
        "candidate_profile_id": 1,
        "name": "Python",
        "category": "Programming Language",
        "proficiency": "Advanced",
        "years_experience": 3.0,
        "evidence": "Used in verified projects.",
        "is_primary": True,
        "verified": True,
    }
    payload.update(overrides)
    record = Skill(**payload)
    database.add(record)
    database.commit()
    database.refresh(record)
    return record


def add_certification(
    database: Session,
    **overrides: object,
) -> Certification:
    payload: dict[str, object] = {
        "candidate_profile_id": 1,
        "name": "Cloud Practitioner",
        "issuing_organization": "Example Cloud",
        "credential_id": "ABC-123",
        "credential_url": "https://example.com/credential/abc-123",
        "issue_date": date(2024, 1, 1),
        "expiry_date": None,
        "does_not_expire": True,
        "description": None,
        "skills": [],
        "verified": True,
    }
    payload.update(overrides)
    record = Certification(**payload)
    database.add(record)
    database.commit()
    database.refresh(record)
    return record


def compare_document(
    client: TestClient,
    document_id: int,
) -> dict[str, Any]:
    response = client.post(f"/api/documents/{document_id}/compare-facts")
    assert response.status_code == 200
    return cast(dict[str, Any], response.json())


def finding_exists(
    payload: dict[str, Any],
    *,
    entity_type: str,
    finding_type: str,
    field_name: str | None = None,
) -> bool:
    for finding in payload["findings"]:
        if finding["entity_type"] != entity_type:
            continue
        if finding["finding_type"] != finding_type:
            continue
        if field_name is not None and finding["field_name"] != field_name:
            continue
        return True

    return False


def matching_findings(
    payload: dict[str, Any],
    *,
    entity_type: str,
    finding_type: str | None = None,
    field_name: str | None = None,
    cv_value: str | None = None,
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []

    for finding in payload["findings"]:
        if finding["entity_type"] != entity_type:
            continue
        if finding_type is not None and finding["finding_type"] != finding_type:
            continue
        if field_name is not None and finding["field_name"] != field_name:
            continue
        if cv_value is not None and finding["cv_value"] != cv_value:
            continue

        matches.append(cast(dict[str, Any], finding))

    return matches


def test_profile_facts_and_harmless_formatting_are_confirmed(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    document = create_ready_document(
        db_session,
        [
            (
                "contact",
                "Contact",
                (
                    "Test Candidate\n"
                    "Backend Engineer\n"
                    "candidate@example.com\n"
                    "555-010-1234\n"
                    "New York, NY\n"
                    "linkedin.com/in/test-candidate\n"
                    "github.com/testcandidate\n"
                    "portfolio.example.com"
                ),
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert payload["status"] == "completed"
    assert finding_exists(
        payload,
        entity_type="candidate_profile",
        finding_type="confirmed",
        field_name="full_name",
    )
    assert finding_exists(
        payload,
        entity_type="candidate_profile",
        finding_type="confirmed",
        field_name="phone",
    )
    assert finding_exists(
        payload,
        entity_type="candidate_profile",
        finding_type="confirmed",
        field_name="linkedin_url",
    )


def test_profile_mismatch_detection_requires_manual_review(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    document = create_ready_document(
        db_session,
        [
            (
                "contact",
                "Contact",
                "Different Candidate\nwrong@example.com\nNew York, NY",
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert finding_exists(
        payload,
        entity_type="candidate_profile",
        finding_type="possible_mismatch",
        field_name="email",
    )
    assert payload["manual_review_count"] >= 1


def test_education_match_and_date_conflict(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_education(db_session)
    document = create_ready_document(
        db_session,
        [
            (
                "education",
                "Education",
                (
                    "Example University, BSc Computer Science\n"
                    "Computer Science, First Class\n"
                    "2019 - 2022"
                ),
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert finding_exists(
        payload,
        entity_type="education",
        finding_type="confirmed",
        field_name="institution",
    )
    assert finding_exists(
        payload,
        entity_type="education",
        finding_type="date_conflict",
        field_name="dates",
    )


def test_work_experience_org_variant_and_date_conflict(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_experience(db_session)
    document = create_ready_document(
        db_session,
        [
            (
                "work_experience",
                "Work Experience",
                (
                    "Example Limited - Software Engineer\n"
                    "Full-time, New York\n"
                    "2020 - 2023"
                ),
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="confirmed",
        field_name="company",
    )
    assert finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="date_conflict",
        field_name="dates",
    )


def test_verified_work_descriptions_do_not_become_unverified_claims(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_experience(
        db_session,
        responsibilities=[
            "Built reliable APIs at scale",
            "Processed 2023 customer records",
        ],
        achievements=["Reduced incidents in 2021"],
    )
    document = create_ready_document(
        db_session,
        [
            (
                "work_experience",
                "Work Experience",
                (
                    "Example Ltd - Software Engineer\n"
                    "Full-time, New York\n"
                    "2020 - 2022\n"
                    "Built reliable APIs at scale\n"
                    "Reduced incidents in 2021\n"
                    "Processed 2023 customer records"
                ),
            ),
        ],
    )

    payload = compare_document(client, document.id)

    for verified_line in [
        "Built reliable APIs at scale",
        "Reduced incidents in 2021",
        "Processed 2023 customer records",
        "2020 - 2022",
    ]:
        assert not matching_findings(
            payload,
            entity_type="work_experience",
            finding_type="unverified_claim",
            cv_value=verified_line,
        )
    assert finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="confirmed",
        field_name="dates",
    )
    assert not finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="date_conflict",
        field_name="dates",
    )


def test_standalone_verified_work_year_is_not_date_evidence(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_experience(
        db_session,
        achievements=["Reduced incidents in 2021"],
    )
    document = create_ready_document(
        db_session,
        [
            (
                "work_experience",
                "Work Experience",
                "Example Ltd - Software Engineer\nReduced incidents in 2021",
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert not matching_findings(
        payload,
        entity_type="work_experience",
        finding_type="unverified_claim",
        cv_value="Reduced incidents in 2021",
    )
    assert not finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="date_conflict",
        field_name="dates",
    )
    assert finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="missing_verified_fact",
        field_name="dates",
    )


def test_genuine_unmatched_work_claim_is_still_unverified(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_experience(db_session)
    document = create_ready_document(
        db_session,
        [
            (
                "work_experience",
                "Work Experience",
                "Unverified Corp - Staff Engineer\n2020 - 2021",
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert matching_findings(
        payload,
        entity_type="work_experience",
        finding_type="unverified_claim",
        cv_value="Unverified Corp - Staff Engineer",
    )
    assert not matching_findings(
        payload,
        entity_type="work_experience",
        finding_type="unverified_claim",
        cv_value="2020 - 2021",
    )


def test_month_year_and_current_work_date_ranges_match(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_experience(
        db_session,
        company="Month Co",
        job_title="Data Engineer",
        start_date=date(2021, 1, 1),
        end_date=date(2023, 3, 1),
    )
    add_experience(
        db_session,
        company="Current Co",
        job_title="Platform Engineer",
        start_date=date(2021, 1, 1),
        end_date=None,
        is_current=True,
    )
    document = create_ready_document(
        db_session,
        [
            (
                "work_experience",
                "Work Experience",
                (
                    "Month Co - Data Engineer\n"
                    "Jan 2021 - Mar 2023\n"
                    "Current Co - Platform Engineer\n"
                    "2021 to Current"
                ),
            ),
        ],
    )

    payload = compare_document(client, document.id)

    confirmed_date_findings = matching_findings(
        payload,
        entity_type="work_experience",
        finding_type="confirmed",
        field_name="dates",
    )
    assert len(confirmed_date_findings) == 2
    assert not finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="date_conflict",
        field_name="dates",
    )


def test_ambiguous_work_date_evidence_requires_manual_review(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_experience(db_session)
    document = create_ready_document(
        db_session,
        [
            (
                "work_experience",
                "Work Experience",
                "Example Ltd - Software Engineer\nStart date: 2020",
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="manual_review",
        field_name="dates",
    )
    assert not finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="date_conflict",
        field_name="dates",
    )
    assert not matching_findings(
        payload,
        entity_type="work_experience",
        finding_type="unverified_claim",
        cv_value="Start date: 2020",
    )


def test_labelled_start_and_end_work_dates_match(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_experience(db_session)
    document = create_ready_document(
        db_session,
        [
            (
                "work_experience",
                "Work Experience",
                (
                    "Example Ltd - Software Engineer\n"
                    "Start date: 2020\n"
                    "End date: 2022"
                ),
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="confirmed",
        field_name="dates",
    )
    assert not finding_exists(
        payload,
        entity_type="work_experience",
        finding_type="date_conflict",
        field_name="dates",
    )
    assert not matching_findings(
        payload,
        entity_type="work_experience",
        finding_type="unverified_claim",
        cv_value="Start date: 2020",
    )
    assert not matching_findings(
        payload,
        entity_type="work_experience",
        finding_type="unverified_claim",
        cv_value="End date: 2022",
    )


def test_project_skill_and_certification_matching(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_project(db_session)
    add_skill(db_session)
    add_certification(db_session)
    document = create_ready_document(
        db_session,
        [
            (
                "projects",
                "Projects",
                (
                    "CareerPilot\nDeveloper Web App\n"
                    "https://example.com/careerpilot\n"
                    "https://github.com/example/careerpilot\n"
                    "Python, FastAPI\n2023 - 2023"
                ),
            ),
            ("skills", "Skills", "Python"),
            (
                "certifications",
                "Certifications",
                (
                    "Cloud Practitioner\nExample Cloud\n"
                    "ABC-123\nhttps://example.com/credential/abc-123\n"
                    "2024 - present"
                ),
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert finding_exists(
        payload,
        entity_type="project",
        finding_type="confirmed",
        field_name="name",
    )
    assert finding_exists(
        payload,
        entity_type="skill",
        finding_type="confirmed",
        field_name="name",
    )
    assert finding_exists(
        payload,
        entity_type="certification",
        finding_type="confirmed",
        field_name="name",
    )


def test_verified_project_descriptions_do_not_become_unverified_claims(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_project(
        db_session,
        features=["Built the 2024 reporting dashboard"],
        achievements=["Processed 2023 customer records"],
    )
    document = create_ready_document(
        db_session,
        [
            (
                "projects",
                "Projects",
                (
                    "CareerPilot\n"
                    "Developer Web App\n"
                    "2023 - 2023\n"
                    "Built the 2024 reporting dashboard\n"
                    "Processed 2023 customer records"
                ),
            ),
        ],
    )

    payload = compare_document(client, document.id)

    for verified_line in [
        "Built the 2024 reporting dashboard",
        "Processed 2023 customer records",
        "2023 - 2023",
    ]:
        assert not matching_findings(
            payload,
            entity_type="project",
            finding_type="unverified_claim",
            cv_value=verified_line,
        )
    assert finding_exists(
        payload,
        entity_type="project",
        finding_type="confirmed",
        field_name="dates",
    )
    assert not finding_exists(
        payload,
        entity_type="project",
        finding_type="date_conflict",
        field_name="dates",
    )


def test_genuine_unmatched_project_claim_is_still_unverified(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_project(db_session)
    document = create_ready_document(
        db_session,
        [
            (
                "projects",
                "Projects",
                "Unlisted Analytics Portal\n2024 - 2025",
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert matching_findings(
        payload,
        entity_type="project",
        finding_type="unverified_claim",
        cv_value="Unlisted Analytics Portal",
    )
    assert not matching_findings(
        payload,
        entity_type="project",
        finding_type="unverified_claim",
        cv_value="2024 - 2025",
    )


def test_skill_unverified_claim_and_ambiguous_manual_review(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_skill(db_session, name="React")
    document = create_ready_document(
        db_session,
        [
            (
                "skills",
                "Skills",
                "React Native, Go",
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert finding_exists(
        payload,
        entity_type="skill",
        finding_type="manual_review",
        field_name="name",
    )
    assert finding_exists(
        payload,
        entity_type="skill",
        finding_type="unverified_claim",
        field_name="name",
    )
    assert payload["manual_review_count"] >= 2


def test_missing_verified_fact_and_unverified_cv_claim(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_education(db_session, institution="Verified University")
    document = create_ready_document(
        db_session,
        [
            (
                "education",
                "Education",
                "Unlisted University, MSc Data Science, 2020 - 2021",
            ),
        ],
    )

    payload = compare_document(client, document.id)

    assert finding_exists(
        payload,
        entity_type="education",
        finding_type="missing_verified_fact",
        field_name="institution",
    )
    assert finding_exists(
        payload,
        entity_type="education",
        finding_type="unverified_claim",
    )


def test_only_verified_vault_records_are_treated_as_truth(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client, facts_verified=False)
    skill = add_skill(db_session, name="Rust", verified=False)
    document = create_ready_document(
        db_session,
        [("skills", "Skills", "Rust")],
    )

    payload = compare_document(client, document.id)

    assert not finding_exists(
        payload,
        entity_type="candidate_profile",
        finding_type="confirmed",
    )
    assert not finding_exists(
        payload,
        entity_type="skill",
        finding_type="confirmed",
    )
    assert finding_exists(
        payload,
        entity_type="skill",
        finding_type="unverified_claim",
    )
    db_session.refresh(skill)
    assert skill.verified is False


def test_comparison_does_not_modify_candidate_facts_vault(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    skill = add_skill(db_session, name="Python")
    education = add_education(db_session)
    profile = db_session.get(CandidateProfile, 1)
    assert profile is not None
    original_profile_updated_at = profile.updated_at
    original_skill_updated_at = skill.updated_at
    original_education_updated_at = education.updated_at
    document = create_ready_document(
        db_session,
        [
            ("skills", "Skills", "Python"),
            (
                "education",
                "Education",
                "Example University, BSc Computer Science, 2018 - 2021",
            ),
        ],
    )

    compare_document(client, document.id)

    db_session.refresh(profile)
    db_session.refresh(skill)
    db_session.refresh(education)
    assert profile.facts_verified is True
    assert skill.verified is True
    assert education.verified is True
    assert profile.updated_at == original_profile_updated_at
    assert skill.updated_at == original_skill_updated_at
    assert education.updated_at == original_education_updated_at


def test_comparison_precondition_errors_and_missing_document(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    not_extracted = create_ready_document(
        db_session,
        [("skills", "Skills", "Python")],
        extraction_status="pending",
    )
    extraction_response = client.post(
        f"/api/documents/{not_extracted.id}/compare-facts"
    )
    assert extraction_response.status_code == 400
    assert "completed text extraction" in extraction_response.json()["detail"]

    no_sections = create_ready_document(
        db_session,
        [("skills", "Skills", "Python")],
        section_detection_status="pending",
    )
    section_response = client.post(
        f"/api/documents/{no_sections.id}/compare-facts"
    )
    assert section_response.status_code == 400
    assert "completed section detection" in section_response.json()["detail"]

    missing_response = client.post("/api/documents/9999/compare-facts")
    assert missing_response.status_code == 404
    assert missing_response.json()["detail"] == "Document was not found."


def test_stable_ordering_safe_recomparison_and_no_duplicate_active_findings(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_skill(db_session, name="Python")
    add_skill(db_session, name="SQL")
    document = create_ready_document(
        db_session,
        [("skills", "Skills", "SQL, Python, Go")],
    )

    first_payload = compare_document(client, document.id)
    second_payload = compare_document(client, document.id)

    first_order = [
        (
            finding["entity_type"],
            finding["finding_type"],
            finding["field_name"],
            finding["normalized_cv_value"],
        )
        for finding in first_payload["findings"]
    ]
    second_order = [
        (
            finding["entity_type"],
            finding["finding_type"],
            finding["field_name"],
            finding["normalized_cv_value"],
        )
        for finding in second_payload["findings"]
    ]
    assert first_order == second_order

    latest_runs = db_session.query(FactComparisonRun).filter_by(
        document_id=document.id,
        is_latest_successful=True,
    ).all()
    assert len(latest_runs) == 1
    assert latest_runs[0].id == second_payload["id"]

    latest_finding_count = db_session.query(FactComparisonFinding).filter_by(
        comparison_run_id=second_payload["id"],
    ).count()
    assert latest_finding_count == second_payload["total_findings"]


def test_previous_success_preserved_after_failed_recomparison(
    client: TestClient,
    db_session: Session,
    monkeypatch: Any,
) -> None:
    create_profile(client)
    add_skill(db_session, name="Python")
    document = create_ready_document(
        db_session,
        [("skills", "Skills", "Python")],
    )
    success_payload = compare_document(client, document.id)

    def fail_comparison(**_kwargs: object) -> object:
        raise RuntimeError("database secret at /internal/path")

    monkeypatch.setattr(
        document_route,
        "compare_document_to_verified_facts",
        fail_comparison,
    )

    failed_response = client.post(
        f"/api/documents/{document.id}/compare-facts"
    )
    assert failed_response.status_code == 200
    failed_payload = failed_response.json()
    assert failed_payload["status"] == "failed"
    assert failed_payload["error"] == "Fact comparison failed."
    assert "/internal/path" not in failed_payload["error"]
    assert failed_payload["status"] != "processing"

    latest_response = client.get(
        f"/api/documents/{document.id}/fact-comparison"
    )
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == success_payload["id"]


def test_evidence_limits_and_document_response_shapes(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    add_education(db_session, institution="Verified University")
    long_claim = f"Unlisted University {'X' * 900}"
    document = create_ready_document(
        db_session,
        [("education", "Education", long_claim)],
    )

    payload = compare_document(client, document.id)
    long_finding = next(
        finding
        for finding in payload["findings"]
        if finding["finding_type"] == "unverified_claim"
    )
    assert len(long_finding["cv_value"]) <= 500
    assert len(long_finding["explanation"]) <= 500

    list_response = client.get("/api/documents")
    assert list_response.status_code == 200
    assert "fact_comparison_summary" not in list_response.json()[0]
    assert "findings" not in list_response.json()[0]

    detail_response = client.get(f"/api/documents/{document.id}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["fact_comparison_summary"]["id"] == payload["id"]
    assert "findings" not in detail_payload["fact_comparison_summary"]

    run_response = client.get(f"/api/fact-comparisons/{payload['id']}")
    assert run_response.status_code == 200
    assert run_response.json()["findings"] == payload["findings"]


def test_fact_comparison_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "fact-comparison-migration.db"
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == [CURRENT_HEAD]
    assert script.get_revision(NEW_HEAD).down_revision == PREVIOUS_HEAD

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{migration_db}")

    with engine.connect() as connection:
        tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table'"
                )
            )
        }
        run_columns = {
            row[1]
            for row in connection.execute(
                text("PRAGMA table_info(fact_comparison_runs)")
            )
        }
        finding_columns = {
            row[1]
            for row in connection.execute(
                text("PRAGMA table_info(fact_comparison_findings)")
            )
        }
    assert "fact_comparison_runs" in tables
    assert "fact_comparison_findings" in tables
    assert {"status", "is_latest_successful"}.issubset(run_columns)
    assert {"finding_type", "dedupe_key"}.issubset(finding_columns)

    command.downgrade(config, PREVIOUS_HEAD)

    with engine.connect() as connection:
        downgraded_tables = {
            row[0]
            for row in connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table'"
                )
            )
        }
    assert "fact_comparison_runs" not in downgraded_tables
    assert "cv_sections" in downgraded_tables

    command.upgrade(config, "head")

    with engine.connect() as connection:
        reupgraded_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' "
                "AND name = 'fact_comparison_runs'"
            )
        ).fetchone()
    assert reupgraded_table is not None

    engine.dispose()
