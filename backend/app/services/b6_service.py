from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.integrations import FileAsset, ImportRun
from app.models.user import User
from app.services.import_service import run_customer_import
from app.services.job_service import enqueue_job
from app.services.storage_service import get_storage, make_storage_key, sha256_bytes


def store_file(db: Session, actor: User, filename: str, content_type: str, data: bytes, metadata: dict | None = None) -> FileAsset:
    if not filename or len(filename) > 255:
        raise HTTPException(status_code=422, detail="Invalid filename")
    digest = sha256_bytes(data)
    storage = get_storage()
    key = make_storage_key(actor.company_id, filename, digest)
    storage.put(key, data, content_type)
    asset = FileAsset(company_id=actor.company_id, created_by_user_id=actor.id, filename=filename, storage_backend=storage.name, storage_key=key, content_type=content_type or "application/octet-stream", size_bytes=len(data), sha256=digest, metadata_json=metadata or {})
    db.add(asset); db.commit(); db.refresh(asset)
    return asset


def create_customer_import(db: Session, actor: User, asset: FileAsset, dry_run: bool = False) -> ImportRun:
    run = ImportRun(company_id=actor.company_id, created_by_user_id=actor.id, file_asset_id=asset.id, entity="customers", mode="dry_run" if dry_run else "import", status="queued")
    db.add(run); db.commit(); db.refresh(run)
    if dry_run:
        return run_customer_import(db, run.id)
    job = enqueue_job(db, company_id=actor.company_id, kind="import.customers", payload={"import_run_id": str(run.id)}, created_by_user=actor, enqueue_external=False, idempotency_key=f"import:{run.id}")
    run.job_id = job.id
    db.commit(); db.refresh(run)
    return run
