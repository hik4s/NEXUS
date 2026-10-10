from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.integrations import FileAsset, ImportRun, IntegrationConnection
from app.services.import_service import validate_customer_rows


def register(client, suffix: str):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"B6 Company {suffix}",
            "company_slug": f"b6-company-{suffix}",
            "full_name": "B6 Owner",
            "email": f"owner-{suffix}@example.com",
            "password": "StrongPass123!",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def auth(token: str):
    return {"Authorization": f"Bearer {token}"}


def test_integration_credentials_are_encrypted_and_status_is_audited(tmp_path, monkeypatch):
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = auth(owner["access_token"])
        response = client.post(
            "/api/v1/integrations",
            headers=headers,
            json={
                "provider": "legacy_portal",
                "name": "Legacy ERP",
                "credentials": {"username": "demo", "password": "super-secret"},
                "config": {"tenant": "demo"},
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["credential_fingerprint"]
        assert "super-secret" not in response.text

        with SessionLocal() as db:
            model = db.scalar(select(IntegrationConnection).where(IntegrationConnection.id == UUID(body["id"])))
            assert model is not None
            assert model.encrypted_credentials
            assert "super-secret" not in model.encrypted_credentials
            assert model.status == "configured"

        health = client.post(f"/api/v1/integrations/{body['id']}/health", headers=headers)
        assert health.status_code == 200
        assert health.json()["status"] == "configured"


def test_file_upload_download_and_company_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_LOCAL_DIR", str(tmp_path / "storage"))
    suffix = uuid4().hex[:8]
    other_suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        other = register(client, other_suffix)
        headers = auth(owner["access_token"])
        other_headers = auth(other["access_token"])

        upload = client.post(
            "/api/v1/integrations/files",
            headers=headers,
            files={"file": ("hello.csv", b"name,email\nAlice,alice@example.com\n", "text/csv")},
        )
        assert upload.status_code == 201, upload.text
        asset = upload.json()
        assert asset["storage_backend"] == "local"

        download = client.get(f"/api/v1/integrations/files/{asset['id']}", headers=headers)
        assert download.status_code == 200
        assert download.content.startswith(b"name,email")

        file_url = client.get(f"/api/v1/integrations/files/{asset['id']}/url", headers=headers)
        assert file_url.status_code == 200
        assert file_url.json()["temporary"] is False

        forbidden = client.get(f"/api/v1/integrations/files/{asset['id']}", headers=other_headers)
        assert forbidden.status_code == 404


def test_customer_import_dry_run_reports_invalid_rows():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = auth(owner["access_token"])
        csv_data = b"name,email\nGood,good@example.com\n,Bad@Example.com\nOther,not-an-email\n"
        response = client.post(
            "/api/v1/integrations/imports/customers?dry_run=true",
            headers=headers,
            files={"file": ("customers.csv", csv_data, "text/csv")},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["mode"] == "dry_run"
        assert body["status"] == "completed"
        assert body["total_rows"] == 3
        assert body["valid_rows"] == 1
        assert body["error_rows"] == 2


def test_customer_import_queues_job_then_imports_rows():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = auth(owner["access_token"])
        csv_data = b"name,email,source\nImported One,one@example.com,legacy\nImported Two,two@example.com,legacy\n"
        response = client.post(
            "/api/v1/integrations/imports/customers",
            headers=headers,
            files={"file": ("customers.csv", csv_data, "text/csv")},
        )
        assert response.status_code == 201, response.text
        run = response.json()
        assert run["status"] == "queued"
        assert run["job_id"]

        execute = client.post(f"/api/v1/async/jobs/{run['job_id']}/run", headers=headers)
        assert execute.status_code == 200, execute.text
        assert execute.json()["status"] == "succeeded"

        with SessionLocal() as db:
            stored = db.get(ImportRun, UUID(run["id"]))
            assert stored is not None
            assert stored.status == "completed"
            assert stored.imported_rows == 2
            assert db.scalar(select(FileAsset).where(FileAsset.id == stored.file_asset_id)) is not None


def test_xlsx_customer_rows_are_supported():
    try:
        from openpyxl import Workbook
    except ImportError:
        return
    buffer = __import__("io").BytesIO()
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["name", "email"])
    sheet.append(["XLSX Customer", "xlsx@example.com"])
    workbook.save(buffer)
    from app.services.import_service import _rows_from_bytes
    rows = list(_rows_from_bytes("customers.xlsx", buffer.getvalue()))
    valid, errors = validate_customer_rows(rows)
    assert errors == []
    assert valid[0]["name"] == "XLSX Customer"


def test_playwright_job_endpoint_is_async_and_does_not_execute_in_http_process():
    suffix = uuid4().hex[:8]
    with TestClient(app) as client:
        owner = register(client, suffix)
        headers = auth(owner["access_token"])
        response = client.post(
            "/api/v1/integrations/automation/playwright",
            headers=headers,
            json={"url": "https://example.com", "idempotency_key": f"pw-{suffix}"},
        )
        assert response.status_code == 202, response.text
        body = response.json()
        assert body["job_id"]
        with SessionLocal() as db:
            from app.models.async_jobs import BackgroundJob
            job = db.get(BackgroundJob, UUID(body["job_id"]))
            assert job.kind == "playwright.capture_page"
            assert job.status == "queued"


def test_playwright_url_validation_happens_before_browser_import():
    from app.automation.playwright_executor import capture_page_sync
    try:
        capture_page_sync("file:///etc/passwd")
    except ValueError as exc:
        assert "http(s)" in str(exc)
    else:
        raise AssertionError("Expected URL validation to fail")


def test_storage_backend_selection_and_s3_configuration_failure(monkeypatch, tmp_path):
    from app.services.storage_service import get_storage
    monkeypatch.setattr("app.services.storage_service.settings.STORAGE_BACKEND", "local")
    monkeypatch.setattr("app.services.storage_service.settings.STORAGE_LOCAL_DIR", str(tmp_path / "storage"))
    assert get_storage().name == "local"
    monkeypatch.setattr("app.services.storage_service.settings.STORAGE_BACKEND", "s3")
    monkeypatch.setattr("app.services.storage_service.settings.S3_BUCKET", "")
    try:
        get_storage()
    except RuntimeError as exc:
        assert "S3_BUCKET" in str(exc)
    else:
        raise AssertionError("Expected missing S3 configuration to fail fast")
