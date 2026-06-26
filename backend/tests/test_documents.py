import io
import os
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.schemas.document import DocumentType


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
    return response.json()


def make_pdf_bytes() -> bytes:
    return b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def make_docx_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, mode="w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", "<document></document>")
    return buffer.getvalue()


def hash_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def upload_document(
    client: TestClient,
    file_name: str,
    file_bytes: bytes,
    document_type: DocumentType = "original_cv",
    is_primary: bool = False,
    content_type: str | None = None,
) -> Any:
    files = [
        (
            "file",
            (
                file_name,
                file_bytes,
                content_type or "application/octet-stream",
            ),
        ),
        ("document_type", (None, document_type)),
        ("is_primary", (None, "true" if is_primary else "false")),
    ]

    response = client.post("/api/documents/upload", files=files)
    return response


def get_document(client: TestClient, document_id: int) -> Any:
    response = client.get(f"/api/documents/{document_id}")
    return response


def list_documents(client: TestClient) -> Any:
    return client.get("/api/documents")


def delete_document(client: TestClient, document_id: int) -> Any:
    return client.delete(f"/api/documents/{document_id}")


@pytest.fixture(autouse=True)
def set_document_storage_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(
        "CAREERPILOT_DOCUMENT_STORAGE_DIR",
        str(tmp_path / "documents"),
    )


def test_successful_pdf_upload(client: TestClient) -> None:
    create_profile(client)
    response = upload_document(
        client,
        "resume.pdf",
        make_pdf_bytes(),
        content_type="application/pdf",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "resume.pdf"
    assert data["file_extension"] == ".pdf"
    assert data["media_type"] == "application/pdf"
    assert data["upload_status"] == "validated"
    assert data["document_type"] == "original_cv"
    assert data["is_primary"] is False


def test_successful_docx_upload(client: TestClient) -> None:
    create_profile(client)
    response = upload_document(
        client,
        "cover.docx",
        make_docx_bytes(),
        document_type="cover_letter",
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "cover.docx"
    assert data["file_extension"] == ".docx"
    assert data["media_type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert data["document_type"] == "cover_letter"


@pytest.mark.parametrize(
    ("file_name", "file_bytes", "content_type"),
    [
        ("notes.txt", b"hello world", "text/plain"),
        ("resume.doc", make_pdf_bytes(), "application/pdf"),
    ],
)
def test_unsupported_extension_rejection(
    client: TestClient,
    file_name: str,
    file_bytes: bytes,
    content_type: str,
) -> None:
    create_profile(client)
    response = upload_document(
        client,
        file_name,
        file_bytes,
        content_type=content_type,
    )

    assert response.status_code == 400
    assert "Unsupported file extension" in response.json()["detail"] or (
        "file type is not supported" in response.json()["detail"].lower()
    )


def test_mime_and_content_mismatch_rejection(client: TestClient) -> None:
    create_profile(client)
    response = upload_document(
        client,
        "resume.pdf",
        make_docx_bytes(),
        content_type="application/pdf",
    )

    assert response.status_code == 400
    assert "extension does not match file content" in response.json()["detail"].lower()


def test_invalid_pdf_rejection(client: TestClient) -> None:
    create_profile(client)
    response = upload_document(
        client,
        "resume.pdf",
        b"%PDF-INVALID\nnot a valid pdf",
        content_type="application/pdf",
    )

    assert response.status_code == 400
    assert "invalid pdf" in response.json()["detail"].lower()


def test_malformed_docx_rejection(client: TestClient) -> None:
    create_profile(client)
    payload = b"PK\x03\x04corrupt"
    response = upload_document(
        client,
        "resume.docx",
        payload,
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ),
    )

    assert response.status_code == 400
    assert response.json()["detail"].lower() in {
        "uploaded file type is not supported.",
        "invalid docx file.",
        "invalid docx file structure.",
    }


def test_empty_file_rejection(client: TestClient) -> None:
    create_profile(client)
    response = upload_document(
        client,
        "resume.pdf",
        b"",
        content_type="application/pdf",
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_oversized_file_rejection(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAREERPILOT_MAX_DOCUMENT_UPLOAD_SIZE_BYTES", "10")
    create_profile(client)
    response = upload_document(
        client,
        "resume.pdf",
        b"0" * 11,
        content_type="application/pdf",
    )

    assert response.status_code == 400
    assert "exceeds the maximum" in response.json()["detail"].lower()


def test_sha256_generation_and_random_stored_filename(client: TestClient) -> None:
    create_profile(client)
    pdf_bytes = make_pdf_bytes()
    response = upload_document(
        client,
        "resume.pdf",
        pdf_bytes,
        content_type="application/pdf",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sha256_hash"] == hash_bytes(pdf_bytes)
    assert data["stored_filename"] != "resume.pdf"
    assert data["stored_filename"].endswith(".pdf")


def test_document_listing_and_retrieval(client: TestClient) -> None:
    create_profile(client)
    pdf_response = upload_document(
        client,
        "resume.pdf",
        make_pdf_bytes(),
        content_type="application/pdf",
    )
    assert pdf_response.status_code == 201

    list_response = list_documents(client)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1

    document_id = list_response.json()[0]["id"]
    get_response = get_document(client, document_id)
    assert get_response.status_code == 200
    assert get_response.json()["id"] == document_id


def test_missing_document_404(client: TestClient) -> None:
    create_profile(client)
    response = get_document(client, 9999)
    assert response.status_code == 404
    assert response.json()["detail"] == "Document was not found."


def make_alternate_pdf_bytes() -> bytes:
    return b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<>>\nendobj\n2 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF\n"


def test_primary_cv_selection(client: TestClient) -> None:
    create_profile(client)
    first = upload_document(
        client,
        "resume1.pdf",
        make_pdf_bytes(),
        content_type="application/pdf",
        is_primary=True,
    )
    assert first.status_code == 201

    second = upload_document(
        client,
        "resume2.pdf",
        make_alternate_pdf_bytes(),
        content_type="application/pdf",
        is_primary=False,
    )
    assert second.status_code == 201

    document_id = second.json()["id"]
    patch_response = client.patch(f"/api/documents/{document_id}/primary")
    assert patch_response.status_code == 200
    assert patch_response.json()["is_primary"] is True

    list_response = list_documents(client)
    primaries = [item for item in list_response.json() if item["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["id"] == document_id


def test_duplicate_file_rejection(client: TestClient) -> None:
    create_profile(client)
    bytes_data = make_pdf_bytes()
    first = upload_document(
        client,
        "resume.pdf",
        bytes_data,
        content_type="application/pdf",
    )
    assert first.status_code == 201

    second = upload_document(
        client,
        "resume-copy.pdf",
        bytes_data,
        content_type="application/pdf",
    )
    assert second.status_code == 409
    assert "duplicate" in second.json()["detail"].lower()


def test_delete_metadata_and_stored_file(client: TestClient, tmp_path: Path) -> None:
    create_profile(client)
    response = upload_document(
        client,
        "resume.pdf",
        make_pdf_bytes(),
        content_type="application/pdf",
    )
    assert response.status_code == 201
    document_id = response.json()["id"]
    stored_filename = response.json()["stored_filename"]

    storage_dir = Path(os.environ["CAREERPILOT_DOCUMENT_STORAGE_DIR"])
    assert (storage_dir / stored_filename).exists()

    delete_response = delete_document(client, document_id)
    assert delete_response.status_code == 204
    assert not (storage_dir / stored_filename).exists()


def test_delete_missing_file_still_deletes_metadata(client: TestClient) -> None:
    create_profile(client)
    response = upload_document(
        client,
        "resume.pdf",
        make_pdf_bytes(),
        content_type="application/pdf",
    )
    assert response.status_code == 201
    document_id = response.json()["id"]
    stored_filename = response.json()["stored_filename"]

    storage_dir = Path(os.environ["CAREERPILOT_DOCUMENT_STORAGE_DIR"])
    (storage_dir / stored_filename).unlink()

    delete_response = delete_document(client, document_id)
    assert delete_response.status_code == 204


def test_upload_rejection_without_candidate_profile(client: TestClient) -> None:
    response = upload_document(
        client,
        "resume.pdf",
        make_pdf_bytes(),
        content_type="application/pdf",
    )
    assert response.status_code == 400
    assert "candidate profile" in response.json()["detail"].lower()


def test_path_traversal_filename_protection(client: TestClient) -> None:
    create_profile(client)
    response = upload_document(
        client,
        "../../evil.pdf",
        make_pdf_bytes(),
        content_type="application/pdf",
    )

    assert response.status_code == 201
    data = response.json()
    assert data["original_filename"] == "evil.pdf"
    storage_dir = Path(os.environ["CAREERPILOT_DOCUMENT_STORAGE_DIR"])
    assert (storage_dir / data["stored_filename"]).exists()
