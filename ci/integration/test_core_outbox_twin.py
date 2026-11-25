"""Real Core outbox → JetStream → durable Twin projection boundary."""

# pyright: reportMissingImports=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownParameterType=false, reportUnknownVariableType=false, reportOptionalMemberAccess=false
# Integration imports are supplied by this job's explicit PYTHONPATH; nats-py
# also exposes incomplete dynamic type information at its transport boundary.

from __future__ import annotations

import asyncio
import os
import secrets
import uuid
from collections.abc import Iterator, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import LiteralString, cast

import nats
import psycopg
import pytest
from cap_contracts.envelope import EventEnvelope
from cap_event_consumer.consumer import DeliveryContext, Event
from cap_event_consumer.jetstream import Binding, JetStreamConsumer
from cap_event_consumer.ledger import Outcome, ProcessedMessageLedger
from manufacturing_core.commands import OutcomeStatus, PlaceLotOnHold
from manufacturing_core.database import connect_runtime
from manufacturing_core.migrate import migrate
from manufacturing_core.outbox import OutboxRecord, OutboxRelay, OutboxRepository
from manufacturing_core.outbox_publisher import JetStreamOutboxPublisher
from manufacturing_core.transitions import CoreTransitionService
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.api import DeliverPolicy
from nats.js.errors import NotFoundError
from operational_twin.nats_consumer import build_consumer
from operational_twin.postgres_projection import PostgresProjectionStore
from operational_twin.projector import ProjectionState, Projector
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow, dict_row
from psycopg.sql import SQL, Identifier, Literal

pytestmark = pytest.mark.integration


@dataclass(frozen=True)
class OutboxTwinDatabase:
    admin_dsn: str
    core_runtime_dsn: str


@pytest.fixture(scope="module")
def outbox_twin_dsn() -> Iterator[OutboxTwinDatabase]:
    admin_dsn = os.environ.get("CI_PG_DSN")
    if not admin_dsn or os.environ.get("OUTBOX_TWIN_TEST_DISPOSABLE") != "1":
        pytest.fail("real disposable PostgreSQL DSN and explicit opt-in required")
    suffix = uuid.uuid4().hex[:12]
    name = "outbox_twin_" + suffix
    migration_role = name + "_migration"
    runtime_role = name + "_runtime"
    migration_password = secrets.token_urlsafe(32)
    runtime_password = secrets.token_urlsafe(32)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        if admin.info.server_version < 180000:
            pytest.fail("this integration requires PostgreSQL 18")
        for role, password in (
            (migration_role, migration_password),
            (runtime_role, runtime_password),
        ):
            admin.execute(
                SQL(
                    "CREATE ROLE {} LOGIN PASSWORD {} NOSUPERUSER NOCREATEDB "
                    "NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS"
                ).format(Identifier(role), Literal(password))
            )
        admin.execute(SQL("CREATE DATABASE {}").format(Identifier(name)))
        admin.execute(
            SQL("GRANT CREATE ON DATABASE {} TO {}").format(
                Identifier(name), Identifier(migration_role)
            )
        )
    migration_dsn = make_conninfo(
        admin_dsn, dbname=name, user=migration_role, password=migration_password
    )
    runtime_dsn = make_conninfo(
        admin_dsn, dbname=name, user=runtime_role, password=runtime_password
    )
    admin_database_dsn = make_conninfo(admin_dsn, dbname=name)
    root = Path(__file__).parents[2]
    try:
        assert migrate(migration_dsn, runtime_role) is True
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(
                SQL("REVOKE CREATE ON DATABASE {} FROM {}").format(
                    Identifier(name), Identifier(migration_role)
                )
            )
        with psycopg.connect(admin_database_dsn) as connection:
            twin_migration = root / "services/operational-twin/migrations/0001_twin.sql"
            for statement in twin_migration.read_text(encoding="utf-8").split(";\n"):
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
        yield OutboxTwinDatabase(
            admin_dsn=admin_database_dsn, core_runtime_dsn=runtime_dsn
        )
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(SQL("DROP DATABASE {} WITH (FORCE)").format(Identifier(name)))
            for role in (runtime_role, migration_role):
                admin.execute(SQL("DROP ROLE {}").format(Identifier(role)))


def connect_dict(dsn: str) -> psycopg.Connection[DictRow]:
    return psycopg.Connection[DictRow].connect(dsn, row_factory=dict_row)


def core_hold_outbox_record(dsn: str) -> OutboxRecord:
    occurred = datetime(2026, 11, 23, 12, tzinfo=UTC)
    with connect_runtime(dsn) as connection, connection.transaction():
        connection.execute(
            "INSERT INTO core.manufacturing_route(id, revision) VALUES (%s, %s)",
            ("ROUTE-OUTBOX-1", "route-r1"),
        )
        connection.execute(
            "INSERT INTO core.production_order(id, revision, route_id) VALUES (%s, %s, %s)",
            ("ORDER-OUTBOX-1", "order-r1", "ROUTE-OUTBOX-1"),
        )
        connection.execute(
            "INSERT INTO core.lot(id, revision, order_id) VALUES (%s, %s, %s)",
            ("LOT-OUTBOX-1", "CORE-REV-1", "ORDER-OUTBOX-1"),
        )
        connection.execute(
            "INSERT INTO core.lot_state(id, revision) VALUES (%s, %s)",
            ("LOT-OUTBOX-1", "CORE-REV-1"),
        )
        command = PlaceLotOnHold.model_validate(
            {
                "idempotency_key": "hold-outbox-1",
                "world_id": "OUTBOX-TEST-WORLD",
                "correlation_id": "CORR-OUTBOX-1",
                "causation_id": "INCIDENT-OUTBOX-1",
                "target": {"entity_type": "Lot", "entity_id": "LOT-OUTBOX-1"},
                "expected": {"expected_revision": "CORE-REV-1"},
                "hold_reason": "inspection anomaly",
                "material_hold_id": "HOLD-OUTBOX-1",
            }
        )
        outcome = CoreTransitionService(connection).place_lot_on_hold(
            {"core.lot.place_hold"}, command, now=occurred
        )
        assert outcome.status is OutcomeStatus.ACCEPTED
        records = OutboxRepository(connection).pending()
        assert len(records) == 1
        record = records[0]
        hold = connection.execute(
            "SELECT status, placed_command_id FROM core.material_hold WHERE id = %s",
            ("HOLD-OUTBOX-1",),
        ).fetchone()
        assert hold is not None and hold["status"] == "ACTIVE"
        assert str(hold["placed_command_id"]) == str(command.command_id)
        assert record.event.causation_id == str(command.command_id)
        assert record.event.correlation_id == command.correlation_id
        return record


async def _publish_and_project(database: OutboxTwinDatabase, nats_url: str) -> None:
    record = core_hold_outbox_record(database.core_runtime_dsn)
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

        publisher = JetStreamOutboxPublisher(js, stream, subject)

        class FailAfterAck:
            ack_seq: int | None = None

            async def publish(self, outbox_record: OutboxRecord) -> object:
                ack = await publisher.publish(outbox_record)
                self.ack_seq = ack.seq
                raise RuntimeError("simulated relay crash after JetStream ACK")

        # A crash after ACK leaves a retryable row; JetStream deduplicates the
        # restart by EventID, then the relay marks it published after the next ACK.
        failed_attempt = FailAfterAck()
        with connect_dict(database.core_runtime_dsn) as connection:
            relay = OutboxRelay(connection)
            assert await relay.publish_pending_async(failed_attempt, limit=25) == 0
            with connection.transaction():
                failed = OutboxRepository(connection).get(record.outbox_id)
        assert failed is not None
        assert failed.publication_status == "PENDING"
        assert failed.attempt_count == 1
        assert failed.last_error == "RuntimeError"
        assert failed_attempt.ack_seq is not None

        with connect_dict(database.core_runtime_dsn) as connection:
            assert (
                await OutboxRelay(connection).publish_pending_async(publisher, limit=25)
                == 1
            )
        with connect_dict(database.admin_dsn) as connection, connection.transaction():
            published = OutboxRepository(connection).get(record.outbox_id)
        assert published is not None
        assert published.publication_status == "PUBLISHED"
        assert published.attempt_count == 1
        info = await js.stream_info(stream)
        assert info.state.last_seq == failed_attempt.ack_seq

        scope = "twin-outbox-test"
        store = PostgresProjectionStore(scope)
        projector = Projector(ProjectionState("OUTBOX-TEST-WORLD"))
        consumer = build_consumer(
            ledger=ProcessedMessageLedger("twin_consumer"),
            scope=scope,
            connect=lambda: connect_dict(database.admin_dsn),
            projector=projector,
            projection_store=store,
            expected_world_id="OUTBOX-TEST-WORLD",
        )
        received_envelopes: list[EventEnvelope] = []
        identify = consumer.identify

        def capture_envelope(data: bytes) -> Event:
            event = identify(data)
            envelope = event.body.get("envelope")
            if not isinstance(envelope, Mapping):
                raise AssertionError("published EVT-002 envelope is missing")
            received_envelopes.append(EventEnvelope.from_mapping(envelope))
            return event

        consumer.identify = capture_envelope
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
        assert len(received_envelopes) == 1
        received = received_envelopes[0]
        assert received.event_id == record.event.event_id
        assert received.correlation_id == record.event.correlation_id
        assert received.causation_id == record.event.causation_id
        assert received.trace_id == record.event.trace_id
        assert received.world_id == record.event.world_id
        assert received.occurred_at == record.event.occurred_at.value
        assert received.observed_at == record.event.observed_at

        with connect_dict(database.admin_dsn) as connection:
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
        assert outbox.attempt_count == 1

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
    outbox_twin_dsn: OutboxTwinDatabase,
) -> None:
    nats_url = os.environ.get("CI_NATS_URL")
    if not nats_url:
        pytest.fail("CI_NATS_URL is required for real JetStream acceptance")
    asyncio.run(_publish_and_project(outbox_twin_dsn, nats_url))
