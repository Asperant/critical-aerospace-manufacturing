"""Internal capability health and structured, credential-free query telemetry."""

import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from cap_observability.health import Check
from cap_observability.health import health_report as build_health_report
from cap_observability.telemetry import Telemetry, configure

from manufacturing_core.database import connect_runtime
from manufacturing_core.migrate import TABLES

LOGGER = logging.getLogger("manufacturing_core")
SERVICE = "manufacturing-core"
SERVICE_VERSION = "0.1.0"
CORRELATION_HEADER = "X-Correlation-Id"
_OUTBOX_PUBLICATION_DELAY: Any = None


def configure_core_telemetry() -> Telemetry:
    """Install standard structured logs and optional OTLP exporters."""
    return configure(SERVICE, SERVICE_VERSION)


def record_outbox_publication_delay(
    created_at: datetime, *, published_at: datetime | None = None
) -> None:
    """Record the committed-row-to-ACK delay estimate without event labels.

    ``created_at`` is written in the same transaction as the outbox row, so it
    precedes commit by only the remainder of that transaction. The measurement
    is therefore a conservative upper bound on commit-to-durable-ACK delay.
    """
    global _OUTBOX_PUBLICATION_DELAY
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("outbox created_at must be timezone-aware")
    end = published_at or datetime.now(UTC)
    if end.tzinfo is None or end.utcoffset() is None:
        raise ValueError("publication time must be timezone-aware")
    if _OUTBOX_PUBLICATION_DELAY is None:
        from opentelemetry import metrics

        _OUTBOX_PUBLICATION_DELAY = metrics.get_meter(SERVICE).create_histogram(
            "core.outbox.publication_delay",
            unit="s",
            description="Outbox row creation to durable broker acknowledgement",
        )
    delay_seconds = max(0.0, (end - created_at).total_seconds())
    _OUTBOX_PUBLICATION_DELAY.record(delay_seconds)


def correlation(value: str | None) -> str:
    if value is None:
        return uuid4().hex
    if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,128}", value):
        raise ValueError("invalid correlation ID")
    return value


def record(
    correlation_id: str, operation: str, outcome: str, duration_ms: float
) -> None:
    LOGGER.info(
        "Core operation",
        extra={
            "event_name": "core.operation",
            "correlation_id": correlation_id,
            "attributes": {
                "operation": operation,
                "outcome": outcome,
                "duration_ms": duration_ms,
            },
        },
    )


def record_transition_rejection(
    correlation_id: str, command_id: str, operation: str, error_code: str
) -> None:
    """Emit safe transition rejection context without domain payloads."""
    LOGGER.info(
        "Core transition rejected",
        extra={
            "event_name": "core.transition_rejected",
            "correlation_id": correlation_id,
            "error_code": error_code,
            "attributes": {
                "command_id": command_id,
                "operation": operation,
                "outcome": "REJECTED",
            },
        },
    )


def record_http_access(
    *,
    correlation_id: str,
    method: str,
    route: str,
    operation_id: str | None,
    status: int,
    duration_ms: float,
) -> None:
    """Log a bounded request summary; request data and query values are omitted."""
    LOGGER.info(
        "HTTP request",
        extra={
            "event_name": "http.request",
            "correlation_id": correlation_id,
            "attributes": {
                "method": method,
                "route": route,
                "operation_id": operation_id,
                "status": status,
                "duration_ms": round(duration_ms, 3),
            },
        },
    )


def core_health_report(
    *,
    environment: str,
    database_status: Literal["READY", "UNAVAILABLE"],
    correlation_id: str,
) -> dict[str, object]:
    """Build the standard readiness document for Core's required database."""
    return build_health_report(
        SERVICE,
        environment,
        [
            Check(
                "postgres-core",
                "dependency",
                "REQUIRED",
                database_status,
                detail="Core runtime database access",
            )
        ],
        correlation_id=correlation_id,
    )


@dataclass(frozen=True)
class CoreHealth:
    status: Literal["READY", "UNAVAILABLE"]
    correlation_id: str


def health(dsn: str, *, correlation_id: str | None = None) -> CoreHealth:
    """Probe real runtime access; READY is not manufacturing/action readiness.

    External callers configure handlers/exporters. No secrets, exception text,
    domain payloads, or connection settings are logged or returned.
    """
    from time import perf_counter

    identity = correlation(correlation_id)
    started = perf_counter()
    status: Literal["READY", "UNAVAILABLE"] = "UNAVAILABLE"
    try:
        with connect_runtime(dsn) as conn, conn.transaction():
            conn.execute("SET TRANSACTION READ ONLY")
            privileges = conn.execute(
                "SELECT pg_catalog.has_table_privilege(current_user, "
                "'core.' || name, 'SELECT') AND pg_catalog.has_table_privilege("
                "current_user, 'core.' || name, 'INSERT') AS allowed "
                "FROM unnest(%s::text[]) AS name",
                (list(TABLES),),
            ).fetchall()
            if len(privileges) == len(TABLES) and all(
                row["allowed"] for row in privileges
            ):
                status = "READY"
    except Exception:
        status = "UNAVAILABLE"
    record(identity, "health", status, (perf_counter() - started) * 1000)
    return CoreHealth(status, identity)
