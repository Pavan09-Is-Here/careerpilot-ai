"""Pluggable object storage for uploaded documents and generated CVs.

Provides a small storage interface with a local-filesystem backend
(the default, matching current behaviour) and an S3 backend for
production deployments. The same path-safety rules apply to both: keys
are validated so they cannot escape the storage root or bucket prefix.

The S3 backend imports boto3 lazily, so the dependency is only required
when object storage is actually configured. Credentials come from the
environment / instance role, never from source.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Protocol

from app.core.config import Settings


_SAFE_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


class StorageError(RuntimeError):
    pass


def validate_key(key: str) -> str:
    """Reject absolute paths, parent traversal, and unsafe characters."""
    if not key or not _SAFE_KEY.match(key):
        raise StorageError("Invalid storage key.")
    if key.startswith("/") or ".." in key.split("/"):
        raise StorageError("Invalid storage key.")
    return key


class StorageBackend(Protocol):
    def save_bytes(self, key: str, data: bytes) -> str: ...

    def read_bytes(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...


class LocalStorageBackend:
    """Filesystem-backed storage rooted at a base directory."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = Path(base_dir)

    def _path(self, key: str) -> Path:
        validate_key(key)
        resolved = (self.base_dir / key).resolve()
        root = self.base_dir.resolve()
        if root != resolved and root not in resolved.parents:
            raise StorageError("Resolved path escapes storage root.")
        return resolved

    def save_bytes(self, key: str, data: bytes) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read_bytes(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise StorageError("Object not found.")
        return path.read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.is_file():
            path.unlink()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()


class S3StorageBackend:
    """S3 (or S3-compatible) storage. Requires boto3 at construction."""

    def __init__(
        self,
        *,
        bucket: str,
        region: str | None = None,
        prefix: str = "",
        endpoint_url: str | None = None,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - env dependent
            raise StorageError(
                "S3 storage requires the 'boto3' package to be "
                "installed."
            ) from exc

        if not bucket:
            raise StorageError("S3 storage requires a bucket name.")

        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._client = boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
        )

    def _object_key(self, key: str) -> str:
        validate_key(key)
        return f"{self.prefix}/{key}" if self.prefix else key

    def save_bytes(self, key: str, data: bytes) -> str:
        self._client.put_object(
            Bucket=self.bucket,
            Key=self._object_key(key),
            Body=data,
        )
        return key

    def read_bytes(self, key: str) -> bytes:
        response = self._client.get_object(
            Bucket=self.bucket,
            Key=self._object_key(key),
        )
        return response["Body"].read()

    def delete(self, key: str) -> None:
        self._client.delete_object(
            Bucket=self.bucket,
            Key=self._object_key(key),
        )

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(
                Bucket=self.bucket,
                Key=self._object_key(key),
            )
            return True
        except Exception:  # noqa: BLE001 - any error means "not present"
            return False


def get_storage_backend(
    settings: Settings | None = None,
) -> StorageBackend:
    settings = settings or Settings()

    if settings.storage_backend == "s3":
        return S3StorageBackend(
            bucket=settings.s3_bucket or "",
            region=settings.s3_region,
            prefix=settings.s3_prefix,
            endpoint_url=settings.s3_endpoint_url,
        )

    if settings.storage_backend == "local":
        return LocalStorageBackend(settings.document_storage_dir)

    raise StorageError(
        f"Unknown storage backend '{settings.storage_backend}'."
    )
