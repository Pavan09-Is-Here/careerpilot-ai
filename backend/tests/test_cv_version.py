from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, inspect, select, text
from sqlalchemy.orm import Session

from app.models.candidate_profile import CandidateProfile
from app.models.cv_section import CVSection
from app.models.cv_version import CVVersion
from app.models.document import Document
from app.models.fact_comparison import FactComparisonRun
from app.services import cv_version as cv_version_service


PHASE35_HEAD = "e5f6a7b8c9d0"
PHASE36_HEAD = "f6a7b8c9d0e1"
CURRENT_HEAD = "f8a9b0c1d2e3"


@pytest.fixture(autouse=True)
def clear_cv_versions_after_test(db_session: Session) -> None:
    yield
    db_session.rollback()
    db_session.execute(text("PRAGMA foreign_keys=OFF"))
    db_session.execute(text("DELETE FROM cv_versions"))
    db_session.commit()
    db_session.execute(text("PRAGMA foreign_keys=ON"))


def make_profile(
    database: Session,
    *,
    profile_id: int = 1,
    full_name: str = "Test Candidate",
) -> CandidateProfile:
    profile = CandidateProfile(
        id=profile_id,
        full_name=full_name,
        email=f"candidate-{profile_id}@example.com",
        phone=None,
        location="London",
        professional_title="Software Engineer",
        professional_summary=None,
        linkedin_url=None,
        github_url=None,
        portfolio_url=None,
        work_authorization="Right to work confirmed",
        requires_sponsorship=False,
        willing_to_relocate=False,
        preferred_work_modes=["Remote"],
        target_roles=["Backend Engineer"],
        preferred_locations=["London"],
        minimum_salary=50000,
        salary_currency="GBP",
        minimum_match_score=85,
        auto_apply_enabled=False,
        facts_verified=True,
    )
    database.add(profile)
    database.commit()
    database.refresh(profile)
    return profile


def make_document(
    database: Session,
    *,
    candidate_profile_id: int = 1,
    document_type: str = "original_cv",
    upload_status: str = "validated",
    original_filename: str | None = None,
) -> Document:
    token = uuid4().hex
    digest = sha256(f"{candidate_profile_id}-{token}".encode()).hexdigest()
    document = Document(
        candidate_profile_id=candidate_profile_id,
        original_filename=original_filename or f"resume-{token}.pdf",
        stored_filename=f"{token}.pdf",
        file_extension=".pdf",
        media_type="application/pdf",
        size_bytes=128,
        sha256_hash=digest,
        document_type=document_type,
        upload_status=upload_status,
        is_primary=False,
        extraction_status="completed",
        extracted_text="Synthetic CV text that is not returned by versions.",
        extraction_error=None,
        extracted_at=datetime.now(timezone.utc),
        page_count=1,
        extracted_character_count=48,
        section_detection_status="completed",
        section_detection_error=None,
        section_detected_at=datetime.now(timezone.utc),
        section_count=0,
        section_detection_method="test",
    )
    database.add(document)
    database.commit()
    database.refresh(document)
    return document


def make_cv_version(
    database: Session,
    *,
    candidate_profile_id: int = 1,
    version_type: str = "original",
    status: str = "ready",
    parent_version_id: int | None = None,
    source_document_id: int | None = None,
    display_name: str | None = None,
    is_primary: bool = False,
    created_at: datetime | None = None,
    storage_path: str | None = None,
) -> CVVersion:
    document: Document | None = None

    if version_type == "original" and source_document_id is None:
        document = make_document(
            database,
            candidate_profile_id=candidate_profile_id,
        )
        source_document_id = document.id

    now = created_at or datetime.now(timezone.utc)
    digest = sha256(f"{version_type}-{uuid4().hex}".encode()).hexdigest()
    version = CVVersion(
        candidate_profile_id=candidate_profile_id,
        source_document_id=source_document_id,
        parent_version_id=parent_version_id,
        version_type=version_type,
        status=status,
        display_name=display_name or f"{version_type} {uuid4().hex[:8]}",
        description=None,
        job_reference=None,
        is_primary=is_primary,
        storage_path=storage_path,
        mime_type=document.media_type if document else "application/pdf",
        file_size=document.size_bytes if document else 128,
        sha256=document.sha256_hash if document else digest,
        created_at=now,
        updated_at=now,
        archived_at=now if status == "archived" else None,
    )
    database.add(version)
    database.commit()
    database.refresh(version)
    return version


def get_version(database: Session, version_id: int) -> CVVersion | None:
    database.expire_all()
    return database.get(CVVersion, version_id)


def count_cv_versions(database: Session) -> int:
    return (
        database.scalar(select(func.count()).select_from(CVVersion)) or 0
    )


def assert_no_private_document_fields(payload: dict[str, Any]) -> None:
    assert "storage_path" not in payload
    assert "extracted_text" not in payload
    assert "stored_filename" not in payload


def assert_outside_repository(path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]

    try:
        path.resolve().relative_to(repository_root)
    except ValueError:
        return

    raise AssertionError(f"Temporary database is inside repository: {path}")


def test_adopt_original_version_from_validated_document(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    document = make_document(db_session, original_filename="base-cv.pdf")
    original_metadata = {
        "stored_filename": document.stored_filename,
        "sha256_hash": document.sha256_hash,
        "size_bytes": document.size_bytes,
    }

    response = client.post(
        f"/api/documents/{document.id}/cv-version",
        json={
            "display_name": "Original CV",
            "description": "Uploaded baseline CV.",
            "status": "ready",
            "is_primary": True,
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["version_type"] == "original"
    assert payload["status"] == "ready"
    assert payload["source_document_id"] == document.id
    assert payload["parent_version_id"] is None
    assert payload["is_primary"] is True
    assert payload["mime_type"] == "application/pdf"
    assert payload["file_size"] == document.size_bytes
    assert payload["sha256"] == document.sha256_hash
    assert_no_private_document_fields(payload)

    db_session.expire_all()
    persisted_document = db_session.get(Document, document.id)
    assert persisted_document is not None
    assert persisted_document.stored_filename == original_metadata["stored_filename"]
    assert persisted_document.sha256_hash == original_metadata["sha256_hash"]
    assert persisted_document.size_bytes == original_metadata["size_bytes"]


def test_original_adoption_is_idempotent(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    document = make_document(db_session)

    first = client.post(f"/api/documents/{document.id}/cv-version")
    second = client.post(
        f"/api/documents/{document.id}/cv-version",
        json={"display_name": "Duplicate request", "is_primary": True},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["is_primary"] is True
    assert count_cv_versions(db_session) == 1


def test_adoption_rejects_missing_document(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)

    response = client.post("/api/documents/999999/cv-version")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document was not found."


@pytest.mark.parametrize(
    ("document_type", "upload_status"),
    [
        ("original_cv", "pending"),
        ("cover_letter", "validated"),
    ],
)
def test_adoption_rejects_invalid_document(
    client: TestClient,
    db_session: Session,
    document_type: str,
    upload_status: str,
) -> None:
    make_profile(db_session)
    document = make_document(
        db_session,
        document_type=document_type,
        upload_status=upload_status,
    )

    response = client.post(f"/api/documents/{document.id}/cv-version")

    assert response.status_code == 400
    assert "Only" in response.json()["detail"]


def test_create_parsed_version_from_original(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(db_session, version_type="original")

    response = client.post(
        "/api/cv-versions",
        json={
            "version_type": "parsed",
            "parent_version_id": original.id,
            "status": "ready",
            "display_name": "Parsed CV",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["version_type"] == "parsed"
    assert payload["parent_version_id"] == original.id
    assert payload["source_document_id"] is None


def test_generic_create_verified_master_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(db_session, version_type="original")
    parsed = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
    )

    first = client.post(
        "/api/cv-versions",
        json={
            "version_type": "verified_master",
            "parent_version_id": parsed.id,
            "status": "ready",
            "display_name": "Verified Master",
        },
    )

    assert first.status_code == 400
    assert first.json()["detail"] == (
        "Use the verified master generation workflow to create "
        "verified master CV versions."
    )


def test_create_tailored_version_from_verified_master(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(db_session, version_type="original")
    parsed = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
    )
    verified = make_cv_version(
        db_session,
        version_type="verified_master",
        parent_version_id=parsed.id,
    )

    response = client.post(
        "/api/cv-versions",
        json={
            "version_type": "tailored",
            "parent_version_id": verified.id,
            "status": "draft",
            "display_name": "Tailored for Example Role",
            "job_reference": "Example Role",
        },
    )

    assert response.status_code == 201
    assert response.json()["version_type"] == "tailored"
    assert response.json()["parent_version_id"] == verified.id


@pytest.mark.parametrize(
    ("version_type", "parent_type"),
    [
        ("parsed", "parsed"),
        ("tailored", "original"),
    ],
)
def test_invalid_parent_types_are_rejected(
    client: TestClient,
    db_session: Session,
    version_type: str,
    parent_type: str,
) -> None:
    make_profile(db_session)
    parent = make_cv_version(db_session, version_type=parent_type)

    response = client.post(
        "/api/cv-versions",
        json={
            "version_type": version_type,
            "parent_version_id": parent.id,
            "display_name": "Invalid child",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Parent CV version type is not valid for this version type."
    )


def test_self_parent_update_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    version = make_cv_version(db_session, version_type="original")

    response = client.patch(
        f"/api/cv-versions/{version.id}",
        json={"parent_version_id": version.id},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "A CV version cannot be its own parent."


def test_circular_ancestry_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(db_session, version_type="original")
    parsed = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
    )
    verified = make_cv_version(
        db_session,
        version_type="verified_master",
        parent_version_id=parsed.id,
    )
    original.parent_version_id = verified.id
    db_session.commit()

    response = client.post(
        "/api/cv-versions",
        json={
            "version_type": "parsed",
            "parent_version_id": original.id,
            "display_name": "Cycle child",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "Circular CV version ancestry is not allowed."
    )


def test_cross_candidate_parent_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session, profile_id=1)
    make_profile(db_session, profile_id=2, full_name="Other Candidate")
    other_parent = make_cv_version(
        db_session,
        candidate_profile_id=2,
        version_type="original",
    )

    response = client.post(
        "/api/cv-versions",
        json={
            "version_type": "parsed",
            "parent_version_id": other_parent.id,
            "display_name": "Cross-candidate child",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "CV version was not found."


def test_cross_candidate_source_document_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session, profile_id=1)
    make_profile(db_session, profile_id=2, full_name="Other Candidate")
    other_document = make_document(db_session, candidate_profile_id=2)

    response = client.post(
        "/api/cv-versions",
        json={
            "version_type": "original",
            "source_document_id": other_document.id,
            "display_name": "Cross-candidate original",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Document was not found."


def test_list_versions_in_stable_order(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    timestamp = datetime.now(timezone.utc)
    oldest = make_cv_version(
        db_session,
        version_type="original",
        created_at=timestamp,
    )
    same_time_higher_id = make_cv_version(
        db_session,
        version_type="original",
        created_at=timestamp,
    )
    newest = make_cv_version(
        db_session,
        version_type="original",
        created_at=timestamp + timedelta(seconds=1),
    )

    response = client.get("/api/cv-versions")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [
        newest.id,
        same_time_higher_id.id,
        oldest.id,
    ]


def test_retrieve_one_version_returns_metadata_only(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    version = make_cv_version(
        db_session,
        version_type="original",
        storage_path="/internal/storage/generated.pdf",
    )

    response = client.get(f"/api/cv-versions/{version.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == version.id
    assert payload["display_name"] == version.display_name
    assert_no_private_document_fields(payload)


def test_missing_version_returns_404(
    client: TestClient,
) -> None:
    response = client.get("/api/cv-versions/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "CV version was not found."


def test_update_allowed_metadata(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    version = make_cv_version(db_session, version_type="original")

    response = client.patch(
        f"/api/cv-versions/{version.id}",
        json={
            "display_name": "Renamed CV",
            "description": "Metadata only update.",
            "job_reference": "Reference",
            "status": "draft",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["display_name"] == "Renamed CV"
    assert payload["description"] == "Metadata only update."
    assert payload["job_reference"] == "Reference"
    assert payload["status"] == "draft"


@pytest.mark.parametrize(
    "payload",
    [
        {"version_type": "parsed"},
        {"source_document_id": 1},
        {"parent_version_id": 999},
    ],
)
def test_immutable_relationship_fields_are_rejected(
    client: TestClient,
    db_session: Session,
    payload: dict[str, int | str],
) -> None:
    make_profile(db_session)
    version = make_cv_version(db_session, version_type="original")

    response = client.patch(f"/api/cv-versions/{version.id}", json=payload)

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "CV version relationship fields cannot be modified."
    )


def test_set_primary_version(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    version = make_cv_version(db_session, version_type="original")

    response = client.patch(f"/api/cv-versions/{version.id}/primary")

    assert response.status_code == 200
    assert response.json()["is_primary"] is True
    persisted = get_version(db_session, version.id)
    assert persisted is not None
    assert persisted.is_primary is True


def test_prior_primary_of_same_type_is_unset(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(db_session, version_type="original")
    first = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
        is_primary=True,
    )
    second = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
    )

    response = client.patch(f"/api/cv-versions/{second.id}/primary")

    assert response.status_code == 200
    refreshed_first = get_version(db_session, first.id)
    refreshed_second = get_version(db_session, second.id)
    assert refreshed_first is not None
    assert refreshed_second is not None
    assert refreshed_first.is_primary is False
    assert refreshed_second.is_primary is True


def test_different_version_types_can_each_have_primary(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(
        db_session,
        version_type="original",
        is_primary=True,
    )
    parsed = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
    )

    response = client.patch(f"/api/cv-versions/{parsed.id}/primary")

    assert response.status_code == 200
    refreshed_original = get_version(db_session, original.id)
    refreshed_parsed = get_version(db_session, parsed.id)
    assert refreshed_original is not None
    assert refreshed_parsed is not None
    assert refreshed_original.is_primary is True
    assert refreshed_parsed.is_primary is True


@pytest.mark.parametrize(
    ("status_value", "message"),
    [
        ("archived", "Archived CV versions cannot be primary."),
        ("failed", "Failed CV versions cannot be primary."),
    ],
)
def test_archived_and_failed_versions_cannot_be_primary(
    client: TestClient,
    db_session: Session,
    status_value: str,
    message: str,
) -> None:
    make_profile(db_session)
    version = make_cv_version(
        db_session,
        version_type="original",
        status=status_value,
    )

    response = client.patch(f"/api/cv-versions/{version.id}/primary")

    assert response.status_code == 400
    assert response.json()["detail"] == message


def test_archiving_primary_version_clears_primary_state(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    version = make_cv_version(
        db_session,
        version_type="original",
        is_primary=True,
    )

    response = client.patch(f"/api/cv-versions/{version.id}/archive")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "archived"
    assert payload["is_primary"] is False
    assert payload["archived_at"] is not None


def test_archive_preserves_children_and_history(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(db_session, version_type="original")
    parsed = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
    )

    archive_response = client.patch(f"/api/cv-versions/{original.id}/archive")
    history_response = client.get(f"/api/cv-versions/{parsed.id}/history")

    assert archive_response.status_code == 200
    assert history_response.status_code == 200
    history = history_response.json()
    assert [item["id"] for item in history["ancestry"]] == [
        original.id,
        parsed.id,
    ]
    assert history["ancestry"][0]["status"] == "archived"


def test_unsafe_deletion_with_child_versions_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(db_session, version_type="original")
    child = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
    )

    response = client.delete(f"/api/cv-versions/{original.id}")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "CV versions with child history cannot be deleted."
    )
    assert get_version(db_session, original.id) is not None
    assert get_version(db_session, child.id) is not None


def test_safe_deletion_without_children_succeeds(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    version = make_cv_version(db_session, version_type="original")

    response = client.delete(f"/api/cv-versions/{version.id}")

    assert response.status_code == 204
    assert get_version(db_session, version.id) is None


def test_source_document_sections_and_comparisons_survive_version_delete(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    document = make_document(db_session)
    section = CVSection(
        document_id=document.id,
        section_order=0,
        section_type="summary",
        title="Summary",
        start_char=0,
        end_char=10,
        content_text="Synthetic.",
        confidence=0.95,
        detection_method="test",
        created_at=datetime.now(timezone.utc),
    )
    run = FactComparisonRun(
        document_id=document.id,
        status="completed",
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
        error=None,
        total_findings=0,
        confirmed_count=0,
        mismatch_count=0,
        missing_verified_count=0,
        unverified_claim_count=0,
        manual_review_count=0,
        comparison_version="test",
        is_latest_successful=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add_all([section, run])
    db_session.commit()
    version = make_cv_version(
        db_session,
        version_type="original",
        source_document_id=document.id,
    )
    original_document_state = (
        document.stored_filename,
        document.sha256_hash,
    )

    response = client.delete(f"/api/cv-versions/{version.id}")

    assert response.status_code == 204
    db_session.expire_all()
    persisted_document = db_session.get(Document, document.id)
    assert persisted_document is not None
    assert (
        persisted_document.stored_filename,
        persisted_document.sha256_hash,
    ) == original_document_state
    assert db_session.get(CVSection, section.id) is not None
    assert db_session.get(FactComparisonRun, run.id) is not None


def test_version_history_ancestry_is_returned_in_order(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    original = make_cv_version(db_session, version_type="original")
    parsed = make_cv_version(
        db_session,
        version_type="parsed",
        parent_version_id=original.id,
    )
    verified = make_cv_version(
        db_session,
        version_type="verified_master",
        parent_version_id=parsed.id,
    )
    tailored = make_cv_version(
        db_session,
        version_type="tailored",
        parent_version_id=verified.id,
    )

    response = client.get(f"/api/cv-versions/{tailored.id}/history")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload["ancestry"]] == [
        original.id,
        parsed.id,
        verified.id,
        tailored.id,
    ]
    assert [item["version_type"] for item in payload["ancestry"]] == [
        "original",
        "parsed",
        "verified_master",
        "tailored",
    ]
    assert payload["children"] == []


def test_failed_primary_switch_preserves_prior_primary(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_profile(db_session)
    first = make_cv_version(
        db_session,
        version_type="original",
        is_primary=True,
    )
    second = make_cv_version(db_session, version_type="original")
    original_clear = cv_version_service.clear_primary_for_type

    def fail_after_clear(*args: Any, **kwargs: Any) -> None:
        original_clear(*args, **kwargs)
        raise RuntimeError("internal /tmp/secret database failure")

    monkeypatch.setattr(
        cv_version_service,
        "clear_primary_for_type",
        fail_after_clear,
    )

    response = client.patch(f"/api/cv-versions/{second.id}/primary")

    assert response.status_code == 500
    detail = response.json()["detail"]
    assert detail == "Failed to set primary CV version."
    assert "/tmp/secret" not in detail
    refreshed_first = get_version(db_session, first.id)
    refreshed_second = get_version(db_session, second.id)
    assert refreshed_first is not None
    assert refreshed_second is not None
    assert refreshed_first.is_primary is True
    assert refreshed_second.is_primary is False


def test_failed_primary_create_does_not_leave_partial_version(
    client: TestClient,
    db_session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_profile(db_session)
    existing_primary = make_cv_version(
        db_session,
        version_type="original",
        is_primary=True,
    )
    new_document = make_document(db_session)
    original_clear = cv_version_service.clear_primary_for_type

    def fail_after_clear(*args: Any, **kwargs: Any) -> None:
        original_clear(*args, **kwargs)
        raise RuntimeError("internal database failure")

    monkeypatch.setattr(
        cv_version_service,
        "clear_primary_for_type",
        fail_after_clear,
    )

    response = client.post(
        "/api/cv-versions",
        json={
            "version_type": "original",
            "source_document_id": new_document.id,
            "display_name": "Will roll back",
            "is_primary": True,
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to create CV version."
    assert count_cv_versions(db_session) == 1
    refreshed_primary = get_version(db_session, existing_primary.id)
    assert refreshed_primary is not None
    assert refreshed_primary.is_primary is True


def test_duplicate_original_versions_are_prevented(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    document = make_document(db_session)

    first = client.post(
        "/api/cv-versions",
        json={
            "version_type": "original",
            "source_document_id": document.id,
            "display_name": "Original",
        },
    )
    second = client.post(
        "/api/cv-versions",
        json={
            "version_type": "original",
            "source_document_id": document.id,
            "display_name": "Duplicate original",
            "is_primary": True,
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["id"] == first.json()["id"]
    assert second.json()["is_primary"] is True
    assert count_cv_versions(db_session) == 1


def test_general_list_responses_exclude_private_storage_and_content(
    client: TestClient,
    db_session: Session,
) -> None:
    make_profile(db_session)
    make_cv_version(
        db_session,
        version_type="original",
        storage_path="/internal/storage/private.pdf",
    )

    response = client.get("/api/cv-versions")

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert_no_private_document_fields(response.json()[0])


def test_candidate_facts_vault_records_are_not_modified(
    client: TestClient,
    db_session: Session,
) -> None:
    profile = make_profile(db_session)
    document = make_document(db_session)
    expected_profile_state = {
        "full_name": profile.full_name,
        "facts_verified": profile.facts_verified,
        "target_roles": list(profile.target_roles),
    }

    adopt_response = client.post(f"/api/documents/{document.id}/cv-version")
    version_id = adopt_response.json()["id"]
    archive_response = client.patch(f"/api/cv-versions/{version_id}/archive")

    assert adopt_response.status_code == 201
    assert archive_response.status_code == 200
    db_session.expire_all()
    persisted_profile = db_session.get(CandidateProfile, profile.id)
    assert persisted_profile is not None
    assert {
        "full_name": persisted_profile.full_name,
        "facts_verified": persisted_profile.facts_verified,
        "target_roles": list(persisted_profile.target_roles),
    } == expected_profile_state


def test_cv_version_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "cv-version-migration.db"
    assert_outside_repository(migration_db)

    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == [CURRENT_HEAD]
    assert script.get_revision(PHASE36_HEAD).down_revision == PHASE35_HEAD

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{migration_db}")

    try:
        inspector = inspect(engine)
        assert "cv_versions" in inspector.get_table_names()
        index_names = {
            index["name"]
            for index in inspector.get_indexes("cv_versions")
        }
        assert {
            "ix_cv_versions_candidate_profile_id",
            "ix_cv_versions_source_document_id",
            "ix_cv_versions_parent_version_id",
            "ix_cv_versions_candidate_type",
            "uq_cv_versions_primary_per_type",
        }.issubset(index_names)
        foreign_keys = {
            (
                foreign_key["constrained_columns"][0],
                foreign_key["referred_table"],
                foreign_key["referred_columns"][0],
                foreign_key.get("options", {}).get("ondelete"),
            )
            for foreign_key in inspector.get_foreign_keys("cv_versions")
        }
        assert {
            ("candidate_profile_id", "candidate_profiles", "id", "CASCADE"),
            ("source_document_id", "documents", "id", "SET NULL"),
            ("parent_version_id", "cv_versions", "id", "RESTRICT"),
        }.issubset(foreign_keys)

        with engine.connect() as connection:
            upgraded_tables = {
                row[0]
                for row in connection.execute(
                    text(
                        "SELECT name FROM sqlite_master "
                        "WHERE type = 'table'"
                    )
                )
            }

        command.downgrade(config, PHASE35_HEAD)

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
        assert {
            "cv_versions",
            "cv_version_artifacts",
        }.issubset(upgraded_tables - downgraded_tables)
        assert "fact_comparison_runs" in downgraded_tables

        command.upgrade(config, "head")

        with engine.connect() as connection:
            restored_table = connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name = 'cv_versions'"
                )
            ).fetchone()
        assert restored_table is not None
        assert script.get_heads() == [CURRENT_HEAD]
    finally:
        engine.dispose()
