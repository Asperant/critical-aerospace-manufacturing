"""Checksum replay, SQL constraints and runtime privilege checks on PostgreSQL."""

import psycopg
import pytest
from cap_event_consumer.migrate import migrate
from conftest import Database
from psycopg import errors
from psycopg.rows import DictRow, dict_row

pytestmark = pytest.mark.integration


def test_migration_replay(database: Database) -> None:
    with psycopg.Connection[DictRow].connect(
        database.migration_dsn, row_factory=dict_row
    ) as conn:
        conn.execute("SELECT 1")
        assert migrate(conn, "consumer", database.runtime_role) is False


def test_checksum_mismatch(database: Database) -> None:
    with (
        psycopg.Connection[DictRow].connect(
            database.migration_dsn, row_factory=dict_row
        ) as conn,
        conn.transaction(force_rollback=True),
    ):
        conn.execute("UPDATE consumer.consumer_schema_migration SET sha256 = 'bad'")
        with pytest.raises(ValueError, match="checksum mismatch"):
            migrate(conn, "consumer", database.runtime_role)


@pytest.mark.parametrize("scope,event", [("", "e"), ("s", " ")])
def test_nonblank_key(
    connection: psycopg.Connection[DictRow], scope: str, event: str
) -> None:
    with pytest.raises(errors.CheckViolation), connection.transaction():
        connection.execute(
            "INSERT INTO consumer.processed_message (consumer_scope,event_id) "
            "VALUES (%s,%s)",
            (scope, event),
        )


def test_primary_key(connection: psycopg.Connection[DictRow]) -> None:
    connection.execute(
        "INSERT INTO consumer.processed_message (consumer_scope,event_id) VALUES ('s','e')"
    )
    with pytest.raises(errors.UniqueViolation), connection.transaction():
        connection.execute(
            "INSERT INTO consumer.processed_message (consumer_scope,event_id) "
            "VALUES ('s','e')"
        )


@pytest.mark.parametrize(
    "statement",
    [
        "DELETE FROM consumer.processed_message",
        "UPDATE consumer.processed_message SET event_id = 'changed'",
        "SELECT * FROM consumer.consumer_schema_migration",
        "CREATE TABLE consumer.forbidden (id int)",
    ],
)
def test_runtime_privileges(
    connection: psycopg.Connection[DictRow], statement: str
) -> None:
    with pytest.raises(errors.InsufficientPrivilege), connection.transaction():
        connection.execute(statement.encode())
