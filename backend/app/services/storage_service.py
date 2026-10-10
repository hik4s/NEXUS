from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Protocol
from uuid import UUID

from app.core.config import settings


class StorageBackend(Protocol):
    name: str
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def presign_get(self, key: str, expires_seconds: int = 900) -> str | None: ...


def _safe_component(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", value)[:180]


def make_storage_key(company_id: UUID, filename: str, digest: str) -> str:
    return f"companies/{company_id}/files/{digest[:16]}-{_safe_component(filename)}"


class LocalStorage:
    name = "local"

    def __init__(self, root: str | None = None) -> None:
        self.root = Path(root or settings.STORAGE_LOCAL_DIR)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.root / key).resolve()
        root = self.root.resolve()
        candidate.relative_to(root)
        return candidate

    def put(self, key: str, data: bytes, content_type: str) -> None:  # noqa: ARG002
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()

    def presign_get(self, key: str, expires_seconds: int = 900) -> str | None:  # noqa: ARG002
        return None


class S3Storage:
    name = "s3"

    def __init__(self) -> None:
        if not settings.S3_BUCKET:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("boto3 is required for S3 storage") from exc
        self.client = boto3.client("s3", region_name=settings.AWS_REGION, endpoint_url=settings.AWS_ENDPOINT_URL or None)
        self.bucket = settings.S3_BUCKET

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def presign_get(self, key: str, expires_seconds: int = 900) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )


def get_storage(backend: str | None = None) -> StorageBackend:
    selected = (backend or settings.STORAGE_BACKEND).lower()
    if selected == "s3":
        return S3Storage()
    return LocalStorage()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
