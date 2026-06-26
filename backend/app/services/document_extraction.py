from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

from pypdf import PdfReader
from pypdf.errors import FileNotDecryptedError, PdfReadError

from app.core.config import Settings
from app.models.document import Document
from app.services.document_storage import (
    ALLOWED_EXTENSIONS,
    DocumentStorageError,
    assert_within_storage_directory,
)


DOCX_DOCUMENT_XML = "word/document.xml"
MAX_DOCX_XML_BYTES = 20 * 1024 * 1024
NO_EMBEDDED_TEXT_MESSAGE = (
    "No embedded text was found. OCR is not available for this milestone."
)


@dataclass(frozen=True)
class ExtractionResult:
    status: str
    extracted_text: str | None
    extraction_error: str | None
    extracted_at: datetime
    page_count: int | None
    extracted_character_count: int


class DocumentExtractionError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        page_count: int | None = None,
    ) -> None:
        super().__init__(message)
        self.safe_message = message
        self.page_count = page_count


def get_settings() -> Settings:
    return Settings()


def get_storage_dir(settings: Settings) -> Path:
    storage_dir = settings.document_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def resolve_document_path(
    document: Document,
    settings: Settings,
) -> Path:
    storage_dir = get_storage_dir(settings)
    file_path = storage_dir / document.stored_filename

    try:
        assert_within_storage_directory(file_path, storage_dir)
    except DocumentStorageError as exc:
        raise DocumentExtractionError(
            "The stored document path is invalid."
        ) from exc

    if not file_path.exists() or not file_path.is_file():
        raise DocumentExtractionError(
            "The stored document file could not be found."
        )

    return file_path


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\t", " ")
    text = re.sub(r"[ \f\v]+", " ", text)
    lines = [line.strip() for line in text.split("\n")]
    normalized = "\n".join(lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)

    return normalized.strip()


def enforce_text_limit(
    text_parts: list[str],
    max_characters: int,
    *,
    page_count: int | None = None,
) -> None:
    current_length = len(normalize_text("\n\n".join(text_parts)))

    if current_length > max_characters:
        raise DocumentExtractionError(
            "Extracted text exceeds the configured maximum size.",
            page_count=page_count,
        )


def build_result(
    text_parts: list[str],
    *,
    page_count: int | None,
) -> ExtractionResult:
    text = normalize_text("\n\n".join(text_parts))

    if not text:
        return ExtractionResult(
            status="no_text",
            extracted_text=None,
            extraction_error=NO_EMBEDDED_TEXT_MESSAGE,
            extracted_at=datetime.now(timezone.utc),
            page_count=page_count,
            extracted_character_count=0,
        )

    return ExtractionResult(
        status="completed",
        extracted_text=text,
        extraction_error=None,
        extracted_at=datetime.now(timezone.utc),
        page_count=page_count,
        extracted_character_count=len(text),
    )


def extract_pdf_text(
    file_path: Path,
    max_characters: int,
) -> ExtractionResult:
    try:
        reader = PdfReader(str(file_path))
    except PdfReadError as exc:
        raise DocumentExtractionError("Invalid or corrupted PDF file.") from exc
    except Exception as exc:
        raise DocumentExtractionError("PDF text extraction failed.") from exc

    if reader.is_encrypted:
        raise DocumentExtractionError(
            "Encrypted PDF files are not supported.",
            page_count=None,
        )

    text_parts: list[str] = []
    page_count: int | None = None

    try:
        page_count = len(reader.pages)

        for page in reader.pages:
            page_text = page.extract_text() or ""
            normalized_page_text = normalize_text(page_text)

            if normalized_page_text:
                text_parts.append(normalized_page_text)

            enforce_text_limit(
                text_parts,
                max_characters,
                page_count=page_count,
            )
    except PdfReadError as exc:
        raise DocumentExtractionError(
            "Invalid or corrupted PDF file.",
            page_count=page_count,
        ) from exc
    except FileNotDecryptedError as exc:
        raise DocumentExtractionError(
            "Encrypted PDF files are not supported.",
            page_count=None,
        ) from exc
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError(
            "PDF text extraction failed.",
            page_count=page_count,
        ) from exc

    return build_result(text_parts, page_count=page_count)


def read_docx_document_xml(file_path: Path) -> bytes:
    try:
        with zipfile.ZipFile(file_path) as archive:
            if DOCX_DOCUMENT_XML not in archive.namelist():
                raise DocumentExtractionError("Invalid DOCX file structure.")

            document_info = archive.getinfo(DOCX_DOCUMENT_XML)

            if document_info.file_size > MAX_DOCX_XML_BYTES:
                raise DocumentExtractionError(
                    "DOCX document XML exceeds the configured maximum size."
                )

            return archive.read(DOCX_DOCUMENT_XML)
    except DocumentExtractionError:
        raise
    except zipfile.BadZipFile as exc:
        raise DocumentExtractionError("Invalid or corrupted DOCX file.") from exc
    except KeyError as exc:
        raise DocumentExtractionError("Invalid DOCX file structure.") from exc
    except Exception as exc:
        raise DocumentExtractionError("DOCX text extraction failed.") from exc


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def extract_docx_text(
    file_path: Path,
    max_characters: int,
) -> ExtractionResult:
    xml_bytes = read_docx_document_xml(file_path)

    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError as exc:
        raise DocumentExtractionError("Invalid DOCX document XML.") from exc

    paragraphs: list[str] = []

    for element in root.iter():
        if local_name(element.tag) != "p":
            continue

        text_runs: list[str] = []

        for child in element.iter():
            child_name = local_name(child.tag)

            if child_name == "t" and child.text:
                text_runs.append(child.text)
            elif child_name in {"tab", "br"}:
                text_runs.append(" ")

        paragraph_text = normalize_text("".join(text_runs))

        if paragraph_text:
            paragraphs.append(paragraph_text)

        enforce_text_limit(paragraphs, max_characters)

    return build_result(paragraphs, page_count=None)


def extract_document_text(document: Document) -> ExtractionResult:
    if document.upload_status != "validated":
        raise DocumentExtractionError(
            "Only validated documents can be extracted."
        )

    if document.file_extension not in ALLOWED_EXTENSIONS:
        raise DocumentExtractionError("Unsupported document format.")

    settings = get_settings()
    file_path = resolve_document_path(document, settings)
    max_characters = settings.max_document_extracted_text_characters

    if document.file_extension == ".pdf":
        return extract_pdf_text(file_path, max_characters)

    if document.file_extension == ".docx":
        return extract_docx_text(file_path, max_characters)

    raise DocumentExtractionError("Unsupported document format.")
