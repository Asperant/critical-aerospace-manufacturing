"""Pending age from real persisted timestamps; never broker-delay evidence."""

import json
import logging
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import psycopg
import pytest
from conftest import Database
from manufacturing_core.database import connect
from manufacturing_core.events_v1 import DomainEventV1
from manufacturing_core.observability import outbox_pending_age
from manufacturing_core.outbox import OutboxRecord, OutboxRepository
from psycopg.rows import DictRow

pytestmark = pytest.mark.integration
AS_OF = datetime(2026, 10, 23, 12, tzinfo=UTC)
FIXTURE = (
    Path(__file__).resolve().parents[2] / "contracts/v1/domain-event.LotReleased.json"
)


def insert(connection: psycopg.Connection[DictRow], index: int, age: float) -> None:
    data = json.loads(FIXTURE.read_text())
    data["event_id"] = f"AGE-EVENT-{index}"
    OutboxRepository(connection).insert(
        OutboxRecord(
            outbox_id=f"AGE-OUTBOX-{index}",
            event=DomainEventV1.model_validate(data),
            created_at=AS_OF - timedelta(seconds=age),
        )
    )


@pytest.mark.parametrize(
    "ages,expected", [([], None), ([3.25], 3.25), ([2.0, 9.5, 1.0], 9.5), ([0.0], 0.0)]
)
def test_pending_age_and_deterministic_reference(
    connection: psycopg.Connection[DictRow],
    ages: list[float],
    expected: float | None,
    caplog: pytest.LogCaptureFixture,
) -> None:
    for index, age in enumerate(ages):
        insert(connection, index, age)
    with caplog.at_level(logging.INFO, logger="manufacturing_core"):
        first = outbox_pending_age(connection, as_of=AS_OF, correlation_id="age-1")
        second = outbox_pending_age(connection, as_of=AS_OF, correlation_id="age-1")
    assert first == second
    assert first.pending_count == len(ages)
    assert first.oldest_pending_age_seconds == expected
    assert first.as_of == AS_OF
    log = json.loads(caplog.records[-1].message)
    assert log == {
        "service": "manufacturing-core",
        "operation": "outbox-pending-age",
        "correlation_id": "age-1",
        "outcome": "COMPLETED",
        "as_of": AS_OF.isoformat(),
        "pending_count": len(ages),
        "oldest_pending_age_seconds": expected,
    }
    later = outbox_pending_age(connection, as_of=AS_OF + timedelta(seconds=1))
    assert later.oldest_pending_age_seconds == (
        None if expected is None else expected + 1
    )


def test_timezone_equivalent_reference(connection: psycopg.Connection[DictRow]) -> None:
    insert(connection, 0, 2.5)
    assert outbox_pending_age(connection, as_of=AS_OF) == outbox_pending_age(
        connection, as_of=AS_OF.astimezone(timezone(timedelta(hours=3)))
    )


def test_naive_reference_rejected(connection: psycopg.Connection[DictRow]) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        outbox_pending_age(connection, as_of=AS_OF.replace(tzinfo=None))


def test_future_timestamp_is_not_hidden_by_older_row(
    connection: psycopg.Connection[DictRow],
    caplog: pytest.LogCaptureFixture,
) -> None:
    insert(connection, 0, 10)
    insert(connection, 1, -1)
    with (
        caplog.at_level(logging.INFO, logger="manufacturing_core"),
        pytest.raises(ValueError, match="after as_of"),
    ):
        outbox_pending_age(connection, as_of=AS_OF, correlation_id="age-future")
    log = json.loads(caplog.records[-1].message)
    assert log["outcome"] == "FAILED"
    assert "pending_count" not in log


@pytest.mark.parametrize("with_pending", [False, True])
def test_published_rows_excluded(database: Database, with_pending: bool) -> None:
    # Future-state fixture only: production schema remains pending-only.
    # Both the constraint relaxation and published row are rolled back together.
    with connect(database.migration_dsn) as conn, conn.transaction(force_rollback=True):
        conn.execute(
            "ALTER TABLE core.outbox DROP CONSTRAINT outbox_publication_status_check"
        )
        insert(conn, 0, 100)
        conn.execute("UPDATE core.outbox SET publication_status = 'PUBLISHED'")
        if with_pending:
            insert(conn, 1, 2)
        result = outbox_pending_age(conn, as_of=AS_OF)
        assert result.pending_count == (1 if with_pending else 0)
        assert result.oldest_pending_age_seconds == (2 if with_pending else None)


def test_database_failure_is_not_empty_backlog(
    connection: psycopg.Connection[DictRow],
    caplog: pytest.LogCaptureFixture,
) -> None:
    connection.close()
    with (
        caplog.at_level(logging.INFO, logger="manufacturing_core"),
        pytest.raises(psycopg.OperationalError),
    ):
        outbox_pending_age(connection, as_of=AS_OF, correlation_id="age-failed")
    log = json.loads(caplog.records[-1].message)
    assert log["outcome"] == "FAILED"
    assert "oldest_pending_age_seconds" not in log
