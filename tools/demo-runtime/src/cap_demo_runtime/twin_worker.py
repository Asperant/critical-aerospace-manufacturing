from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import nats
import psycopg
from cap_event_consumer.consumer import DeliveryContext
from cap_event_consumer.jetstream import Binding, JetStreamConsumer
from cap_event_consumer.ledger import ProcessedMessageLedger
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.api import DeliverPolicy
from operational_twin.nats_consumer import build_consumer
from operational_twin.postgres_projection import PostgresProjectionStore
from operational_twin.projector import ProjectionState, Projector
from psycopg.rows import DictRow, dict_row

from .config import Settings


def _connect(settings: Settings) -> psycopg.Connection[DictRow]:
    return psycopg.Connection[DictRow].connect(
        settings.pg_dsn, row_factory=dict_row, connect_timeout=10
    )


async def run() -> None:
    settings = Settings.from_env()
    nc = await nats.connect(settings.nats_url)
    js = nc.jetstream()

    def connect() -> psycopg.Connection[Any]:
        return _connect(settings)

    projection_store = PostgresProjectionStore(settings.consumer_scope)
    consumer = build_consumer(
        ledger=ProcessedMessageLedger("twin_consumer"),
        scope=settings.consumer_scope,
        connect=connect,
        projector=Projector(ProjectionState(settings.world_id, settings.branch_id)),
        projection_store=projection_store,
        expected_world_id=settings.world_id,
        expected_branch_id=settings.branch_id,
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
