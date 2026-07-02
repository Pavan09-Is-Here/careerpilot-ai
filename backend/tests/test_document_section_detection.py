from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.api.routes import document as document_route
from app.models.document import Document


REPAIR_REVISION = "d8e9f0a1b2c3"


def profile_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "full_name": "Test Candidate",
        "email": "candidate@example.com",
        "phone": None,
        "location": "London",
        "professional_title": "Software Engineer",
        "professional_summary": None,
        "linkedin_url": None,
        "github_url": None,
        "portfolio_url": None,
        "work_authorization": "Right to work confirmed",
        "requires_sponsorship": False,
        "willing_to_relocate": False,
        "preferred_work_modes": ["Remote"],
        "target_roles": ["Backend Engineer"],
        "preferred_locations": ["London"],
        "minimum_salary": 50000,
        "salary_currency": "GBP",
        "minimum_match_score": 85,
        "auto_apply_enabled": False,
        "facts_verified": True,
    }
    payload.update(overrides)

    return payload


def create_profile(client: TestClient) -> dict[str, Any]:
    response = client.put("/api/profile", json=profile_payload())
    assert response.status_code == 200

    return cast(dict[str, Any], response.json())


def create_extracted_document(
    database: Session,
    text_value: str | None,
    *,
    extraction_status: str = "completed",
) -> Document:
    digest_source = f"{text_value or ''}-{uuid4().hex}".encode()
    document = Document(
        candidate_profile_id=1,
        original_filename="resume.pdf",
        stored_filename=f"{uuid4().hex}.pdf",
        file_extension=".pdf",
        media_type="application/pdf",
        size_bytes=len(text_value or ""),
        sha256_hash=sha256(digest_source).hexdigest(),
        document_type="original_cv",
        upload_status="validated",
        is_primary=False,
        extraction_status=extraction_status,
        extracted_text=text_value,
        extraction_error=None,
        extracted_at=datetime.now(timezone.utc),
        page_count=1,
        extracted_character_count=len(text_value or ""),
        section_detection_status="pending",
        section_detection_error=None,
        section_detected_at=None,
        section_count=0,
        section_detection_method=None,
    )
    database.add(document)
    database.commit()
    database.refresh(document)

    return document


def detect_sections(client: TestClient, document_id: int) -> Any:
    return client.post(f"/api/documents/{document_id}/detect-sections")


def get_sections(client: TestClient, document_id: int) -> Any:
    return client.get(f"/api/documents/{document_id}/sections")


def section_types(sections: list[dict[str, Any]]) -> list[str]:
    return [section["section_type"] for section in sections]


def assert_character_ranges(
    text_value: str,
    sections: list[dict[str, Any]],
) -> None:
    for section in sections:
        start = section["start_char"]
        end = section["end_char"]
        assert 0 <= start <= end <= len(text_value)
        assert section["content_text"] == text_value[start:end]
        assert 0 <= section["confidence"] <= 1
        assert (
            section["detection_method"]
            == "deterministic_section_detection_v1"
        )


def test_standard_cv_sections_and_contact_inference(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    cv_text = (
        "Jane Candidate\n"
        "jane@example.com\n"
        "+44 20 7946 0958\n"
        "London, UK\n\n"
        "PROFESSIONAL SUMMARY\n"
        "Backend engineer building reliable APIs.\n\n"
        "WORK EXPERIENCE\n"
        "Example Ltd - Software Engineer\n"
        "Built FastAPI services.\n\n"
        "EDUCATION\n"
        "Example University, BSc Computer Science\n\n"
        "TECHNICAL SKILLS\n"
        "Python, FastAPI, SQLAlchemy\n\n"
        "PROJECTS\n"
        "Career automation platform\n\n"
        "CERTIFICATIONS\n"
        "Cloud Practitioner\n"
    )
    document = create_extracted_document(db_session, cv_text)

    response = detect_sections(client, document.id)

    assert response.status_code == 200
    payload = response.json()
    sections = payload["sections"]
    assert payload["section_detection_status"] == "completed"
    assert payload["section_detection_error"] is None
    assert payload["section_count"] == len(sections)
    assert payload["section_detection_method"] == (
        "deterministic_section_detection_v1"
    )
    assert section_types(sections) == [
        "contact",
        "summary",
        "work_experience",
        "education",
        "skills",
        "projects",
        "certifications",
    ]
    assert sections[0]["title"] == "Contact"
    assert "jane@example.com" in sections[0]["content_text"]
    assert sections[0]["start_char"] == 0
    assert_character_ranges(cv_text, sections)

    list_response = get_sections(client, document.id)
    assert list_response.status_code == 200
    assert list_response.json() == sections


def test_aliases_numbered_headings_and_non_standard_order(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    cv_text = (
        "A. Technical Skills\n"
        "Python, TypeScript\n\n"
        "2. Academic Background\n"
        "Example University\n\n"
        "Work History:\n"
        "Example Ltd\n\n"
        "1. Selected Projects\n"
        "Parser project\n\n"
        "Licences\n"
        "Driver licence\n\n"
        "LANGUAGE SKILLS\n"
        "English\n"
    )
    document = create_extracted_document(db_session, cv_text)

    response = detect_sections(client, document.id)

    assert response.status_code == 200
    sections = response.json()["sections"]
    assert section_types(sections) == [
        "skills",
        "education",
        "work_experience",
        "projects",
        "certifications",
        "languages",
    ]
    assert [section["section_order"] for section in sections] == list(
        range(len(sections))
    )
    assert_character_ranges(cv_text, sections)


def test_missing_headings_fall_back_to_contact_and_additional(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    cv_text = (
        "Jane Candidate\n"
        "jane@example.com\n"
        "\n"
        "Backend engineer with API and database experience."
    )
    document = create_extracted_document(db_session, cv_text)

    response = detect_sections(client, document.id)

    assert response.status_code == 200
    sections = response.json()["sections"]
    assert section_types(sections) == ["contact", "additional"]
    assert "Backend engineer" in sections[1]["content_text"]


def test_repeated_and_empty_sections_are_handled(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    cv_text = (
        "SKILLS\n\n"
        "WORK EXPERIENCE\n"
        "First role\n\n"
        "WORK EXPERIENCE\n"
        "Second role\n"
    )
    document = create_extracted_document(db_session, cv_text)

    response = detect_sections(client, document.id)

    assert response.status_code == 200
    sections = response.json()["sections"]
    assert section_types(sections) == [
        "skills",
        "work_experience",
        "work_experience",
    ]
    assert sections[0]["content_text"] == ""
    assert sections[1]["start_char"] != sections[2]["start_char"]
    assert_character_ranges(cv_text, sections)


def test_section_detection_requires_completed_extraction(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    document = create_extracted_document(
        db_session,
        None,
        extraction_status="no_text",
    )

    response = detect_sections(client, document.id)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Only documents with completed text extraction can be "
        "section-detected."
    )


def test_detect_sections_missing_document_returns_404(
    client: TestClient,
) -> None:
    create_profile(client)

    response = detect_sections(client, 9999)

    assert response.status_code == 404
    assert response.json()["detail"] == "Document was not found."


def test_get_sections_returns_empty_list_before_detection(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    document = create_extracted_document(
        db_session,
        "SUMMARY\nReady for detection.",
    )

    response = get_sections(client, document.id)

    assert response.status_code == 200
    assert response.json() == []


def test_redetection_replaces_old_sections_without_duplicates(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    document = create_extracted_document(
        db_session,
        "SUMMARY\nFirst summary\n\nSKILLS\nPython",
    )

    first_response = detect_sections(client, document.id)
    assert first_response.status_code == 200
    assert section_types(first_response.json()["sections"]) == [
        "summary",
        "skills",
    ]

    document.extracted_text = "EDUCATION\nExample University"
    document.extracted_character_count = len(document.extracted_text)
    db_session.commit()

    second_response = detect_sections(client, document.id)

    assert second_response.status_code == 200
    sections = second_response.json()["sections"]
    assert section_types(sections) == ["education"]
    assert len(sections) == 1

    get_response = get_sections(client, document.id)
    assert get_response.json() == sections


def test_failed_redetection_preserves_previous_valid_sections(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_profile(client)
    document = create_extracted_document(
        db_session,
        "SUMMARY\nReliable backend engineer.",
    )
    first_response = detect_sections(client, document.id)
    assert first_response.status_code == 200
    previous_sections = first_response.json()["sections"]

    def fail_detection(_document: Document) -> object:
        raise RuntimeError("internal parser detail")

    monkeypatch.setattr(
        document_route,
        "detect_document_sections",
        fail_detection,
    )

    failed_response = detect_sections(client, document.id)

    assert failed_response.status_code == 200
    payload = failed_response.json()
    assert payload["section_detection_status"] == "failed"
    assert payload["section_detection_error"] == "CV section detection failed."
    assert "internal parser detail" not in payload["section_detection_error"]
    assert payload["sections"] == previous_sections

    get_response = get_sections(client, document.id)
    assert get_response.json() == previous_sections


def test_section_persistence_failure_records_safe_failure_and_allows_retry(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    create_profile(client)
    document = create_extracted_document(
        db_session,
        "SUMMARY\nReliable backend engineer.",
    )
    first_response = detect_sections(client, document.id)
    assert first_response.status_code == 200
    previous_sections = first_response.json()["sections"]

    document.extracted_text = "EDUCATION\nExample University"
    document.extracted_character_count = len(document.extracted_text)
    db_session.commit()

    original_replace_document_sections = (
        document_route.replace_document_sections
    )

    def fail_section_persistence(
        _document: Document,
        _result: object,
        _database: Session,
    ) -> None:
        raise RuntimeError("database write failed at /internal/path")

    monkeypatch.setattr(
        document_route,
        "replace_document_sections",
        fail_section_persistence,
    )

    failed_response = detect_sections(client, document.id)

    assert failed_response.status_code == 200
    failed_payload = failed_response.json()
    assert failed_payload["section_detection_status"] == "failed"
    assert failed_payload["section_detection_error"] == (
        "CV section detection failed."
    )
    assert "/internal/path" not in failed_payload["section_detection_error"]
    assert failed_payload["sections"] == previous_sections

    db_session.expire_all()
    persisted_document = db_session.get(Document, document.id)
    assert persisted_document is not None
    assert persisted_document.section_detection_status == "failed"
    assert persisted_document.section_detection_status != "processing"
    assert persisted_document.section_count == len(previous_sections)

    monkeypatch.setattr(
        document_route,
        "replace_document_sections",
        original_replace_document_sections,
    )

    retry_response = detect_sections(client, document.id)

    assert retry_response.status_code == 200
    retry_payload = retry_response.json()
    assert retry_payload["section_detection_status"] == "completed"
    assert retry_payload["section_detection_error"] is None
    assert section_types(retry_payload["sections"]) == ["education"]

    get_response = get_sections(client, document.id)
    assert get_response.json() == retry_payload["sections"]


def test_section_detection_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "section-migration-validation.db"
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["e1f2a3b4c5d6"]
    assert script.get_revision(REPAIR_REVISION).down_revision == (
        "b7a3c8d9e012"
    )

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{migration_db}")

    with engine.connect() as connection:
        document_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(documents)"))
        }
        section_columns = {
            row[1]
            for row in connection.execute(
                text("PRAGMA table_info(cv_sections)")
            )
        }
        facts_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'candidate_profiles'"
            )
        ).fetchone()
    assert {
        "section_detection_status",
        "section_detection_error",
        "section_detected_at",
        "section_count",
        "section_detection_method",
    }.issubset(document_columns)
    assert {
        "document_id",
        "section_order",
        "section_type",
        "title",
        "start_char",
        "end_char",
        "content_text",
        "confidence",
        "detection_method",
    }.issubset(section_columns)
    assert facts_table is not None

    command.downgrade(config, REPAIR_REVISION)

    with engine.connect() as connection:
        downgraded_document_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(documents)"))
        }
        section_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'cv_sections'"
            )
        ).fetchone()
        downgraded_facts_table = connection.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type = 'table' AND name = 'candidate_profiles'"
            )
        ).fetchone()
    assert "section_detection_status" not in downgraded_document_columns
    assert section_table is None
    assert downgraded_facts_table is not None

    command.upgrade(config, "head")

    with engine.connect() as connection:
        reupgraded_document_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(documents)"))
        }
    assert "section_detection_status" in reupgraded_document_columns

    engine.dispose()
