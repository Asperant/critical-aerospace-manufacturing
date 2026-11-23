"""Real Core outbox → JetStream → durable Twin projection boundary."""

# pyright: reportMissingImports=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportOptionalMemberAccess=false
# Integration imports are supplied by this job's explicit PYTHONPATH; nats-py
# also exposes incomplete dynamic type information at its transport boundary.

from __future__ import annotations

import asyncio
import os
import uuid
from collections.abc import Iterator
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import LiteralString, cast

import nats
import psycopg
import pytest
from cap_event_consumer.consumer import DeliveryContext
from cap_event_consumer.jetstream import Binding, JetStreamConsumer
from cap_event_consumer.ledger import Outcome, ProcessedMessageLedger
from manufacturing_core.events_v1 import EntityReference, UtcOccurrence
from manufacturing_core.events_v2 import LotHeldEventV2, LotHeldPayloadV2
from manufacturing_core.outbox import OutboxRecord, OutboxRepository
from manufacturing_core.outbox_publisher import JetStreamOutboxPublisher
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.api import DeliverPolicy
from nats.js.errors import NotFoundError
from operational_twin.nats_consumer import build_consumer
from operational_twin.postgres_projection import PostgresProjectionStore
from operational_twin.projector import ProjectionState, Projector
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow, dict_row
from psycopg.sql import SQL, Identifier

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def outbox_twin_dsn() -> Iterator[str]:
    admin_dsn = os.environ.get("CI_PG_DSN")
    if not admin_dsn or os.environ.get("OUTBOX_TWIN_TEST_DISPOSABLE") != "1":
        pytest.fail("real disposable PostgreSQL DSN and explicit opt-in required")
    name = "outbox_twin_" + uuid.uuid4().hex[:12]
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        if admin.info.server_version < 180000:
            pytest.fail("this integration requires PostgreSQL 18")
        admin.execute(SQL("CREATE DATABASE {}").format(Identifier(name)))
    dsn = make_conninfo(admin_dsn, dbname=name)
    root = Path(__file__).parents[2]
    try:
        with psycopg.connect(dsn) as connection:
            connection.execute("CREATE SCHEMA core")
            connection.execute("CREATE TABLE core.lot (id text PRIMARY KEY)")
            migration_paths = (
                root
                / "services/manufacturing-core/src/manufacturing_core/migrations/0005_outbox.sql",
                root / "services/operational-twin/migrations/0001_twin.sql",
            )
            for migration_path in migration_paths:
                for statement in migration_path.read_text(encoding="utf-8").split(
                    ";\n"
                ):
                    if statement.strip():
                        connection.execute(SQL(cast(LiteralString, statement)))
            connection.execute("CREATE SCHEMA twin_consumer")
            consumer_migration = (
                root
                / "packages/event-consumer/src/cap_event_consumer/migrations/0001_processed_message.sql"
            ).read_text(encoding="utf-8")
            for statement in consumer_migration.split(";\n"):
                if statement.strip():
                    connection.execute(
                        SQL(
                            cast(
                                LiteralString, statement.format(schema="twin_consumer")
                            )
                        )
                    )
        yield dsn
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(SQL("DROP DATABASE {} WITH (FORCE)").format(Identifier(name)))


def connect_dict(dsn: str) -> psycopg.Connection[DictRow]:
    return psycopg.Connection[DictRow].connect(dsn, row_factory=dict_row)


def outbox_record() -> OutboxRecord:
    occurred = datetime(2026, 11, 23, 12, tzinfo=UTC)
    payload = LotHeldPayloadV2(
        event_type="production.lot-held",
        schema_version=2,
        aggregate_type="Lot",
        aggregate_id="LOT-OUTBOX-1",
        aggregate_version=1,
        lot_id="LOT-OUTBOX-1",
        lot_revision="CORE-REV-1",
        material_hold_id="HOLD-OUTBOX-1",
        reason="inspection anomaly",
    )
    event = LotHeldEventV2(
        event_id="EVT-OUTBOX-1",
        producer="manufacturing-core",
        world_id="OUTBOX-TEST-WORLD",
        correlation_id="CORR-OUTBOX-1",
        causation_id="CMD-OUTBOX-1",
        trace_id="TRACE-OUTBOX-1",
        occurred_at=UtcOccurrence(clock="UTC", value=occurred),
        observed_at=occurred,
        entity_refs=(
            EntityReference(
                entity_type="Lot", id="LOT-OUTBOX-1", revision="CORE-REV-1"
            ),
        ),
        event_type="production.lot-held",
        schema_version=2,
        payload=payload,
    )
    return OutboxRecord.new(event, created_at=occurred)


async def _publish_and_project(dsn: str, nats_url: str) -> None:
    nc = await nats.connect(nats_url, connect_timeout=10)
    js = nc.jetstream()
    stream, subject, durable = "CAP_EVENTS", "cap.core.events", "twin-outbox-test"
    subscription: JetStreamConsumer | None = None
    stream_created = False
    try:
        try:
            await js.stream_info(stream)
        except NotFoundError:
            await js.add_stream(name=stream, subjects=[subject])
            stream_created = True
        else:
            pytest.fail(
                "dedicated CAP_EVENTS fixture already exists; refusing to reuse it"
            )

        record = outbox_record()
        with connect_dict(dsn) as connection, connection.transaction():
            OutboxRepository(connection).insert(record)

        # The committed intent is still pending after a simulated relay restart.
        with connect_dict(dsn) as connection, connection.transaction():
            pending = OutboxRepository(connection).pending(limit=25)
        assert [item.outbox_id for item in pending] == [record.outbox_id]

        publisher = JetStreamOutboxPublisher(js, stream, subject)
        first_ack = await publisher.publish(pending[0])
        # Simulate a process crash after JetStream ACK but before marking the row.
        restarted_publisher = JetStreamOutboxPublisher(js, stream, subject)
        retry_ack = await restarted_publisher.publish(pending[0])
        assert first_ack.seq == retry_ack.seq

        with connect_dict(dsn) as connection, connection.transaction():
            OutboxRepository(connection).mark_published(record.outbox_id)

        scope = "twin-outbox-test"
        store = PostgresProjectionStore(scope)
        projector = Projector(ProjectionState("OUTBOX-TEST-WORLD"))
        consumer = build_consumer(
            ledger=ProcessedMessageLedger("twin_consumer"),
            scope=scope,
            connect=lambda: connect_dict(dsn),
            projector=projector,
            projection_store=store,
            expected_world_id="OUTBOX-TEST-WORLD",
        )
        subscription = await JetStreamConsumer.bind(
            js,
            Binding(
                stream=stream,
                subject=subject,
                durable=durable,
                ack_wait=30,
                max_deliver=10,
                deliver_policy=DeliverPolicy.ALL,
            ),
            consumer,
            DeliveryContext(),
            ack_timeout=5,
        )
        assert await subscription.receive_once(timeout=10) is Outcome.PROCESSED

        with connect_dict(dsn) as connection:
            applied = connection.execute(
                "SELECT event_id, world_id, aggregate_version FROM twin.applied_event "
                "WHERE consumer_scope=%s AND event_id=%s",
                (scope, record.event.event_id),
            ).fetchone()
            entity = connection.execute(
                "SELECT state->>'lifecycle' AS lifecycle, source_event_id "
                "FROM twin.projection_entity WHERE world_id=%s AND aggregate_id=%s",
                ("OUTBOX-TEST-WORLD", "LOT-OUTBOX-1"),
            ).fetchone()
            revision = connection.execute(
                "SELECT source_event_id, status FROM twin.projection_revision "
                "WHERE world_id=%s AND branch_id='PRIMARY'",
                ("OUTBOX-TEST-WORLD",),
            ).fetchone()
            outbox = OutboxRepository(connection).get(record.outbox_id)
        assert applied is not None and applied["event_id"] == record.event.event_id
        assert applied["aggregate_version"] == 1
        assert entity is not None and entity["lifecycle"] == "HELD"
        assert entity["source_event_id"] == record.event.event_id
        assert revision is not None and revision["status"] == "FRESH"
        assert revision["source_event_id"] == record.event.event_id
        assert outbox is not None and outbox.publication_status == "PUBLISHED"

        with pytest.raises(NatsTimeoutError):
            await subscription.receive_once(timeout=0.25)
    finally:
        if subscription is not None:
            await subscription.close()
        with suppress(NotFoundError):
            await js.delete_consumer(stream, durable)
        if stream_created:
            await js.delete_stream(stream)
        await nc.drain()


def test_real_core_outbox_to_durable_twin_projection(
    outbox_twin_dsn: str,
) -> None:
    nats_url = os.environ.get("CI_NATS_URL")
    if not nats_url:
        pytest.fail("CI_NATS_URL is required for real JetStream acceptance")
    asyncio.run(_publish_and_project(outbox_twin_dsn, nats_url))
