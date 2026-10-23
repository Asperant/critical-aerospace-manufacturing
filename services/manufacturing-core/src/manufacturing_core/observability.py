"""Internal capability health and structured, credential-free query telemetry."""

import json
import logging
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

import psycopg
from psycopg.rows import DictRow

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


@dataclass(frozen=True)
class OutboxPendingAge:
    as_of: datetime
    pending_count: int
    oldest_pending_age_seconds: float | None


def outbox_pending_age(
    connection: psycopg.Connection[DictRow],
    *,
    as_of: datetime,
    correlation_id: str | None = None,
) -> OutboxPendingAge:
    """Read caller snapshot; pending age is not measured broker publication delay.

    No clock sampling, transaction completion, publication or state mutation.
    Empty backlog has no oldest age. Future creation times fail explicitly.
    """
    identity = correlation(correlation_id)
    if as_of.tzinfo is None or as_of.utcoffset() is None:
        raise ValueError("outbox age requires timezone-aware as_of")
    reference = as_of.astimezone(UTC)
    try:
        row = connection.execute(
            "SELECT count(*) AS pending_count, min(created_at) AS oldest, "
            "max(created_at) AS newest FROM core.outbox "
            "WHERE publication_status = 'PENDING'"
        ).fetchone()
        if row is None:
            raise ValueError("outbox aggregate result unavailable")
        if row["newest"] is not None and row["newest"] > reference:
            raise ValueError("outbox creation time is after as_of")
        result = OutboxPendingAge(
            as_of=reference,
            pending_count=row["pending_count"],
            oldest_pending_age_seconds=(
                None
                if row["oldest"] is None
                else (reference - row["oldest"]).total_seconds()
            ),
        )
    except Exception:
        # A failed read never becomes a healthy zero backlog; no exception/DSN dump.
        LOGGER.info(
            json.dumps(
                {
                    "service": "manufacturing-core",
                    "operation": "outbox-pending-age",
                    "correlation_id": identity,
                    "outcome": "FAILED",
                },
                sort_keys=True,
            )
        )
        raise
    LOGGER.info(
        json.dumps(
            {
                "service": "manufacturing-core",
                "operation": "outbox-pending-age",
                "correlation_id": identity,
                "outcome": "COMPLETED",
                "as_of": result.as_of.isoformat(),
                "pending_count": result.pending_count,
                "oldest_pending_age_seconds": result.oldest_pending_age_seconds,
            },
            sort_keys=True,
        )
    )
    return result


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
