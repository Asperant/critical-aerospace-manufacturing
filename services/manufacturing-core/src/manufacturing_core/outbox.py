"""Core-owned outbox storage. Caller owns authorization and the transaction."""

from typing import Literal

import psycopg
from psycopg.pq import TransactionStatus
from psycopg.rows import DictRow
from psycopg.types.json import Jsonb
from pydantic import AwareDatetime, BaseModel, ConfigDict

from manufacturing_core.domain import Identity
from manufacturing_core.events_v1 import DomainEventV1


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
