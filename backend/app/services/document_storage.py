from __future__ import annotations

import re
import zipfile
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import UploadFile

from app.core.config import Settings

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
EXPECTED_MIME_BY_EXTENSION: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
}
REQUIRED_DOCX_FILES = {"[Content_Types].xml", "word/document.xml"}


class DocumentValidationError(ValueError):
    pass


class DocumentStorageError(RuntimeError):
    pass


class DocumentConflictError(RuntimeError):
    pass


def get_settings() -> Settings:
    return Settings()


def sanitize_filename(filename: str) -> str:
    basename = Path(filename).name
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", basename)
    cleaned = cleaned.strip("._-")

    return cleaned or "document"


def get_storage_dir() -> Path:
    settings = get_settings()
    storage_dir = settings.document_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def assert_within_storage_directory(
    candidate_path: Path,
    storage_dir: Path,
) -> None:
    candidate_resolved = candidate_path.resolve()
    storage_resolved = storage_dir.resolve()

    if storage_resolved not in candidate_resolved.parents and (
        candidate_resolved != storage_resolved
    ):
        raise DocumentStorageError(
            "Document path is invalid or outside the allowed storage directory."
        )


def write_upload_to_temp_file(
    upload_file: UploadFile,
    storage_dir: Path,
    max_size_bytes: int,
) -> tuple[Path, int, str]:
    temp_path = storage_dir / f"{uuid4().hex}.tmp"
    hasher = sha256()
    size = 0

    try:
        with temp_path.open("wb") as output_file:
            while True:
                chunk = upload_file.file.read(8192)
                if not chunk:
                    break

                size += len(chunk)
                if size > max_size_bytes:
                    raise DocumentValidationError(
                        "Uploaded file exceeds the maximum allowed size."
                    )

                output_file.write(chunk)
                hasher.update(chunk)

        if size == 0:
            raise DocumentValidationError("Uploaded file is empty.")

        return temp_path, size, hasher.hexdigest()
    except Exception:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)

        raise


def get_declared_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def detect_actual_extension(file_path: Path) -> str:
    with file_path.open("rb") as handle:
        header = handle.read(8)

    if header.startswith(b"%PDF"):
        return ".pdf"

    if zipfile.is_zipfile(file_path):
        return ".docx"

    raise DocumentValidationError("Uploaded file type is not supported.")


def validate_pdf_file(file_path: Path) -> None:
    with file_path.open("rb") as handle:
        contents = handle.read()

    if not contents.startswith(b"%PDF-"):
        raise DocumentValidationError("Invalid PDF file.")

    if b"%%EOF" not in contents[-1024:]:
        raise DocumentValidationError("Invalid PDF file.")


def validate_docx_file(file_path: Path) -> None:
    if not zipfile.is_zipfile(file_path):
        raise DocumentValidationError(
            "Invalid DOCX file."
        )

    with zipfile.ZipFile(file_path) as archive:
        names = set(archive.namelist())

    if not REQUIRED_DOCX_FILES.issubset(names):
        raise DocumentValidationError(
            "Invalid DOCX file structure."
        )


def validate_file_content_type(
    declared_extension: str,
    actual_extension: str,
    content_type: str | None,
) -> None:
    if declared_extension not in ALLOWED_EXTENSIONS:
        raise DocumentValidationError(
            "Unsupported file extension. Only PDF and DOCX are allowed."
        )

    if actual_extension != declared_extension:
        raise DocumentValidationError(
            "File extension does not match file content."
        )

    if content_type in EXPECTED_MIME_BY_EXTENSION.values():
        expected = EXPECTED_MIME_BY_EXTENSION[actual_extension]
        if content_type != expected:
            raise DocumentValidationError(
                "MIME type does not match file content."
            )


def prepare_upload(
    upload_file: UploadFile,
    document_type: str,
    is_primary: bool,
) -> tuple[dict[str, Any], Path]:
    storage_dir = get_storage_dir()
    settings = get_settings()

    original_filename = sanitize_filename(upload_file.filename or "document")
    declared_extension = get_declared_extension(original_filename)

    temp_path, size_bytes, sha256_hash = write_upload_to_temp_file(
        upload_file,
        storage_dir,
        settings.max_document_upload_size_bytes,
    )

    try:
        actual_extension = detect_actual_extension(temp_path)

        if actual_extension == ".pdf":
            validate_pdf_file(temp_path)
        else:
            validate_docx_file(temp_path)

        validate_file_content_type(
            declared_extension,
            actual_extension,
            upload_file.content_type,
        )

        stored_filename = f"{uuid4().hex}{actual_extension}"

        return (
            {
                "original_filename": original_filename,
                "stored_filename": stored_filename,
                "file_extension": actual_extension,
                "media_type": (
                    upload_file.content_type
                    or EXPECTED_MIME_BY_EXTENSION[actual_extension]
                ),
                "size_bytes": size_bytes,
                "sha256_hash": sha256_hash,
                "document_type": document_type,
                "upload_status": "validated",
                "is_primary": is_primary,
            },
            temp_path,
        )
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def save_uploaded_file(temp_path: Path, stored_filename: str) -> Path:
    storage_dir = get_storage_dir()
    final_path = storage_dir / stored_filename
    assert_within_storage_directory(final_path, storage_dir)

    if final_path.exists():
        raise DocumentStorageError(
            "A stored document file already exists with the generated name."
        )

    return temp_path.rename(final_path)


def remove_uploaded_file(stored_filename: str) -> None:
    storage_dir = get_storage_dir()
    file_path = storage_dir / stored_filename
    assert_within_storage_directory(file_path, storage_dir)
    file_path.unlink(missing_ok=True)
