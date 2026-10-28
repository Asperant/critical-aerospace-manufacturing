"""Structured access logging with correlation ids, and the health surface body.

One JSON object per request on the ``operations_bff.access`` logger: method,
route template, operation, status, outcome, duration and the correlation id that
is also returned to the caller and passed to every read port. Query strings,
cookies, headers and bodies are never logged.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from typing import Any, TextIO

ACCESS_LOGGER = "operations_bff.access"
CORRELATION_HEADER = "X-Correlation-Id"
SERVICE = "operations-bff"


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def outcome_of(status: int) -> str:
    if status >= 500:
        return "server_error"
    if status >= 400:
        return "client_error"
    return "success"


def access_record(
    *,
    method: str,
    route: str,
    operation_id: str | None,
    status: int,
    duration_ms: float,
    correlation_id: str,
) -> dict[str, Any]:
    return {
        "event": "http_request",
        "service": SERVICE,
        "method": method,
        "route": route,
        "operation_id": operation_id,
        "status": status,
        "outcome": outcome_of(status),
        "duration_ms": round(duration_ms, 3),
        "correlation_id": correlation_id,
    }


def log_access(record: dict[str, Any]) -> None:
    logging.getLogger(ACCESS_LOGGER).info(
        json.dumps(record, sort_keys=True, separators=(",", ":"))
    )


def configure_access_log(stream: TextIO | None = None) -> None:
    """Send access records to stdout as bare JSON lines (idempotent)."""
    logger = logging.getLogger(ACCESS_LOGGER)
    if any(getattr(h, "_operations_bff", False) for h in logger.handlers):
        return
    handler = logging.StreamHandler(stream or sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler._operations_bff = True  # type: ignore[attr-defined]
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def health_body(
    *, login: bool, overview: bool, facility_state: bool = False
) -> dict[str, Any]:
    """Process and configuration health. It makes no backend or provider call."""
    return {
        "service": SERVICE,
        "status": "ok",
        "capabilities": {
            "session": "ready",
            "login": "enabled" if login else "disabled",
            "overview": "enabled" if overview else "disabled",
            "facility_state": "enabled" if facility_state else "disabled",
        },
    }
