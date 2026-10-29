from __future__ import annotations

import asyncio
import json
from pathlib import Path
from datetime import UTC, datetime
from typing import Any

import nats
import psycopg
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.api import DeliverPolicy
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from cap_event_consumer.consumer import AdmissionError as ConsumerAdmissionError
from cap_event_consumer.consumer import Consumer, DeliveryContext, Event
from cap_event_consumer.jetstream import Binding, JetStreamConsumer
from cap_event_consumer.ledger import ProcessedMessageLedger
from operational_twin.nats_consumer import decode_projection_event
from operational_twin.projector import ProjectionState, Projector

from .config import Settings


def _connect(settings: Settings) -> psycopg.Connection[Any]:
    return psycopg.connect(settings.pg_dsn, row_factory=dict_row, connect_timeout=10)


def _apply(connection: psycopg.Connection[Any], settings: Settings, data: bytes) -> None:
    event = decode_projection_event(data, expected_world_id=settings.world_id, expected_branch_id=settings.branch_id)
    rows = connection.execute(
        "SELECT aggregate_type, aggregate_id, aggregate_version FROM twin.projection_entity "
        "WHERE world_id=%s AND branch_id=%s",
        (settings.world_id, settings.branch_id),
    ).fetchall()
    revisions = {
        (row["aggregate_type"], row["aggregate_id"]): row["aggregate_version"]
        for row in rows
    }
    state = ProjectionState(
        world_id=settings.world_id,
        branch_id=settings.branch_id,
        entities={
            (row["aggregate_type"], row["aggregate_id"]): dict(row["state"])
            for row in rows
        },
        aggregate_revisions=revisions,
    )
    result = Projector(state).apply(event)
    entity = state.entities[(event.aggregate_type, event.aggregate_id)]
    now = datetime.now(UTC)
    connection.execute(
        "INSERT INTO twin.projection_entity "
        "(aggregate_type, aggregate_id, world_id, branch_id, aggregate_version, state, source_event_id, source_revision, updated_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) "
        "ON CONFLICT (world_id, branch_id, aggregate_type, aggregate_id) DO UPDATE SET "
        "aggregate_version=EXCLUDED.aggregate_version, state=EXCLUDED.state, source_event_id=EXCLUDED.source_event_id, "
        "source_revision=EXCLUDED.source_revision, updated_at=EXCLUDED.updated_at",
        (event.aggregate_type, event.aggregate_id, settings.world_id, settings.branch_id,
         event.aggregate_version, Jsonb(entity), event.event_id, result.source_revision, now),
    )
    connection.execute(
        "INSERT INTO twin.applied_event "
        "(consumer_scope,event_id,world_id,branch_id,aggregate_type,aggregate_id,aggregate_version) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (settings.consumer_scope, event.event_id, settings.world_id, settings.branch_id,
         event.aggregate_type, event.aggregate_id, event.aggregate_version),
    )
    connection.execute(
        "INSERT INTO twin.projection_revision(world_id,branch_id,source_event_id,status,updated_at) "
        "VALUES (%s,%s,%s,'FRESH',%s) ON CONFLICT (world_id,branch_id) DO UPDATE SET "
        "source_event_id=EXCLUDED.source_event_id,status='FRESH',updated_at=EXCLUDED.updated_at",
        (settings.world_id, settings.branch_id, event.event_id, now),
    )


def _identify(data: bytes) -> Event:
    try:
        body = json.loads(data)
        event_id = body.get("envelope", body).get("event_id")
    except (TypeError, ValueError, AttributeError):
        raise ConsumerAdmissionError("event: invalid envelope JSON") from None
    if not isinstance(event_id, str) or not event_id.strip():
        raise ConsumerAdmissionError("original event_id required")
    return Event(event_id, body)


async def run() -> None:
    settings = Settings.from_env()
    nc = await nats.connect(settings.nats_url)
    js = nc.jetstream()
    def connect() -> psycopg.Connection[Any]:
        return _connect(settings)

    def admit(_connection: Any, event: Event, _context: DeliveryContext) -> None:
        decode_projection_event(
            json.dumps(event.body).encode(),
            expected_world_id=settings.world_id,
            expected_branch_id=settings.branch_id,
        )

    def effect(connection: Any, event: Event, _context: DeliveryContext) -> None:
        _apply(connection, settings, json.dumps(event.body).encode())

    consumer = Consumer(
        ledger=ProcessedMessageLedger("twin_consumer"),
        scope=settings.consumer_scope,
        connect=connect,
        admit=admit,
        effect=effect,
        identify=_identify,
    )
    subscription = await JetStreamConsumer.bind(
        js,
        Binding(
            stream=settings.stream,
            subject=settings.subject,
            durable=settings.durable,
            ack_wait=30,
            max_deliver=10,
            deliver_policy=DeliverPolicy.ALL,
        ),
        consumer,
        DeliveryContext(),
        ack_timeout=5,
    )
    Path("/tmp/cap-demo-twin.ready").touch()
    try:
        while True:
            try:
                await subscription.receive_once(timeout=5)
            except NatsTimeoutError:
                continue
    finally:
        await subscription.close()
        await nc.drain()


if __name__ == "__main__":
    asyncio.run(run())
