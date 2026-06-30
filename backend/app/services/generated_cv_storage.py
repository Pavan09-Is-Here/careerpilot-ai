from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

from app.core.config import Settings
from app.services.document_storage import sanitize_filename


ARTIFACT_MIME_TYPES = {
    "docx": (
        "application/vnd.openxmlformats-officedocument."
        "wordprocessingml.document"
    ),
    "pdf": "application/pdf",
}

ARTIFACT_EXTENSIONS = {
    "docx": ".docx",
    "pdf": ".pdf",
}


class GeneratedCVStorageError(RuntimeError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.safe_message = message


@dataclass(frozen=True)
class StoredGeneratedArtifact:
    artifact_type: str
    mime_type: str
    safe_filename: str
    storage_path: str
    file_size: int
    sha256: str
    page_count: int | None


def get_settings() -> Settings:
    return Settings()


def get_generated_cv_storage_dir(settings: Settings | None = None) -> Path:
    active_settings = settings or get_settings()
    storage_dir = active_settings.generated_cv_storage_dir
    storage_dir.mkdir(parents=True, exist_ok=True)
    return storage_dir


def assert_within_generated_storage(
    candidate_path: Path,
    storage_dir: Path,
) -> None:
    candidate_resolved = candidate_path.resolve()
    storage_resolved = storage_dir.resolve()

    if storage_resolved not in candidate_resolved.parents and (
        candidate_resolved != storage_resolved
    ):
        raise GeneratedCVStorageError(
            "Generated CV path is invalid."
        )


def safe_download_filename(
    candidate_name: str,
    version_id: int,
    artifact_type: str,
) -> str:
    extension = ARTIFACT_EXTENSIONS[artifact_type]
    base = sanitize_filename(candidate_name).lower()

    return (
        f"{base or 'candidate'}-verified-master-cv-"
        f"v{version_id}{extension}"
    )


def hash_file(file_path: Path) -> tuple[int, str]:
    hasher = sha256()
    size = 0

    with file_path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break

            size += len(chunk)
            hasher.update(chunk)

    return size, hasher.hexdigest()


def write_generated_artifact(
    artifact_type: str,
    safe_filename: str,
    writer: Callable[[Path], int | None],
    *,
    settings: Settings | None = None,
) -> StoredGeneratedArtifact:
    if artifact_type not in ARTIFACT_EXTENSIONS:
        raise GeneratedCVStorageError(
            "Generated CV artifact type is not supported."
        )

    active_settings = settings or get_settings()
    storage_dir = get_generated_cv_storage_dir(active_settings)
    extension = ARTIFACT_EXTENSIONS[artifact_type]
    storage_filename = f"{uuid4().hex}{extension}"
    temp_path = storage_dir / f"{uuid4().hex}.tmp{extension}"
    final_path = storage_dir / storage_filename

    assert_within_generated_storage(temp_path, storage_dir)
    assert_within_generated_storage(final_path, storage_dir)

    try:
        page_count = writer(temp_path)

        if not temp_path.exists() or not temp_path.is_file():
            raise GeneratedCVStorageError(
                "Generated CV artifact was not created."
            )

        file_size, digest = hash_file(temp_path)

        if file_size <= 0:
            raise GeneratedCVStorageError(
                "Generated CV artifact is empty."
            )

        if file_size > active_settings.max_generated_cv_file_size_bytes:
            raise GeneratedCVStorageError(
                "Generated CV artifact exceeds the configured maximum size."
            )

        if final_path.exists():
            raise GeneratedCVStorageError(
                "Generated CV artifact storage collision detected."
            )

        temp_path.replace(final_path)

        return StoredGeneratedArtifact(
            artifact_type=artifact_type,
            mime_type=ARTIFACT_MIME_TYPES[artifact_type],
            safe_filename=safe_filename,
            storage_path=storage_filename,
            file_size=file_size,
            sha256=digest,
            page_count=page_count,
        )
    except Exception:
        temp_path.unlink(missing_ok=True)
        final_path.unlink(missing_ok=True)
        raise


def resolve_generated_artifact_path(
    storage_path: str,
    *,
    settings: Settings | None = None,
    require_exists: bool = True,
) -> Path:
    active_settings = settings or get_settings()
    storage_dir = get_generated_cv_storage_dir(active_settings)
    artifact_path = storage_dir / storage_path
    assert_within_generated_storage(artifact_path, storage_dir)

    if artifact_path.exists() and (
        artifact_path.is_symlink() or not artifact_path.is_file()
    ):
        raise GeneratedCVStorageError(
            "Generated CV artifact file was not found."
        )

    if require_exists and not artifact_path.exists():
        raise GeneratedCVStorageError(
            "Generated CV artifact file was not found."
        )

    return artifact_path


def remove_generated_artifact(
    storage_path: str,
    *,
    settings: Settings | None = None,
) -> None:
    artifact_path = resolve_generated_artifact_path(
        storage_path,
        settings=settings,
        require_exists=False,
    )
    artifact_path.unlink(missing_ok=True)
