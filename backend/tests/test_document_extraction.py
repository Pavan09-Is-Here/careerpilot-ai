import io
import os
import zipfile
from pathlib import Path
from typing import Any, cast
from xml.etree import ElementTree

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.models.document import Document
from app.schemas.document import DocumentType


WORD_NAMESPACE = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


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


def escape_pdf_text(text_value: str) -> str:
    return (
        text_value.replace("\\", "\\\\")
        .replace("(", "\\(")
        .replace(")", "\\)")
    )


def make_text_pdf_bytes(page_texts: list[str]) -> bytes:
    objects: list[str] = [
        "<< /Type /Catalog /Pages 2 0 R >>",
    ]
    kids = " ".join(
        f"{4 + (page_index * 2)} 0 R"
        for page_index in range(len(page_texts))
    )
    objects.append(
        f"<< /Type /Pages /Kids [{kids}] /Count {len(page_texts)} >>"
    )
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    for page_index, page_text in enumerate(page_texts):
        page_object = 4 + (page_index * 2)
        content_object = page_object + 1
        stream = (
            "BT /F1 12 Tf 72 720 Td "
            f"({escape_pdf_text(page_text)}) Tj ET"
        )
        objects.append(
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            "/Resources << /Font << /F1 3 0 R >> >> /Contents "
            f"{content_object} 0 R >>"
        )
        objects.append(
            f"<< /Length {len(stream.encode())} >>\n"
            f"stream\n{stream}\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []

    for object_number, object_body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(
            f"{object_number} 0 obj\n{object_body}\nendobj\n".encode()
        )

    xref_offset = len(output)
    output.extend(
        f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    )

    for offset in offsets:
        output.extend(f"{offset:010d} 00000 n \n".encode())

    output.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return bytes(output)


def make_blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def make_encrypted_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.encrypt("secret")
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def make_docx_bytes(paragraphs: list[str]) -> bytes:
    ElementTree.register_namespace("w", WORD_NAMESPACE)
    document = ElementTree.Element(f"{{{WORD_NAMESPACE}}}document")
    body = ElementTree.SubElement(document, f"{{{WORD_NAMESPACE}}}body")

    for paragraph in paragraphs:
        paragraph_element = ElementTree.SubElement(
            body,
            f"{{{WORD_NAMESPACE}}}p",
        )
        run = ElementTree.SubElement(
            paragraph_element,
            f"{{{WORD_NAMESPACE}}}r",
        )
        text_node = ElementTree.SubElement(run, f"{{{WORD_NAMESPACE}}}t")
        text_node.text = paragraph

    document_xml = ElementTree.tostring(
        document,
        encoding="utf-8",
        xml_declaration=True,
    )
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, mode="w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document_xml)

    return buffer.getvalue()


def upload_document(
    client: TestClient,
    file_name: str,
    file_bytes: bytes,
    document_type: DocumentType = "original_cv",
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
        ("is_primary", (None, "false")),
    ]

    return client.post("/api/documents/upload", files=files)


def stored_file_path(document_payload: dict[str, Any]) -> Path:
    storage_dir = Path(os.environ["CAREERPILOT_DOCUMENT_STORAGE_DIR"])
    stored_filename = cast(str, document_payload["stored_filename"])
    return storage_dir / stored_filename


@pytest.fixture(autouse=True)
def set_document_storage_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv(
        "CAREERPILOT_DOCUMENT_STORAGE_DIR",
        str(tmp_path / "documents"),
    )
    monkeypatch.delenv(
        "CAREERPILOT_MAX_DOCUMENT_EXTRACTED_TEXT_CHARACTERS",
        raising=False,
    )


def test_pdf_extraction_success_and_response_shapes(
    client: TestClient,
) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.pdf",
        make_text_pdf_bytes(["Page one text", "Page two text"]),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201
    assert upload_response.json()["extraction_status"] == "pending"

    document_id = upload_response.json()["id"]
    extract_response = client.post(f"/api/documents/{document_id}/extract")

    expected_text = "Page one text\n\nPage two text"
    assert extract_response.status_code == 200
    extraction_data = extract_response.json()
    assert extraction_data["extraction_status"] == "completed"
    assert extraction_data["page_count"] == 2
    assert extraction_data["extracted_character_count"] == len(expected_text)
    assert "extracted_text" not in extraction_data

    list_response = client.get("/api/documents")
    assert list_response.status_code == 200
    list_item = list_response.json()[0]
    assert list_item["extraction_status"] == "completed"
    assert "extracted_text" not in list_item

    detail_response = client.get(f"/api/documents/{document_id}")
    assert detail_response.status_code == 200
    assert detail_response.json()["extracted_text"] == expected_text


def test_docx_extraction_preserves_paragraph_boundaries(
    client: TestClient,
) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.docx",
        make_docx_bytes(["Summary", "First paragraph", "Second paragraph"]),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml"
            ".document"
        ),
    )
    assert upload_response.status_code == 201

    document_id = upload_response.json()["id"]
    extract_response = client.post(f"/api/documents/{document_id}/extract")
    detail_response = client.get(f"/api/documents/{document_id}")

    assert extract_response.status_code == 200
    assert extract_response.json()["extraction_status"] == "completed"
    assert extract_response.json()["page_count"] is None
    assert detail_response.json()["extracted_text"] == (
        "Summary\n\nFirst paragraph\n\nSecond paragraph"
    )


def test_extract_missing_document_returns_404(client: TestClient) -> None:
    create_profile(client)
    response = client.post("/api/documents/9999/extract")

    assert response.status_code == 404
    assert response.json()["detail"] == "Document was not found."


def test_unvalidated_document_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.pdf",
        make_text_pdf_bytes(["Verified text"]),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    document = db_session.get(Document, document_id)
    assert document is not None
    document.upload_status = "uploaded"
    db_session.commit()

    response = client.post(f"/api/documents/{document_id}/extract")
    assert response.status_code == 400
    assert response.json()["detail"] == "Only validated documents can be extracted."


def test_unsupported_format_is_rejected(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.pdf",
        make_text_pdf_bytes(["Verified text"]),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    document = db_session.get(Document, document_id)
    assert document is not None
    document.file_extension = ".txt"
    db_session.commit()

    response = client.post(f"/api/documents/{document_id}/extract")
    assert response.status_code == 400
    assert response.json()["detail"] == "Unsupported document format."


def test_missing_stored_file_fails_safely(client: TestClient) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.pdf",
        make_text_pdf_bytes(["Verified text"]),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    path = stored_file_path(upload_payload)
    path.unlink()

    response = client.post(f"/api/documents/{upload_payload['id']}/extract")

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_status"] == "failed"
    assert data["extraction_error"] == "The stored document file could not be found."
    assert str(path.parent) not in data["extraction_error"]


def test_corrupt_pdf_fails_safely(client: TestClient) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.pdf",
        make_text_pdf_bytes(["Verified text"]),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    stored_file_path(upload_payload).write_bytes(
        b"%PDF-1.7\nnot a readable pdf\n%%EOF\n"
    )

    response = client.post(f"/api/documents/{upload_payload['id']}/extract")

    assert response.status_code == 200
    assert response.json()["extraction_status"] == "failed"
    assert "PDF" in response.json()["extraction_error"]


def test_corrupt_docx_fails_safely(client: TestClient) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.docx",
        make_docx_bytes(["Verified text"]),
        content_type=(
            "application/vnd.openxmlformats-officedocument.wordprocessingml"
            ".document"
        ),
    )
    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    stored_file_path(upload_payload).write_bytes(b"not a zip archive")

    response = client.post(f"/api/documents/{upload_payload['id']}/extract")

    assert response.status_code == 200
    assert response.json()["extraction_status"] == "failed"
    assert "DOCX" in response.json()["extraction_error"]


def test_encrypted_pdf_fails_safely(client: TestClient) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "encrypted.pdf",
        make_encrypted_pdf_bytes(),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201

    response = client.post(
        f"/api/documents/{upload_response.json()['id']}/extract"
    )

    assert response.status_code == 200
    assert response.json()["extraction_status"] == "failed"
    assert response.json()["extraction_error"] == (
        "Encrypted PDF files are not supported."
    )


def test_textless_pdf_returns_no_text(client: TestClient) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "blank.pdf",
        make_blank_pdf_bytes(),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201

    response = client.post(
        f"/api/documents/{upload_response.json()['id']}/extract"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_status"] == "no_text"
    assert data["page_count"] == 1
    assert data["extracted_character_count"] == 0
    assert "OCR is not available" in data["extraction_error"]


def test_re_extraction_clears_stale_error(client: TestClient) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.pdf",
        make_text_pdf_bytes(["Verified text"]),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201
    upload_payload = upload_response.json()
    path = stored_file_path(upload_payload)
    path.write_bytes(b"%PDF-1.7\nbroken\n%%EOF\n")

    first_response = client.post(f"/api/documents/{upload_payload['id']}/extract")
    assert first_response.status_code == 200
    assert first_response.json()["extraction_status"] == "failed"

    path.write_bytes(make_text_pdf_bytes(["Fresh verified text"]))
    second_response = client.post(f"/api/documents/{upload_payload['id']}/extract")

    assert second_response.status_code == 200
    assert second_response.json()["extraction_status"] == "completed"
    assert second_response.json()["extraction_error"] is None


def test_path_traversal_stored_filename_fails_safely(
    client: TestClient,
    db_session: Session,
) -> None:
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.pdf",
        make_text_pdf_bytes(["Verified text"]),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201
    document_id = upload_response.json()["id"]

    document = db_session.get(Document, document_id)
    assert document is not None
    document.stored_filename = "../evil.pdf"
    db_session.commit()

    response = client.post(f"/api/documents/{document_id}/extract")

    assert response.status_code == 200
    data = response.json()
    assert data["extraction_status"] == "failed"
    assert data["extraction_error"] == "The stored document path is invalid."
    assert ".." not in data["extraction_error"]


def test_extracted_text_limit_is_enforced(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CAREERPILOT_MAX_DOCUMENT_EXTRACTED_TEXT_CHARACTERS",
        "20",
    )
    create_profile(client)
    upload_response = upload_document(
        client,
        "resume.pdf",
        make_text_pdf_bytes(["This extracted text is intentionally long."]),
        content_type="application/pdf",
    )
    assert upload_response.status_code == 201

    response = client.post(
        f"/api/documents/{upload_response.json()['id']}/extract"
    )

    assert response.status_code == 200
    assert response.json()["extraction_status"] == "failed"
    assert response.json()["extraction_error"] == (
        "Extracted text exceeds the configured maximum size."
    )


def test_document_extraction_migration_upgrade_downgrade_reupgrade(
    tmp_path: Path,
) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    migration_db = tmp_path / "migration-validation.db"
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{migration_db}")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["b8c9d0e1f2a3"]
    assert script.get_revision("b7a3c8d9e012").revision == "b7a3c8d9e012"

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{migration_db}")

    with engine.connect() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(documents)"))
        }
    assert {
        "extraction_status",
        "extracted_text",
        "extraction_error",
        "extracted_at",
        "page_count",
        "extracted_character_count",
    }.issubset(columns)

    command.downgrade(config, "6a528be87510")

    with engine.connect() as connection:
        downgraded_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(documents)"))
        }
    assert "extraction_status" not in downgraded_columns
    assert "extracted_text" not in downgraded_columns

    command.upgrade(config, "head")

    with engine.connect() as connection:
        reupgraded_columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(documents)"))
        }
    assert "extraction_status" in reupgraded_columns

    engine.dispose()
