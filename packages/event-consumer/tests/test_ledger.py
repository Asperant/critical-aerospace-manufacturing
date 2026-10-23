"""Real PostgreSQL effects, rollback and cross-connection duplicate contention."""

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import psycopg
import pytest
from cap_event_consumer import Outcome, ProcessedMessageLedger
from conftest import Database
from psycopg import errors
from psycopg.pq import TransactionStatus
from psycopg.rows import DictRow, dict_row

pytestmark = pytest.mark.integration
ledger = ProcessedMessageLedger("consumer")


def effect(conn: psycopg.Connection[DictRow]) -> None:
    conn.execute("INSERT INTO consumer.effect VALUES ('effect')")


def counts(conn: psycopg.Connection[DictRow]) -> tuple[int, int]:
    row = conn.execute(
        "SELECT (SELECT count(*) FROM consumer.effect) AS effects, "
        "(SELECT count(*) FROM consumer.processed_message) AS messages"
    ).fetchone()
    assert row is not None
    return row["effects"], row["messages"]


def test_first_delivery(connection: psycopg.Connection[DictRow]) -> None:
    calls: list[bool] = []

    def callback(conn: psycopg.Connection[DictRow]) -> None:
        calls.append(True)
        effect(conn)

    assert ledger.process(connection, "twin", "event-1", callback) is Outcome.PROCESSED
    assert calls == [True]
    assert counts(connection) == (1, 1)
    assert connection.info.transaction_status == TransactionStatus.INTRANS


def test_duplicate(connection: psycopg.Connection[DictRow]) -> None:
    assert ledger.process(connection, "twin", "event-1", effect) is Outcome.PROCESSED
    assert ledger.process(connection, "twin", "event-1", effect) is Outcome.DUPLICATE
    assert counts(connection) == (1, 1)


def test_consumer_isolation(connection: psycopg.Connection[DictRow]) -> None:
    for scope in ("twin", "vision"):
        assert ledger.process(connection, scope, "event-1", effect) is Outcome.PROCESSED
    assert counts(connection) == (2, 2)


def test_callback_failure_rolls_back(database: Database) -> None:
    def fail(conn: psycopg.Connection[DictRow]) -> None:
        effect(conn)
        raise RuntimeError("injected callback failure")

    with (
        psycopg.Connection[DictRow].connect(
            database.runtime_dsn, row_factory=dict_row
        ) as conn,
    ):
        with (
            pytest.raises(RuntimeError, match="injected callback failure"),
            conn.transaction(),
        ):
            ledger.process(conn, "twin", "event-1", fail)
        assert counts(conn) == (0, 0)


def test_ledger_failure_rolls_back_effect(database: Database) -> None:
    with psycopg.connect(database.migration_dsn) as migration:
        migration.execute(
            "ALTER TABLE consumer.processed_message ADD CONSTRAINT injected_failure "
            "CHECK (event_id <> 'write-fails')"
        )
    try:
        with psycopg.Connection[DictRow].connect(
            database.runtime_dsn, row_factory=dict_row
        ) as conn:
            with pytest.raises(errors.CheckViolation), conn.transaction():
                ledger.process(conn, "twin", "write-fails", effect)
            assert counts(conn) == (0, 0)
    finally:
        with psycopg.connect(database.migration_dsn) as migration:
            migration.execute(
                "ALTER TABLE consumer.processed_message DROP CONSTRAINT injected_failure"
            )


def test_caller_rollback(database: Database) -> None:
    with psycopg.Connection[DictRow].connect(
        database.runtime_dsn, row_factory=dict_row
    ) as conn:
        with conn.transaction(force_rollback=True):
            assert ledger.process(conn, "twin", "event-1", effect) is Outcome.PROCESSED
            assert counts(conn) == (1, 1)
        assert counts(conn) == (0, 0)


def test_committed_redelivery(database: Database) -> None:
    # Committed effects are removed afterwards to keep other cases isolated.
    with psycopg.Connection[DictRow].connect(
        database.runtime_dsn, row_factory=dict_row
    ) as conn:
        with conn.transaction():
            assert ledger.process(conn, "twin", "event-1", effect) is Outcome.PROCESSED
        with conn.transaction():
            assert ledger.process(conn, "twin", "event-1", effect) is Outcome.DUPLICATE
            assert counts(conn) == (1, 1)
    with psycopg.connect(database.admin_dsn) as admin:
        admin.execute("TRUNCATE consumer.effect, consumer.processed_message")


@pytest.mark.parametrize("winner_rollback", [False, True])
def test_concurrent_duplicate(database: Database, winner_rollback: bool) -> None:
    event_id = uuid.uuid4().hex
    second_ready = Event()

    def second() -> Outcome:
        with (
            psycopg.Connection[DictRow].connect(
                database.runtime_dsn,
                row_factory=dict_row,
                application_name="evt-slice2-contender",
            ) as conn,
            conn.transaction(),
        ):
            conn.execute("SET LOCAL statement_timeout = '10s'")
            second_ready.set()
            return ledger.process(conn, "twin", event_id, effect)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            with (
                psycopg.Connection[DictRow].connect(
                    database.runtime_dsn, row_factory=dict_row
                ) as first,
                first.transaction(force_rollback=winner_rollback),
            ):
                assert (
                    ledger.process(first, "twin", event_id, effect) is Outcome.PROCESSED
                )
                future = pool.submit(second)
                assert second_ready.wait(5)
                # Observe actual lock contention before releasing the first transaction.
                with psycopg.connect(database.admin_dsn, autocommit=True) as observer:
                    deadline = time.monotonic() + 5
                    while True:
                        waiting = observer.execute(
                            "SELECT 1 FROM pg_catalog.pg_stat_activity "
                            "WHERE application_name = 'evt-slice2-contender' "
                            "AND wait_event_type = 'Lock' AND wait_event = 'advisory'"
                        ).fetchone()
                        if waiting:
                            break
                        assert time.monotonic() < deadline, "contender never waited"
                        time.sleep(0.01)
                assert not future.done()
            expected = Outcome.PROCESSED if winner_rollback else Outcome.DUPLICATE
            assert future.result(timeout=10) is expected
        with psycopg.Connection[DictRow].connect(
            database.runtime_dsn, row_factory=dict_row
        ) as check:
            assert counts(check) == (1, 1)
    finally:
        with psycopg.connect(database.admin_dsn) as admin:
            admin.execute("TRUNCATE consumer.effect, consumer.processed_message")


def test_requires_caller_transaction(database: Database) -> None:
    with (
        psycopg.Connection[DictRow].connect(
            database.runtime_dsn, row_factory=dict_row, autocommit=True
        ) as conn,
        pytest.raises(ValueError, match="active caller-owned"),
    ):
        ledger.process(conn, "twin", "event-1", effect)


def test_requires_read_committed(database: Database) -> None:
    with (
        psycopg.Connection[DictRow].connect(
            database.runtime_dsn, row_factory=dict_row
        ) as conn,
        conn.transaction(),
    ):
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
        with pytest.raises(ValueError, match="READ COMMITTED"):
            ledger.process(conn, "twin", "event-1", effect)
        assert counts(conn) == (0, 0)
