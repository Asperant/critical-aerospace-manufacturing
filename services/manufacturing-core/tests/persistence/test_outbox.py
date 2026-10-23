"""Outbox primitives on disposable PostgreSQL; no domain-transition proof."""

import json
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest
from conftest import Database
from manufacturing_core.database import connect, connect_runtime
from manufacturing_core.events_v1 import DomainEventV1
from manufacturing_core.migrate import migrate
from manufacturing_core.outbox import OutboxRecord, OutboxRepository
from psycopg import errors
from psycopg.rows import DictRow
from psycopg.types.json import Jsonb
from pydantic import ValidationError

pytestmark = pytest.mark.integration
CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "v1"


def record(name: str = "LotReleased") -> OutboxRecord:
    return OutboxRecord(
        outbox_id="OUTBOX-SYNTHETIC-001",
        event=DomainEventV1.model_validate_json(
            (CONTRACTS / f"domain-event.{name}.json").read_text()
        ),
        created_at=datetime(2026, 10, 23, 12, tzinfo=UTC),
    )


@pytest.mark.parametrize(
    "name",
    [
        "LotReleased",
        "MaterialHoldApplied",
        "QualityExcursionConfirmed",
        "ScheduleActivated",
    ],
)
def test_insert_read_preserves_fact(
    connection: psycopg.Connection[DictRow], name: str
) -> None:
    repo = OutboxRepository(connection)
    original = record(name)
    repo.insert(original)
    assert repo.get(original.outbox_id) == original
    assert repo.get("missing") is None
    row = connection.execute("SELECT * FROM core.outbox").fetchone()
    assert row is not None
    event = original.event.root
    assert row["event_id"] == event.event_id
    assert row["event_type"] == event.event_type
    assert row["aggregate_id"] == event.aggregate_id
    assert row["aggregate_version"] == event.aggregate_version
    assert row["schema_version"] == event.schema_version
    assert row["payload"] == event.payload.model_dump()


@pytest.mark.parametrize("duplicate", ["outbox_id", "event_id"])
def test_duplicate_ids_fail_without_silent_deduplication(
    connection: psycopg.Connection[DictRow], duplicate: str
) -> None:
    repo = OutboxRepository(connection)
    first = record()
    repo.insert(first)
    data = first.model_dump(mode="json")
    if duplicate == "event_id":
        data["outbox_id"] = "OTHER-OUTBOX"
    else:
        data["event"]["event_id"] = "OTHER-EVENT"
    with pytest.raises(errors.UniqueViolation), connection.transaction():
        repo.insert(OutboxRecord.model_validate(data))
    assert repo.get(first.outbox_id) == first
    assert connection.execute("SELECT count(*) AS n FROM core.outbox").fetchone() == {
        "n": 1
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("outbox_id", ""),
        ("created_at", "2026-10-23T12:00:00"),
        ("attempt_count", 1),
        ("last_error", "error"),
        ("publication_status", "PUBLISHED"),
    ],
)
def test_invalid_record_rejected(
    connection: psycopg.Connection[DictRow], field: str, value: object
) -> None:
    data = record().model_dump(mode="json")
    data[field] = value
    with pytest.raises(ValidationError):
        OutboxRepository(connection).insert(OutboxRecord.model_validate(data))
    assert connection.execute("SELECT count(*) AS n FROM core.outbox").fetchone() == {
        "n": 0
    }


@pytest.mark.parametrize(
    "corruption",
    [
        "missing_id",
        "numeric_revision",
        "wrong_version",
        "namespace",
        "binding",
        "payload",
    ],
)
def test_database_constraints_reject_malformed_fact(
    connection: psycopg.Connection[DictRow], corruption: str
) -> None:
    data = json.loads(record().event.model_dump_json())
    if corruption == "missing_id":
        del data["event_id"]
    elif corruption == "numeric_revision":
        data["aggregate_version"] = 42
    elif corruption == "wrong_version":
        data["schema_version"] = "2"
    elif corruption == "namespace":
        data["event_type"] = "simulation.LotReleased"
    elif corruption == "binding":
        data["payload"]["lot_id"] = "OTHER-LOT"
    else:
        data["payload"] = None
    with pytest.raises(errors.IntegrityError), connection.transaction():
        connection.execute(
            "INSERT INTO core.outbox (outbox_id, event, created_at) VALUES (%s, %s, %s)",
            ("BAD", Jsonb(data), record().created_at),
        )


def test_caller_rollback_removes_row(database: Database) -> None:
    original = record()
    with connect_runtime(database.runtime_dsn) as conn:
        with conn.transaction(force_rollback=True):
            OutboxRepository(conn).insert(original)
            assert OutboxRepository(conn).get(original.outbox_id) == original
        assert OutboxRepository(conn).get(original.outbox_id) is None


def test_no_implicit_transaction_or_commit(database: Database) -> None:
    with connect_runtime(database.runtime_dsn) as writer:
        repo = OutboxRepository(writer)
        with pytest.raises(ValueError, match="active caller transaction"):
            repo.insert(record())
        with writer.transaction(force_rollback=True):
            repo.insert(record())
            with connect_runtime(database.runtime_dsn) as reader:
                assert OutboxRepository(reader).get(record().outbox_id) is None


def test_autocommit_insert_rejected(database: Database) -> None:
    with connect_runtime(database.runtime_dsn) as conn:
        conn.autocommit = True
        with pytest.raises(ValueError, match="active caller transaction"):
            OutboxRepository(conn).insert(record())


def test_caller_commit_is_visible_to_another_connection(database: Database) -> None:
    original = record()
    try:
        with connect_runtime(database.runtime_dsn) as writer, writer.transaction():
            OutboxRepository(writer).insert(original)
        with connect_runtime(database.runtime_dsn) as reader:
            assert OutboxRepository(reader).get(original.outbox_id) == original
    finally:
        # Cleanup belongs only to the disposable fixture's migration identity.
        with connect(database.migration_dsn) as conn:
            conn.execute(
                "DELETE FROM core.outbox WHERE outbox_id = %s", (original.outbox_id,)
            )


def test_write_revalidates_unchecked_record(
    connection: psycopg.Connection[DictRow],
) -> None:
    invalid = record().model_copy(update={"outbox_id": " "})
    with pytest.raises(ValidationError):
        OutboxRepository(connection).insert(invalid)
    assert OutboxRepository(connection).get(" ") is None


def test_upgrade_preserves_initial_ledger_and_runtime_grants(
    database: Database,
) -> None:
    # Recreate the pre-0002 state only inside this disposable fixture database.
    with connect(database.migration_dsn) as conn:
        before = conn.execute(
            "SELECT * FROM core.schema_migration WHERE version = '0001_domain'"
        ).fetchone()
        conn.execute("DROP TABLE core.outbox")
        conn.execute("DELETE FROM core.schema_migration WHERE version = '0002_outbox'")
    assert migrate(database.migration_dsn, database.runtime_role) is True
    assert migrate(database.migration_dsn, database.runtime_role) is False
    with connect(database.migration_dsn) as conn:
        assert (
            conn.execute(
                "SELECT * FROM core.schema_migration WHERE version = '0001_domain'"
            ).fetchone()
            == before
        )
    with (
        connect_runtime(database.runtime_dsn) as conn,
        conn.transaction(force_rollback=True),
    ):
        OutboxRepository(conn).insert(record())
        with pytest.raises(errors.InsufficientPrivilege), conn.transaction():
            conn.execute("UPDATE core.outbox SET publication_status = 'PENDING'")
