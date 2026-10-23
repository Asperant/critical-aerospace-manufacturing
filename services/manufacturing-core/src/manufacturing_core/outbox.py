"""Core-owned outbox storage. Caller owns authorization and the transaction."""

from collections.abc import Callable
from typing import Literal, TypeVar

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import DictRow
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, BaseModel, ConfigDict

from manufacturing_core.domain import Identity
from manufacturing_core.events_v1 import DomainEventV1

T = TypeVar("T")


class OutboxRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outbox_id: Identity
    event: DomainEventV1
    created_at: AwareDatetime
    attempt_count: Literal[0] = 0
    last_error: Literal[None] = None
    publication_status: Literal["PENDING"] = "PENDING"


class OutboxRepository:
    def __init__(self, connection: psycopg.Connection[DictRow]) -> None:
        self.connection = connection

    def insert(self, record: OutboxRecord) -> None:
        """Insert one validated fact; duplicate IDs fail, never command-deduplicate.

        No implicit BEGIN, savepoint, commit or rollback. SQL failure belongs to
        the caller's transaction. This API never verifies a manufacturing effect.
        """
        if self.connection.info.transaction_status != TransactionStatus.INTRANS:
            raise ValueError("outbox insert requires an active caller transaction")
        valid = OutboxRecord.model_validate(record.model_dump())
        self.connection.execute(
            "INSERT INTO core.outbox (outbox_id, event, created_at) VALUES (%s, %s, %s)",
            (
                valid.outbox_id,
                Jsonb(valid.event.model_dump(mode="json")),
                valid.created_at,
            ),
        )

    def get(self, outbox_id: str) -> OutboxRecord | None:
        row = self.connection.execute(
            "SELECT outbox_id, event, created_at, attempt_count, last_error, "
            "publication_status FROM core.outbox WHERE outbox_id = %s",
            (outbox_id,),
        ).fetchone()
        return None if row is None else OutboxRecord.model_validate(row)


def execute_with_outbox(
    connection: psycopg.Connection[DictRow],
    mutation: Callable[[psycopg.Connection[DictRow]], T],
    record: OutboxRecord | Callable[[T], OutboxRecord],
) -> T:
    """Run a caller-supplied mutation and insert a caller-formed outbox fact as one unit.

    Generic atomic boundary only. The caller owns the surrounding transaction, the
    mutation, authorization, lifecycle eligibility, command idempotency, revisions
    and event construction; `record` is either the already-formed fact or a
    callable that forms it from the mutation's result. Both statements run in one
    savepoint of the caller's transaction, so a failure of the mutation, of the
    record callable or of the outbox INSERT removes every effect of this unit and
    leaves the caller's transaction usable. The unit never commits or begins a
    transaction (psycopg forbids commit/rollback inside it); a caller rollback
    removes both effects and only the caller's commit makes them visible.
    """
    if connection.info.transaction_status != TransactionStatus.INTRANS:
        raise ValueError(
            "atomic outbox execution requires an active caller transaction"
        )
    if callable(record):
        form = record
    else:
        fixed = OutboxRecord.model_validate(record.model_dump())

        def form(_: T) -> OutboxRecord:
            return fixed

    with connection.transaction():
        result = mutation(connection)
        OutboxRepository(connection).insert(form(result))
    return result
