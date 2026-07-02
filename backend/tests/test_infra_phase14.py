"""Phase 14 — deployment groundwork tests.

Covers configurable database URL resolution, the storage backend
abstraction (local + factory selection), and the health endpoint's
environment/database reporting. No infrastructure is provisioned here.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.database import (
    DEFAULT_SQLITE_URL,
    _is_sqlite,
    resolve_database_url,
)
from app.services.storage_backend import (
    LocalStorageBackend,
    S3StorageBackend,
    StorageError,
    get_storage_backend,
    validate_key,
)


# --- Database URL resolution ----------------------------------------------


def test_default_database_url_is_sqlite() -> None:
    assert resolve_database_url(Settings(database_url=None)) == (
        DEFAULT_SQLITE_URL
    )
    assert _is_sqlite(DEFAULT_SQLITE_URL)


def test_configured_postgres_url_is_used() -> None:
    url = "postgresql+psycopg://user:pass@localhost:5432/careerpilot"
    resolved = resolve_database_url(Settings(database_url=url))
    assert resolved == url
    assert _is_sqlite(resolved) is False


# --- Storage backend ------------------------------------------------------


def test_local_storage_roundtrip(tmp_path: Path) -> None:
    backend = LocalStorageBackend(tmp_path)
    key = "documents/abc123.pdf"

    assert backend.exists(key) is False
    backend.save_bytes(key, b"hello")
    assert backend.exists(key) is True
    assert backend.read_bytes(key) == b"hello"

    backend.delete(key)
    assert backend.exists(key) is False


def test_local_storage_rejects_traversal(tmp_path: Path) -> None:
    backend = LocalStorageBackend(tmp_path)
    with pytest.raises(StorageError):
        backend.save_bytes("../escape.txt", b"x")
    with pytest.raises(StorageError):
        backend.save_bytes("/etc/passwd", b"x")


def test_validate_key_rejects_bad_keys() -> None:
    validate_key("a/b/c.pdf")
    for bad in ("", "../x", "/abs", "a/../b", "a b.pdf"):
        with pytest.raises(StorageError):
            validate_key(bad)


def test_factory_returns_local_by_default(tmp_path: Path) -> None:
    backend = get_storage_backend(
        Settings(
            storage_backend="local",
            document_storage_dir=tmp_path,
        )
    )
    assert isinstance(backend, LocalStorageBackend)


def test_factory_unknown_backend_raises() -> None:
    with pytest.raises(StorageError):
        get_storage_backend(Settings(storage_backend="floppy"))


def test_s3_backend_requires_bucket() -> None:
    # Either boto3 is missing (StorageError) or the empty bucket is
    # rejected (StorageError) — both surface as StorageError.
    with pytest.raises(StorageError):
        S3StorageBackend(bucket="")


# --- Health endpoint ------------------------------------------------------


def test_health_reports_environment_and_database(
    client: TestClient,
) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["environment"] == "development"
    assert body["database"] == "sqlite"
