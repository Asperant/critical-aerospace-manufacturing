"""Standard access telemetry, correlation ids, and process health reporting.

Only method, route template, operation, status, outcome, duration and the
correlation id are logged. Query strings, cookies, headers and bodies are never
logged.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from cap_observability.health import Check, health_report
from cap_observability.telemetry import resource_from_env

ACCESS_LOGGER = "operations_bff.access"
CORRELATION_HEADER = "X-Correlation-Id"
SERVICE = "operations-bff"
SERVICE_VERSION = "0.1.0"


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
        "HTTP request",
        extra={
            "event_name": "http.request",
            "correlation_id": record["correlation_id"],
            "attributes": {
                key: value
                for key, value in record.items()
                if key not in {"event", "service", "correlation_id"}
            },
        },
    )


def configure_access_log() -> None:
    """Route access records through the shared root telemetry handlers."""
    logger = logging.getLogger(ACCESS_LOGGER)
    logger.setLevel(logging.INFO)
    logger.propagate = True


def health_body(
    *,
    environment: str,
    login: bool,
    overview: bool,
    facility_state: bool = False,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Standard process and capability health; makes no backend/provider call."""
    checks = [Check("session", "readiness", "REQUIRED", "READY")]
    checks.extend(
        Check(
            name,
            "capability",
            "OPTIONAL",
            "READY" if enabled else "UNAVAILABLE",
            detail="enabled" if enabled else "disabled",
        )
        for name, enabled in (
            ("login", login),
            ("overview", overview),
            ("facility_state", facility_state),
        )
    )
    return health_report(
        SERVICE,
        environment,
        checks,
        correlation_id=correlation_id,
    )


def health_environment() -> str:
    """Return the same validated environment identity used by telemetry."""
    import os

    return resource_from_env(SERVICE, SERVICE_VERSION, os.environ)[
        "deployment.environment.name"
    ]
