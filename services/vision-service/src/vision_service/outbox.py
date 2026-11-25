"""Transactional Vision event outbox and bounded, retryable JetStream relay."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from psycopg import Connection, sql
from psycopg.rows import DictRow
from psycopg.types.json import Jsonb


@dataclass(frozen=True)
class PendingPublication:
    source_event_id: str
    event_id: str
    subject: str
    payload: Mapping[str, object]
    claim_token: uuid.UUID


@dataclass(frozen=True)
class VisionOutbox:
    schema: str = "vision"

    def enqueue(
        self,
        connection: Connection[DictRow],
        *,
        source_event_id: str,
        event_id: str,
        subject: str,
        payload: Mapping[str, object],
    ) -> None:
        table = sql.Identifier(self.schema, "inspection_observation_outbox")
        connection.execute(
            sql.SQL(
                "INSERT INTO {} (source_event_id, event_id, subject, payload) "
                "VALUES (%s, %s, %s, %s) ON CONFLICT (source_event_id) DO NOTHING"
            ).format(table),
            (source_event_id, event_id, subject, Jsonb(dict(payload))),
        )
        row = connection.execute(
            sql.SQL(
                "SELECT event_id, subject, payload FROM {} WHERE source_event_id = %s"
            ).format(table),
            (source_event_id,),
        ).fetchone()
        if row is None or row["event_id"] != event_id or row["subject"] != subject:
            raise ValueError("Vision outbox identity conflicts with source event")
        if row["payload"] != dict(payload):
            raise ValueError("Vision outbox payload conflicts with source event")

    def claim_one(
        self, connect: Callable[[], Connection[DictRow]], *, lease_seconds: int = 60
    ) -> PendingPublication | None:
        if lease_seconds < 1:
            raise ValueError("positive outbox claim lease required")
        token = uuid.uuid4()
        table = sql.Identifier(self.schema, "inspection_observation_outbox")
        with connect() as connection, connection.transaction():
            row = connection.execute(
                sql.SQL(
                    "SELECT source_event_id, event_id, subject, payload FROM {} "
                    "WHERE published_at IS NULL AND "
                    "(claimed_until IS NULL OR claimed_until < clock_timestamp()) "
                    "ORDER BY created_at, event_id FOR UPDATE SKIP LOCKED LIMIT 1"
                ).format(table)
            ).fetchone()
            if row is None:
                return None
            connection.execute(
                sql.SQL(
                    "UPDATE {} SET claim_token = %s, "
                    "claimed_until = clock_timestamp() + %s, "
                    "attempt_count = attempt_count + 1 WHERE source_event_id = %s"
                ).format(table),
                (token, timedelta(seconds=lease_seconds), row["source_event_id"]),
            )
        return PendingPublication(
            source_event_id=row["source_event_id"],
            event_id=row["event_id"],
            subject=row["subject"],
            payload=row["payload"],
            claim_token=token,
        )

    def settle(
        self,
        connect: Callable[[], Connection[DictRow]],
        item: PendingPublication,
        *,
        published: bool,
    ) -> None:
        table = sql.Identifier(self.schema, "inspection_observation_outbox")
        with connect() as connection, connection.transaction():
            if published:
                connection.execute(
                    sql.SQL(
                        "UPDATE {} SET published_at = clock_timestamp(), "
                        "claim_token = NULL, claimed_until = NULL "
                        "WHERE source_event_id = %s AND claim_token = %s "
                        "AND published_at IS NULL"
                    ).format(table),
                    (item.source_event_id, item.claim_token),
                )
            else:
                connection.execute(
                    sql.SQL(
                        "UPDATE {} SET claim_token = NULL, claimed_until = NULL "
                        "WHERE source_event_id = %s AND claim_token = %s "
                        "AND published_at IS NULL"
                    ).format(table),
                    (item.source_event_id, item.claim_token),
                )


async def publish_one(
    outbox: VisionOutbox,
    connect: Callable[[], Connection[DictRow]],
    publisher: Any,
) -> bool:
    """Publish one committed row outside SQL transactions; retry is idempotent."""
    item = outbox.claim_one(connect)
    if item is None:
        return False
    body = json.dumps(item.payload, sort_keys=True, separators=(",", ":")).encode()
    try:
        await publisher.publish(item.subject, body, message_id=item.event_id)
    except BaseException:
        outbox.settle(connect, item, published=False)
        raise
    outbox.settle(connect, item, published=True)
    return True


async def publish_pending(
    outbox: VisionOutbox,
    connect: Callable[[], Connection[DictRow]],
    publisher: Any,
    *,
    limit: int = 25,
) -> int:
    if limit < 1:
        raise ValueError("positive outbox publish limit required")
    published = 0
    for _ in range(limit):
        if not await publish_one(outbox, connect, publisher):
            break
        published += 1
    return published
