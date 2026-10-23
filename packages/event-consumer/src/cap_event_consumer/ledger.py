"""FR-EVT-005: one local effect per consumer scope and original event identity."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from psycopg import Connection, sql
from psycopg.pq import TransactionStatus
from psycopg.rows import DictRow


class Outcome(Enum):
    PROCESSED = "processed"
    DUPLICATE = "duplicate"


@dataclass(frozen=True)
class ProcessedMessageLedger:
    """Use only inside a caller-owned READ COMMITTED transaction.

    The callback must use the supplied connection, never commit/rollback, and
    perform only rollback-capable local effects. On ANY exception the caller
    must roll back its transaction, including Python callback exceptions.
    PROCESSED means staged, not committed. Caller owns the eventual commit.
    """

    schema: str

    def process(
        self,
        connection: Connection[DictRow],
        consumer_scope: str,
        event_id: str,
        effect: Callable[[Connection[DictRow]], None],
    ) -> Outcome:
        if (
            not self.schema.strip()
            or not consumer_scope.strip()
            or not event_id.strip()
        ):
            raise ValueError("schema, consumer_scope and event_id must be nonblank")
        if connection.info.transaction_status != TransactionStatus.INTRANS:
            raise ValueError("an active caller-owned transaction is required")
        isolation = connection.execute("SHOW transaction_isolation").fetchone()
        if isolation is None or isolation["transaction_isolation"] != "read committed":
            raise ValueError("READ COMMITTED is required for fresh duplicate reads")

        # Same logical key across replicas; hash collisions only serialize extra
        # work. Separate statements ensure a fresh snapshot after lock waiting.
        lock_key = json.dumps(
            ["cap-event-consumer", self.schema, consumer_scope, event_id],
            ensure_ascii=True,
            separators=(",", ":"),
        )
        connection.execute(
            "SELECT pg_catalog.pg_advisory_xact_lock("
            "pg_catalog.hashtextextended(%s, 0))",
            (lock_key,),
        )
        table = sql.Identifier(self.schema, "processed_message")
        key = (consumer_scope, event_id)
        duplicate = connection.execute(
            sql.SQL(
                "SELECT 1 FROM {} WHERE consumer_scope = %s AND event_id = %s"
            ).format(table),
            key,
        ).fetchone()
        if duplicate is not None:
            return Outcome.DUPLICATE
        effect(connection)
        connection.execute(
            sql.SQL("INSERT INTO {} (consumer_scope, event_id) VALUES (%s, %s)").format(
                table
            ),
            key,
        )
        return Outcome.PROCESSED
