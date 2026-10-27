"""Core-owned transactional outbox storage and transport-neutral relay."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from typing import Literal, Protocol, TypeVar
from uuid import uuid4

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import DictRow
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from manufacturing_core.events_v1 import DomainEventV1

T = TypeVar("T")


class OutboxRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    outbox_id: str = Field(pattern=r"^\S+$")
    event: DomainEventV1
    created_at: AwareDatetime
    attempt_count: int = Field(default=0, ge=0)
    last_error: str | None = None
    publication_status: Literal["PENDING", "PUBLISHED"] = "PENDING"

    @classmethod
    def new(cls, event: DomainEventV1, *, created_at: datetime) -> OutboxRecord:
        return cls(outbox_id=str(uuid4()), event=event, created_at=created_at)


class OutboxPublisher(Protocol):
    def publish(self, event: dict[str, object]) -> None: ...


class OutboxRepository:
    def __init__(self, connection: psycopg.Connection[DictRow]) -> None:
        self.connection = connection

    def insert(self, record: OutboxRecord) -> None:
        """Insert one immutable event intent inside the caller's transaction."""
        self._require_transaction()
        valid = OutboxRecord.model_validate(record.model_dump())
        self.connection.execute(
            "INSERT INTO core.outbox (outbox_id, event, occurred_at, created_at) "
            "VALUES (%s, %s, %s, %s)",
            (
                valid.outbox_id,
                Jsonb(valid.event.model_dump(mode="json")),
                valid.event.occurred_at.value,
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

    def pending(self, *, limit: int = 100) -> tuple[OutboxRecord, ...]:
        if limit < 1:
            raise ValueError("limit must be positive")
        rows = self.connection.execute(
            "SELECT outbox_id, event, created_at, attempt_count, last_error, "
            "publication_status FROM core.outbox "
            "WHERE publication_status = 'PENDING' "
            "ORDER BY created_at, outbox_id LIMIT %s",
            (limit,),
        ).fetchall()
        return tuple(OutboxRecord.model_validate(row) for row in rows)

    def mark_published(self, outbox_id: str) -> None:
        self._require_transaction()
        self.connection.execute(
            "UPDATE core.outbox SET publication_status = 'PUBLISHED' "
            "WHERE outbox_id = %s AND publication_status = 'PENDING'",
            (outbox_id,),
        )

    def mark_failed(self, outbox_id: str, error: str) -> None:
        self._require_transaction()
        if not error.strip():
            raise ValueError("relay error must be nonblank")
        self.connection.execute(
            "UPDATE core.outbox SET attempt_count = attempt_count + 1, "
            "last_error = %s WHERE outbox_id = %s AND publication_status = 'PENDING'",
            (error[:2000], outbox_id),
        )

    def _require_transaction(self) -> None:
        if self.connection.info.transaction_status != TransactionStatus.INTRANS:
            raise ValueError("outbox operation requires an active caller transaction")


def execute_with_outbox(
    connection: psycopg.Connection[DictRow],
    mutation: Callable[[psycopg.Connection[DictRow]], T],
    record: OutboxRecord | Callable[[T], OutboxRecord],
) -> T:
    """Run a mutation and its event intent as one savepoint in a caller TX.

    This boundary never starts or commits the caller transaction.  A failure in
    either the mutation or event insertion rolls back only this unit, preserving
    earlier caller work and leaving the surrounding transaction usable.
    """
    if connection.info.transaction_status != TransactionStatus.INTRANS:
        raise ValueError(
            "atomic outbox execution requires an active caller transaction"
        )
    form: Callable[[T], OutboxRecord]
    if isinstance(record, OutboxRecord):
        fixed = OutboxRecord.model_validate(record.model_dump())

        def fixed_form(value: T) -> OutboxRecord:
            del value
            return fixed

        form = fixed_form
    else:
        form = record

    with connection.transaction():
        result = mutation(connection)
        OutboxRepository(connection).insert(form(result))
    return result


class OutboxRelay:
    """At-least-once relay adapter; broker ownership stays outside Core."""

    def __init__(self, connection: psycopg.Connection[DictRow]) -> None:
        self.connection = connection

    def publish_pending(self, publisher: OutboxPublisher, *, limit: int = 100) -> int:
        """Publish committed rows and mark success only after publisher returns.

        The publish and status update share a DB transaction.  A crash after the
        broker accepts the event but before commit may publish a duplicate; that
        is intentional and requires downstream consumer idempotency.
        """
        with self.connection.transaction():
            records = OutboxRepository(self.connection).pending(limit=limit)
        published = 0
        for record in records:
            with self.connection.transaction():
                try:
                    publisher.publish(record.event.model_dump(mode="json"))
                except Exception as error:
                    OutboxRepository(self.connection).mark_failed(
                        record.outbox_id, f"{type(error).__name__}: {error}"
                    )
                else:
                    OutboxRepository(self.connection).mark_published(record.outbox_id)
                    published += 1
        return published
