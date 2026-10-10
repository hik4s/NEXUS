from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections import defaultdict
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Final

from fastapi import Request

REQUEST_ID: Final = ContextVar("nexus_request_id", default="-")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": REQUEST_ID.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging() -> None:
    root = logging.getLogger()
    if root.handlers:
        for handler in root.handlers:
            handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
    root.setLevel(logging.INFO)


def new_request_id(candidate: str | None = None) -> str:
    if candidate and len(candidate) <= 64 and all(ch.isalnum() or ch in "-_" for ch in candidate):
        return candidate
    return uuid.uuid4().hex


def bind_request_id(request: Request) -> str:
    value = new_request_id(request.headers.get("X-Request-ID"))
    request.state.request_id = value
    REQUEST_ID.set(value)
    return value


class RequestMetrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests = 0
        self._errors = 0
        self._total_duration_ms = 0.0
        self._by_route: dict[tuple[str, str, int], dict[str, float | int]] = defaultdict(
            lambda: {"requests": 0, "errors": 0, "duration_ms": 0.0}
        )

    def observe(self, method: str, route: str, status_code: int, duration_ms: float) -> None:
        with self._lock:
            self._requests += 1
            self._errors += int(status_code >= 500)
            self._total_duration_ms += duration_ms
            item = self._by_route[(method, route, status_code)]
            item["requests"] += 1
            item["errors"] += int(status_code >= 500)
            item["duration_ms"] += duration_ms

    def prometheus(self) -> str:
        with self._lock:
            lines = [
                "# HELP nexus_http_requests_total Total HTTP requests.",
                "# TYPE nexus_http_requests_total counter",
                f"nexus_http_requests_total {self._requests}",
                "# HELP nexus_http_errors_total Total HTTP 5xx responses.",
                "# TYPE nexus_http_errors_total counter",
                f"nexus_http_errors_total {self._errors}",
                "# HELP nexus_http_request_duration_ms_sum Total request duration in milliseconds.",
                "# TYPE nexus_http_request_duration_ms_sum counter",
                f"nexus_http_request_duration_ms_sum {self._total_duration_ms:.3f}",
            ]
            for (method, route, status), item in sorted(self._by_route.items()):
                labels = f'method="{method}",route="{route}",status="{status}"'
                lines.append(f"nexus_http_route_requests_total{{{labels}}} {int(item['requests'])}")
                lines.append(f"nexus_http_route_duration_ms_sum{{{labels}}} {float(item['duration_ms']):.3f}")
            return "\n".join(lines) + "\n"


metrics = RequestMetrics()
