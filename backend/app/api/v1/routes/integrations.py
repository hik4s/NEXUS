from io import BytesIO
from zipfile import BadZipFile, ZipFile
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.identity.dependencies import require_permission
from app.models.integrations import FileAsset, ImportRun, IntegrationConnection, IntegrationLog
from app.models.user import User
from app.schemas.integrations import FileAssetRead, ImportRunRead, IntegrationCreate, IntegrationLogRead, IntegrationRead
from app.services.b6_service import create_customer_import, store_file
from app.services.integration_service import create_integration, get_integration, health_check, list_integrations
from app.services.storage_service import get_storage
from app.services.job_service import enqueue_job

router = APIRouter(prefix="/integrations")


def _validate_upload(filename: str, content: bytes) -> None:
    if not content:
        raise HTTPException(status_code=422, detail="Uploaded file is empty")
    if len(content) > settings.IMPORT_MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds maximum size of {settings.IMPORT_MAX_BYTES} bytes")
    lower_name = filename.lower()
    if not lower_name.endswith((".csv", ".xlsx")):
        raise HTTPException(status_code=422, detail="Only CSV and XLSX files are supported for imports")
    if lower_name.endswith(".xlsx"):
        if not content.startswith(b"PK\x03\x04"):
            raise HTTPException(status_code=422, detail="Invalid XLSX payload")
        try:
            with ZipFile(BytesIO(content)) as archive:
                total_uncompressed = sum(item.file_size for item in archive.infolist())
                if total_uncompressed > 100 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail="Compressed XLSX expands beyond the allowed limit")
        except BadZipFile as exc:
            raise HTTPException(status_code=422, detail="Invalid XLSX archive") from exc


@router.post("", response_model=IntegrationRead, status_code=status.HTTP_201_CREATED)
def create_integration_route(
    payload: IntegrationCreate,
    request: Request,
    current_user: User = Depends(require_permission("integrations:manage")),
    db: Session = Depends(get_db),
):
    return create_integration(db, current_user, payload, request=request)


@router.get("", response_model=list[IntegrationRead])
def list_integrations_route(
    current_user: User = Depends(require_permission("integrations:read")),
    db: Session = Depends(get_db),
):
    return list_integrations(db, current_user.company_id)


@router.post("/{integration_id}/health", response_model=IntegrationRead)
def health_check_route(
    integration_id: UUID,
    request: Request,
    current_user: User = Depends(require_permission("integrations:manage")),
    db: Session = Depends(get_db),
):
    return health_check(db, current_user, integration_id, request=request)


@router.get("/{integration_id}/logs", response_model=list[IntegrationLogRead])
def list_integration_logs_route(
    integration_id: UUID,
    current_user: User = Depends(require_permission("integrations:read")),
    db: Session = Depends(get_db),
):
    integration = get_integration(db, current_user.company_id, integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Integration not found")
    return list(db.scalars(select(IntegrationLog).where(IntegrationLog.company_id == current_user.company_id, IntegrationLog.integration_id == integration_id).order_by(IntegrationLog.created_at.desc())).all())


@router.post("/files", response_model=FileAssetRead, status_code=status.HTTP_201_CREATED)
def upload_file_route(
    file: UploadFile = File(...),
    current_user: User = Depends(require_permission("integrations:import")),
    db: Session = Depends(get_db),
):
    content = file.file.read(settings.IMPORT_MAX_BYTES + 1)
    _validate_upload(file.filename or "upload", content)
    return store_file(db, current_user, file.filename or "upload", file.content_type or "application/octet-stream", content, {"purpose": "integration_file"})


@router.get("/files/{file_id}", response_model=None)
def download_file_route(
    file_id: UUID,
    current_user: User = Depends(require_permission("integrations:read")),
    db: Session = Depends(get_db),
):
    asset = db.scalar(select(FileAsset).where(FileAsset.id == file_id, FileAsset.company_id == current_user.company_id))
    if asset is None:
        raise HTTPException(status_code=404, detail="File not found")
    data = get_storage(asset.storage_backend).get(asset.storage_key)
    return StreamingResponse(BytesIO(data), media_type=asset.content_type, headers={"Content-Disposition": f'attachment; filename="{asset.filename}"'})


@router.get("/files/{file_id}/url")
def file_download_url_route(
    file_id: UUID,
    expires_seconds: int = Query(default=900, ge=60, le=3600),
    current_user: User = Depends(require_permission("integrations:read")),
    db: Session = Depends(get_db),
):
    asset = db.scalar(select(FileAsset).where(FileAsset.id == file_id, FileAsset.company_id == current_user.company_id))
    if asset is None:
        raise HTTPException(status_code=404, detail="File not found")
    storage = get_storage(asset.storage_backend)
    temporary_url = storage.presign_get(asset.storage_key, expires_seconds=expires_seconds)
    if temporary_url:
        return {"url": temporary_url, "expires_in": expires_seconds, "temporary": True}
    return {"url": f"/api/v1/integrations/files/{asset.id}", "expires_in": None, "temporary": False}


@router.post("/imports/customers", response_model=ImportRunRead, status_code=status.HTTP_201_CREATED)
def import_customers_route(
    request: Request,
    file: UploadFile = File(...),
    dry_run: bool = Query(default=False),
    current_user: User = Depends(require_permission("integrations:import")),
    db: Session = Depends(get_db),
):
    content = file.file.read(settings.IMPORT_MAX_BYTES + 1)
    _validate_upload(file.filename or "customers.csv", content)
    asset = store_file(db, current_user, file.filename or "customers.csv", file.content_type or "application/octet-stream", content, {"purpose": "customer_import"})
    return create_customer_import(db, current_user, asset, dry_run=dry_run)


@router.get("/imports", response_model=list[ImportRunRead])
def list_imports_route(
    current_user: User = Depends(require_permission("integrations:import")),
    db: Session = Depends(get_db),
):
    return list(db.scalars(select(ImportRun).where(ImportRun.company_id == current_user.company_id).order_by(ImportRun.created_at.desc())).all())


@router.post("/automation/playwright", response_model=dict, status_code=status.HTTP_202_ACCEPTED)
def queue_playwright_capture_route(
    payload: dict,
    current_user: User = Depends(require_permission("integrations:automate")),
    db: Session = Depends(get_db),
):
    url = str(payload.get("url", "")).strip()
    if not url:
        raise HTTPException(status_code=422, detail="url is required")
    import_key = str(payload.get("idempotency_key", f"playwright:{current_user.id}:{url}"))
    screenshot_key = payload.get("screenshot_key") or f"companies/{current_user.company_id}/automation/{uuid4().hex}.png"
    job = enqueue_job(
        db,
        company_id=current_user.company_id,
        kind="playwright.capture_page",
        payload={"url": url, "screenshot_key": screenshot_key},
        created_by_user=current_user,
        idempotency_key=import_key,
    )
    return {"job_id": str(job.id), "status": job.status}
