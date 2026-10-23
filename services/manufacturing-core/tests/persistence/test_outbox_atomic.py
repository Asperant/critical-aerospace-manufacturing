"""Generic atomic mutation + outbox boundary on disposable PostgreSQL.

The mutation is a test-owned neutral probe table in a test-owned schema; the event
is a synthetic contract fixture. No lifecycle, command, revision or ReleaseLot
semantics are exercised, so this is NOT the canonical transition atomicity proof.
"""

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path

import psycopg
import pytest
from conftest import Database
from manufacturing_core.database import connect_runtime
from manufacturing_core.events_v1 import DomainEventV1
from manufacturing_core.outbox import (
    OutboxRecord,
    OutboxRepository,
    execute_with_outbox,
)
from psycopg import errors, sql
from psycopg.rows import DictRow
from pydantic import ValidationError

pytestmark = pytest.mark.integration
CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "v1"
SCHEMA = "atomic_probe"
Connection = psycopg.Connection[DictRow]


def fact(tag: str) -> OutboxRecord:
    raw = json.loads((CONTRACTS / "domain-event.ScheduleActivated.json").read_text())
    raw["event_id"] = f"EVENT-ATOMIC-PROBE-{tag}"
    return OutboxRecord(
        outbox_id=f"OUTBOX-ATOMIC-PROBE-{tag}",
        event=DomainEventV1.model_validate(raw),
        created_at=datetime(2026, 10, 23, 12, tzinfo=UTC),
    )


def write(probe_id: str) -> Callable[[Connection], str]:
    def mutation(conn: Connection) -> str:
        conn.execute(
            sql.SQL("INSERT INTO {}.mutation_probe (probe_id) VALUES (%s)").format(
                sql.Identifier(SCHEMA)
            ),
            (probe_id,),
        )
        return probe_id

    return mutation


def probes(conn: Connection) -> list[str]:
    rows = conn.execute(
        sql.SQL("SELECT probe_id FROM {}.mutation_probe ORDER BY probe_id").format(
            sql.Identifier(SCHEMA)
        )
    ).fetchall()
    return [row["probe_id"] for row in rows]


def facts(conn: Connection) -> list[str]:
    rows = conn.execute(
        "SELECT outbox_id FROM core.outbox WHERE outbox_id LIKE 'OUTBOX-ATOMIC-PROBE-%' "
        "ORDER BY outbox_id"
    ).fetchall()
    return [row["outbox_id"] for row in rows]


def state(conn: Connection) -> tuple[list[str], list[str]]:
    return probes(conn), facts(conn)


@pytest.fixture
def probe(database: Database) -> Iterator[Database]:
    """Test-owned persistence fixture, created and removed by the disposable admin."""
    schema = sql.Identifier(SCHEMA)
    with psycopg.connect(database.admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(schema))
        admin.execute(sql.SQL("CREATE SCHEMA {}").format(schema))
        admin.execute(
            sql.SQL(
                "CREATE TABLE {}.mutation_probe (probe_id text PRIMARY KEY)"
            ).format(schema)
        )
        admin.execute(
            sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(
                schema, sql.Identifier(database.runtime_role)
            )
        )
        admin.execute(
            sql.SQL("GRANT SELECT, INSERT ON {}.mutation_probe TO {}").format(
                schema, sql.Identifier(database.runtime_role)
            )
        )
        try:
            yield database
        finally:
            admin.execute(
                "DELETE FROM core.outbox WHERE outbox_id LIKE 'OUTBOX-ATOMIC-PROBE-%'"
            )
            admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(schema))


def committed(database: Database) -> tuple[list[str], list[str]]:
    with connect_runtime(database.runtime_dsn) as reader:
        return state(reader)


def test_commit_persists_mutation_and_outbox_together(probe: Database) -> None:
    with connect_runtime(probe.runtime_dsn) as writer, writer.transaction():
        assert execute_with_outbox(writer, write("P-1"), fact("1")) == "P-1"
        assert state(writer) == (["P-1"], ["OUTBOX-ATOMIC-PROBE-1"])
        assert committed(probe) == ([], [])  # nothing visible before the commit
    assert committed(probe) == (["P-1"], ["OUTBOX-ATOMIC-PROBE-1"])
    with connect_runtime(probe.runtime_dsn) as reader:
        assert OutboxRepository(reader).get("OUTBOX-ATOMIC-PROBE-1") == fact("1")


@pytest.mark.parametrize("failure", ["python", "sql"])
def test_mutation_failure_leaves_no_outbox_row(probe: Database, failure: str) -> None:
    def failing(conn: Connection) -> str:
        write("P-2")(conn)
        if failure == "python":
            raise RuntimeError("mutation failed after writing")
        return write("P-2")(conn)  # duplicate primary key

    expected = RuntimeError if failure == "python" else errors.UniqueViolation
    with connect_runtime(probe.runtime_dsn) as writer, writer.transaction():
        write("P-KEEP")(writer)  # caller work before the unit survives
        with pytest.raises(expected):
            execute_with_outbox(writer, failing, fact("2"))
        # The caller's transaction is still usable and holds only its own work.
        assert state(writer) == (["P-KEEP"], [])
    assert committed(probe) == (["P-KEEP"], [])


@pytest.mark.parametrize("duplicate", ["outbox_id", "event_id"])
def test_outbox_failure_rolls_back_the_mutation(
    probe: Database, duplicate: str
) -> None:
    existing = fact("3")
    clash = fact("3-clash")
    if duplicate == "outbox_id":
        clash = OutboxRecord(
            outbox_id=existing.outbox_id,
            event=clash.event,
            created_at=clash.created_at,
        )
    else:
        clash = OutboxRecord(
            outbox_id=clash.outbox_id, event=existing.event, created_at=clash.created_at
        )
    with connect_runtime(probe.runtime_dsn) as writer, writer.transaction():
        OutboxRepository(writer).insert(existing)
        with pytest.raises(errors.UniqueViolation):
            execute_with_outbox(writer, write("P-3"), clash)
        assert state(writer) == ([], ["OUTBOX-ATOMIC-PROBE-3"])
    assert committed(probe) == ([], ["OUTBOX-ATOMIC-PROBE-3"])


def test_caller_rollback_removes_both(probe: Database) -> None:
    with connect_runtime(probe.runtime_dsn) as writer:
        with writer.transaction(force_rollback=True):
            execute_with_outbox(writer, write("P-4"), fact("4"))
            assert state(writer) == (["P-4"], ["OUTBOX-ATOMIC-PROBE-4"])
        assert state(writer) == ([], [])
    assert committed(probe) == ([], [])


def test_record_may_be_formed_from_the_mutation_result(probe: Database) -> None:
    seen: list[str] = []

    def form(result: str) -> OutboxRecord:
        seen.append(result)
        return fact("5")

    with connect_runtime(probe.runtime_dsn) as writer, writer.transaction():
        assert execute_with_outbox(writer, write("P-5"), form) == "P-5"
    assert seen == ["P-5"]
    assert committed(probe) == (["P-5"], ["OUTBOX-ATOMIC-PROBE-5"])


def test_record_formation_failure_rolls_back_the_mutation(probe: Database) -> None:
    def broken(_: str) -> OutboxRecord:
        raise ValueError("event could not be formed")

    with connect_runtime(probe.runtime_dsn) as writer, writer.transaction():
        with pytest.raises(ValueError, match="could not be formed"):
            execute_with_outbox(writer, write("P-6"), broken)
        assert state(writer) == ([], [])
    assert committed(probe) == ([], [])


def test_invalid_record_is_rejected_before_the_mutation_runs(probe: Database) -> None:
    calls: list[str] = []

    def mutation(conn: Connection) -> str:
        calls.append("ran")
        return write("P-7")(conn)

    unchecked = OutboxRecord.model_construct(
        outbox_id="", event=fact("7").event, created_at=fact("7").created_at
    )
    with (
        connect_runtime(probe.runtime_dsn) as writer,
        writer.transaction(force_rollback=True),
    ):
        with pytest.raises(ValidationError):
            execute_with_outbox(writer, mutation, unchecked)
        assert state(writer) == ([], [])
    assert calls == []


def test_requires_an_active_caller_transaction(probe: Database) -> None:
    calls: list[str] = []

    def mutation(conn: Connection) -> str:
        calls.append("ran")
        return write("P-8")(conn)

    with connect_runtime(probe.runtime_dsn) as conn:
        with pytest.raises(ValueError, match="active caller transaction"):
            execute_with_outbox(conn, mutation, fact("8"))
        conn.autocommit = True
        with pytest.raises(ValueError, match="active caller transaction"):
            execute_with_outbox(conn, mutation, fact("8"))
    assert calls == []
    assert committed(probe) == ([], [])


def test_unit_cannot_commit_or_end_the_caller_transaction(probe: Database) -> None:
    def committing(conn: Connection) -> str:
        write("P-9")(conn)
        conn.commit()
        return "P-9"

    with (
        connect_runtime(probe.runtime_dsn) as writer,
        writer.transaction(force_rollback=True),
    ):
        with pytest.raises(psycopg.ProgrammingError):
            execute_with_outbox(writer, committing, fact("9"))
        assert state(writer) == ([], [])
    assert committed(probe) == ([], [])
