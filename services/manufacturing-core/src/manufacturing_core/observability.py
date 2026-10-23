"""Internal capability health and structured, credential-free query telemetry."""

import json
import logging
import re
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from manufacturing_core.database import connect_runtime
from manufacturing_core.migrate import TABLES

LOGGER = logging.getLogger("manufacturing_core")


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
        json.dumps(
            {
                "service": "manufacturing-core",
                "correlation_id": correlation_id,
                "operation": operation,
                "outcome": outcome,
                "duration_ms": duration_ms,
            },
            sort_keys=True,
        )
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
