from __future__ import annotations

import asyncio
from urllib.parse import urlparse

from app.core.config import settings
from app.services.storage_service import get_storage


def _allowed_host(host: str) -> bool:
    raw = [item.strip().lower() for item in settings.PLAYWRIGHT_ALLOWED_HOSTS.split(",") if item.strip()]
    return not raw or host.lower() in raw


async def capture_page(url: str, screenshot_key: str | None = None) -> dict:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Playwright URL must be http(s)")
    if not _allowed_host(parsed.hostname):
        raise ValueError(f"Host is not allowed: {parsed.hostname}")
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("playwright is not installed") from exc

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=settings.PLAYWRIGHT_TIMEOUT_MS)
            title = await page.title()
            result = {"url": page.url, "title": title, "status_code": response.status if response else None}
            if screenshot_key:
                image = await page.screenshot(full_page=True)
                get_storage().put(screenshot_key, image, "image/png")
                result["screenshot_key"] = screenshot_key
            return result
        except Exception as exc:
            # Capture best-effort diagnostic evidence before the worker reports failure.
            if screenshot_key:
                try:
                    image = await page.screenshot(full_page=True)
                    get_storage().put(screenshot_key, image, "image/png")
                except Exception:
                    pass
            detail = f"Playwright task failed: {exc}"
            if screenshot_key:
                detail += f"; screenshot_key={screenshot_key}"
            raise RuntimeError(detail) from exc
        finally:
            await browser.close()


def capture_page_sync(url: str, screenshot_key: str | None = None) -> dict:
    return asyncio.run(capture_page(url, screenshot_key=screenshot_key))
