from __future__ import annotations

import asyncio
import json
import os
import secrets
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

import nats
import psycopg
import pytest
from cap_contracts.envelope import (
    CausationID,
    CorrelationID,
    EntityID,
    EntityReference,
    EntityRevision,
    EventEnvelope,
    EventID,
    TraceID,
)
from cap_event_consumer.consumer import DeliveryContext
from cap_event_consumer.jetstream import Binding, JetStreamConsumer
from cap_event_consumer.ledger import Outcome
from conftest import (
    encode_png,
    gray,
    reference_for,
    request_for,
    store_with,
    textured,
)
from nats.js.api import DeliverPolicy
from nats.js.errors import NotFoundError
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow, dict_row
from psycopg.sql import SQL, Identifier, Literal
from vision_service.migrate import migrate
from vision_service.worker import VisionWorker, WorkerConfig

pytestmark = pytest.mark.integration


class Publisher:
    def __init__(self, jetstream: Any) -> None:
        self.jetstream = jetstream

    async def publish(self, subject: str, data: bytes, *, message_id: str) -> Any:
        return await self.jetstream.publish(
            subject, data, headers={"Nats-Msg-Id": message_id}
        )


class PublishThenFail:
    def __init__(self, delegate: Publisher) -> None:
        self.delegate = delegate
        self.failed = False

    async def publish(self, subject: str, data: bytes, *, message_id: str) -> Any:
        result = await self.delegate.publish(subject, data, message_id=message_id)
        if not self.failed:
            self.failed = True
            raise RuntimeError("simulated relay crash after JetStream ACK")
        return result


def request_envelope() -> EventEnvelope:
    return EventEnvelope(
        event_id=EventID("evt-request-1"),
        event_type="InspectionRequested",
        schema_version=1,
        producer="manufacturing-core",
        world_id="world-production",
        correlation_id=CorrelationID("corr-1"),
        causation_id=CausationID("evt-root"),
        trace_id=TraceID("trace-1"),
        occurred_at=datetime(2026, 10, 29, tzinfo=UTC),
        observed_at=datetime(2026, 10, 29, tzinfo=UTC),
        entity_refs=(
            EntityReference(
                "SerializedComponent", EntityID("C-1"), EntityRevision("r1")
            ),
        ),
    )


def _runtime_database(admin_dsn: str) -> Generator[str, None, None]:
    suffix = uuid.uuid4().hex[:12]
    database = "vision_test_" + suffix
    migration_role = database + "_migration"
    runtime_role = database + "_runtime"
    migration_password = secrets.token_urlsafe(24)
    runtime_password = secrets.token_urlsafe(24)
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        if admin.info.server_version < 180000:
            pytest.fail("Vision consumer acceptance requires PostgreSQL 18")
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
        admin.execute(SQL("CREATE DATABASE {}").format(Identifier(database)))
        admin.execute(
            SQL("GRANT CREATE ON DATABASE {} TO {}").format(
                Identifier(database), Identifier(migration_role)
            )
        )
    migration_dsn = make_conninfo(
        admin_dsn,
        dbname=database,
        user=migration_role,
        password=migration_password,
    )
    runtime_dsn = make_conninfo(
        admin_dsn, dbname=database, user=runtime_role, password=runtime_password
    )
    try:
        with (
            psycopg.Connection[DictRow].connect(
                migration_dsn, row_factory=dict_row
            ) as connection,
            connection.transaction(),
        ):
            connection.execute(SQL("CREATE SCHEMA {}").format(Identifier("vision")))
            connection.execute(
                SQL("CREATE SCHEMA {}").format(Identifier("vision_consumer"))
            )
            assert migrate(connection, runtime_role)
            assert not migrate(connection, runtime_role)
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(
                SQL("REVOKE CREATE ON DATABASE {} FROM {}").format(
                    Identifier(database), Identifier(migration_role)
                )
            )
        yield runtime_dsn
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(
                SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    Identifier(database)
                )
            )
            admin.execute(
                SQL("DROP ROLE IF EXISTS {}").format(Identifier(runtime_role))
            )
            admin.execute(
                SQL("DROP ROLE IF EXISTS {}").format(Identifier(migration_role))
            )


def test_real_vision_consumer_deduplicates_redelivery_and_retries_outbox() -> None:
    admin_dsn = os.environ.get("CI_PG_DSN")
    nats_url = os.environ.get("CI_NATS_URL")
    if not admin_dsn or not nats_url or os.environ.get("VISION_TEST_DISPOSABLE") != "1":
        pytest.fail(
            "disposable PostgreSQL/NATS and explicit VISION_TEST_DISPOSABLE=1 required"
        )

    database = _runtime_database(admin_dsn)
    runtime_dsn = next(database)
    suffix = uuid.uuid4().hex[:10]
    stream = "VISION_TEST_" + suffix
    input_subject = "vision.test." + suffix + ".input"
    output_subject = "vision.test." + suffix + ".output"
    durable = "vision-test-" + suffix

    async def scenario() -> None:
        connection = await nats.connect(nats_url, connect_timeout=10)
        js = connection.jetstream()
        bound: JetStreamConsumer | None = None
        stream_created = False
        try:
            try:
                await js.stream_info(stream)
            except NotFoundError:
                await js.add_stream(
                    name=stream, subjects=[input_subject, output_subject]
                )
                stream_created = True
            else:
                pytest.fail("unique Vision test stream already exists; refusing reuse")

            image = encode_png(gray(textured(seed=13)))
            image_ref = reference_for(
                image,
                **{
                    "context": {
                        "world_id": "world-production",
                        "simulation_run_id": None,
                        "branch_id": None,
                    }
                },
            )
            request = request_for(image_ref, world_id="world-production")
            reader = store_with(image_ref, image)
            config = WorkerConfig(
                nats_url=nats_url,
                database_dsn=runtime_dsn,
                input_stream=stream,
                input_subject=input_subject,
                input_durable=durable,
                output_subject=output_subject,
                world_id="world-production",
            )

            def connect() -> psycopg.Connection[DictRow]:
                return psycopg.Connection[DictRow].connect(
                    runtime_dsn, row_factory=dict_row
                )

            class NoopPublisher:
                async def publish(
                    self, subject: str, data: bytes, *, message_id: str
                ) -> None:
                    raise AssertionError("run_nats installs the real publisher")

            worker = VisionWorker(
                reader,
                NoopPublisher(),
                config,
                clock=lambda: datetime.now(UTC),
                connect=connect,
            )
            bound = await JetStreamConsumer.bind(
                js,
                Binding(
                    stream=stream,
                    subject=input_subject,
                    durable=durable,
                    ack_wait=10,
                    max_deliver=5,
                    deliver_policy=DeliverPolicy.ALL,
                ),
                worker.consumer,
                DeliveryContext(),
                ack_timeout=10,
            )

            request_body = {
                "envelope": request_envelope().to_mapping(),
                "payload": request,
            }
            encoded = json.dumps(request_body).encode()
            await js.publish(input_subject, encoded, headers={"Nats-Msg-Id": "first"})
            assert await bound.receive_once(timeout=3) is Outcome.PROCESSED
            assert await js.stream_info(stream)  # the request is committed/ACKed

            crashing = PublishThenFail(Publisher(js))
            worker.publisher = crashing
            with pytest.raises(RuntimeError, match="simulated relay crash"):
                await worker.publish_pending(limit=1)
            worker.publisher = Publisher(js)
            assert await worker.publish_pending(limit=1) == 1

            await js.publish(
                input_subject, encoded, headers={"Nats-Msg-Id": "redelivery"}
            )

            class FailIfRead:
                def read(self, _reference: Any) -> bytes:
                    raise AssertionError("committed duplicate must skip artifact IO")

            worker.reader = FailIfRead()
            assert await bound.receive_once(timeout=3) is Outcome.DUPLICATE
            assert await worker.publish_pending(limit=1) == 0

            with (
                psycopg.Connection[DictRow].connect(
                    runtime_dsn, row_factory=dict_row
                ) as db,
                db.transaction(),
            ):
                rows = db.execute(
                    "SELECT source_event_id, event_id, attempt_count, published_at "
                    "FROM vision.inspection_observation_outbox"
                ).fetchall()
                processed = db.execute(
                    "SELECT count(*) AS n FROM vision_consumer.processed_message"
                ).fetchone()
            assert len(rows) == 1
            assert rows[0]["source_event_id"] == "evt-request-1"
            assert rows[0]["attempt_count"] == 2
            assert rows[0]["published_at"] is not None
            assert processed is not None and processed["n"] == 1
            state = await js.stream_info(stream)
            assert state.state.messages == 3  # two inputs, one deduplicated output
        finally:
            if bound is not None:
                await bound.close()
            if stream_created:
                await js.delete_stream(stream)
            await connection.close()

    try:
        asyncio.run(scenario())
    finally:
        database.close()
