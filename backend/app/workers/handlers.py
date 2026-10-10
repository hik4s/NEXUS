from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.services.notification_service import create_notification
from app.services.import_service import run_customer_import
from app.automation.playwright_executor import capture_page_sync


Handler = Callable[[Session, dict[str, Any]], dict[str, Any]]


def noop_handler(_: Session, payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "payload": payload}


def create_notification_handler(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    notification = create_notification(
        db,
        company_id=UUID(payload["company_id"]),
        user_id=UUID(payload["user_id"]),
        title=payload["title"],
        body=payload["body"],
        notification_type=payload.get("notification_type", "system"),
        severity=payload.get("severity", "info"),
        action_url=payload.get("action_url"),
    )
    return {"notification_id": str(notification.id)}

def import_customers_handler(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    run = run_customer_import(db, UUID(payload["import_run_id"]))
    return {"import_run_id": str(run.id), "status": run.status, "imported_rows": run.imported_rows, "error_rows": run.error_rows}


def playwright_capture_handler(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    # Playwright always runs inside the worker, never in the HTTP process.
    result = capture_page_sync(payload["url"], screenshot_key=payload.get("screenshot_key"))
    return result


HANDLERS: dict[str, Handler] = {
    "noop": noop_handler,
    "notification.create": create_notification_handler,
    "import.customers": import_customers_handler,
    "playwright.capture_page": playwright_capture_handler,
}
