"""TEST-EVT-CONSUMER-IDEMP: real PostgreSQL + isolated real JetStream resources."""

import asyncio
import json
import os
import sys
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from pathlib import Path
from threading import Event as ThreadEvent

import nats
import psycopg
import pytest
from cap_event_consumer.consumer import AdmissionError, DeliveryContext
from cap_event_consumer.jetstream import Binding, JetStreamConsumer, JetStreamDelivery
from cap_event_consumer.ledger import Outcome
from conftest import Database
from nats.aio.client import Client
from nats.errors import ConnectionClosedError
from nats.js.api import DeliverPolicy, StorageType
from nats.js.client import JetStreamContext
from psycopg.rows import DictRow
from worker_support import make_consumer

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def clean(database: Database) -> Iterator[None]:
    yield
    with psycopg.connect(database.admin_dsn) as conn:
        conn.execute("TRUNCATE consumer.effect, consumer.processed_message")


def counts(database: Database) -> tuple[int, int]:
    with psycopg.connect(database.runtime_dsn) as conn:
        row = conn.execute(
            "SELECT (SELECT count(*) FROM consumer.effect), "
            "(SELECT count(*) FROM consumer.processed_message)"
        ).fetchone()
        assert row is not None
        return row


def url() -> str:
    value = os.environ.get("CI_NATS_URL")
    if not value:
        pytest.fail("explicit disposable real CI_NATS_URL required")
    return value


@asynccontextmanager
async def broker() -> AsyncIterator[tuple[Client, JetStreamContext, Binding]]:
    nc = await nats.connect(url())
    js = nc.jetstream()
    identity = uuid.uuid4().hex
    binding = Binding(
        "EVT_TEST_" + identity,
        "evt.test." + identity,
        "test-durable",
        0.3,
        10,
        DeliverPolicy.ALL,
    )
    await js.add_stream(
        name=binding.stream, subjects=[binding.subject], storage=StorageType.FILE
    )
    try:
        yield nc, js, binding
    finally:
        # Use a separate connection if the case deliberately disconnected its client.
        cleanup = await nats.connect(url())
        try:
            await cleanup.jetstream().delete_stream(binding.stream)
        finally:
            await cleanup.close()
            if not nc.is_closed:
                await nc.close()


async def boundary(
    js: JetStreamContext,
    binding: Binding,
    database: Database,
    *,
    scope: str = "test/live",
    context: DeliveryContext | None = None,
    replay: bool = False,
) -> JetStreamConsumer:
    return await JetStreamConsumer.bind(
        js,
        binding,
        make_consumer(database.runtime_dsn, scope, replay=replay),
        context or DeliveryContext(),
        ack_timeout=2,
    )


def test_first_duplicate_and_independent_scope(database: Database) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            consumer = await boundary(js, binding, database)
            await js.publish(binding.subject, b'{"event_id":"event-1"}')

            class VerifiedAck(JetStreamDelivery):
                async def ack(self) -> None:
                    # A separate DB connection sees both committed rows before
                    # the real broker acknowledgement is sent.
                    assert counts(database) == (1, 1)
                    await super().ack()

            message = (await consumer.subscription.fetch(1, timeout=3))[0]
            assert (
                await consumer.consumer.handle(
                    VerifiedAck(message, 2), DeliveryContext()
                )
                is Outcome.PROCESSED
            )
            await js.publish(binding.subject, b'{"event_id":"event-1"}')
            assert await consumer.receive_once(timeout=3) is Outcome.DUPLICATE
            assert counts(database) == (1, 1)
            assert (
                await js.consumer_info(binding.stream, binding.durable)
            ).num_ack_pending == 0
            await consumer.close()
            independent = await boundary(
                js, binding, database, scope="test/independent"
            )
            await js.publish(binding.subject, b'{"event_id":"event-1"}')
            assert await independent.receive_once(timeout=3) is Outcome.PROCESSED
            assert counts(database) == (2, 2)
            await independent.close()

    asyncio.run(run())


@pytest.mark.parametrize(
    "payload,error",
    [
        ({"event_id": "failed", "fail": True}, RuntimeError),
        ({"event_id": "gap", "aggregate_version": 3}, AdmissionError),
        ({}, AdmissionError),
    ],
)
def test_failure_nak_and_retry(
    database: Database, payload: dict[str, object], error: type[Exception]
) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            consumer = await boundary(js, binding, database)
            await js.publish(binding.subject, json.dumps(payload).encode())
            with pytest.raises(error):
                await consumer.receive_once(timeout=3)
            assert counts(database) == (0, 0)
            redelivery = (await consumer.subscription.fetch(1, timeout=3))[0]
            assert redelivery.metadata.num_delivered >= 2
            assert (
                await js.consumer_info(binding.stream, binding.durable)
            ).num_ack_pending == 1
            await consumer.close()

    asyncio.run(run())


def test_retry_after_callback_repair(database: Database) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            consumer = await boundary(js, binding, database)
            original = consumer.consumer.effect

            def fail(*args: object) -> None:
                raise RuntimeError("transient failure")

            consumer.consumer.effect = fail
            await js.publish(binding.subject, b'{"event_id":"retry"}')
            with pytest.raises(RuntimeError):
                await consumer.receive_once(timeout=3)
            consumer.consumer.effect = original
            assert await consumer.receive_once(timeout=3) is Outcome.PROCESSED
            assert counts(database) == (1, 1)
            await consumer.close()

    asyncio.run(run())


def test_database_failure_never_acks(database: Database) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            consumer = await boundary(js, binding, database)
            original = consumer.consumer.connect

            def unavailable() -> psycopg.Connection[DictRow]:
                raise psycopg.OperationalError("injected unavailable database")

            consumer.consumer.connect = unavailable
            await js.publish(binding.subject, b'{"event_id":"db-failure"}')
            with pytest.raises(psycopg.OperationalError):
                await consumer.receive_once(timeout=3)
            assert counts(database) == (0, 0)
            consumer.consumer.connect = original
            assert await consumer.receive_once(timeout=3) is Outcome.PROCESSED
            assert counts(database) == (1, 1)
            await consumer.close()

    asyncio.run(run())


def test_process_death_after_commit_before_ack(database: Database) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            initial = await boundary(js, binding, database)
            await initial.close()
            await js.publish(binding.subject, b'{"event_id":"crash"}')
            worker = Path(__file__).with_name("crash_worker.py")
            env = dict(
                os.environ,
                EVT_TEST_DSN=database.runtime_dsn,
                EVT_TEST_STREAM=binding.stream,
                EVT_TEST_SUBJECT=binding.subject,
                PYTHONPATH=str(Path(__file__).parents[1] / "src"),
            )
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(worker), env=env
            )
            try:
                assert await asyncio.wait_for(process.wait(), timeout=15) == 71
            finally:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            assert counts(database) == (1, 1)
            restarted = await boundary(js, binding, database)
            message = (await restarted.subscription.fetch(1, timeout=3))[0]
            assert message.metadata.num_delivered >= 2
            assert (
                await restarted.consumer.handle(
                    JetStreamDelivery(message, 2), DeliveryContext()
                )
                is Outcome.DUPLICATE
            )
            assert counts(database) == (1, 1)
            assert (
                await js.consumer_info(binding.stream, binding.durable)
            ).num_ack_pending == 0
            await restarted.close()

    asyncio.run(run())


def test_disconnect_reconnect_durable_redelivery(database: Database) -> None:
    async def run() -> None:
        async with broker() as (nc, js, binding):
            initial = await boundary(js, binding, database)
            await js.publish(binding.subject, b'{"event_id":"disconnect"}')
            message = (await initial.subscription.fetch(1, timeout=3))[0]
            await nc.close()
            with pytest.raises(ConnectionClosedError):
                await initial.consumer.handle(
                    JetStreamDelivery(message, 1), DeliveryContext()
                )
            assert counts(database) == (1, 1)
            reconnected = await nats.connect(url())
            try:
                restarted = await boundary(reconnected.jetstream(), binding, database)
                assert await restarted.receive_once(timeout=3) is Outcome.DUPLICATE
                assert counts(database) == (1, 1)
                await restarted.close()
            finally:
                await reconnected.close()

    asyncio.run(run())


def test_concurrent_deliveries(database: Database) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            consumer = await boundary(js, binding, database)
            for _ in range(2):
                await js.publish(binding.subject, b'{"event_id":"concurrent"}')
            results = await asyncio.gather(
                *(consumer.receive_once(timeout=3) for _ in range(2))
            )
            assert set(results) == {Outcome.PROCESSED, Outcome.DUPLICATE}
            assert counts(database) == (1, 1)
            await consumer.close()

    asyncio.run(run())


def test_cancellation_never_acks_unsettled_work(database: Database) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            consumer = await boundary(js, binding, database)
            started, release = ThreadEvent(), ThreadEvent()
            original = consumer.consumer.effect

            def delayed(conn, event, context) -> None:
                started.set()
                if not release.wait(5):
                    raise RuntimeError("test transaction release timed out")
                original(conn, event, context)

            consumer.consumer.effect = delayed
            await js.publish(binding.subject, b'{"event_id":"cancel"}')
            task = asyncio.create_task(consumer.receive_once(timeout=3))
            try:
                assert await asyncio.to_thread(started.wait, 5)
                task.cancel()
            finally:
                release.set()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert counts(database) == (1, 1)
            await consumer.close()
            restarted = await boundary(js, binding, database)
            assert await restarted.receive_once(timeout=3) is Outcome.DUPLICATE
            assert counts(database) == (1, 1)
            await restarted.close()

    asyncio.run(run())


def test_isolated_replay_and_live_rejection(database: Database) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            context = DeliveryContext(
                replay=True, replay_id="test-run", target="shadow-test"
            )
            live = await boundary(js, binding, database, context=context)
            await js.publish(binding.subject, b'{"event_id":"replay"}')
            with pytest.raises(AdmissionError):
                await live.receive_once(timeout=3)
            assert counts(database) == (0, 0)
            await live.close()
            shadow = await boundary(
                js,
                binding,
                database,
                scope="test/shadow-generation",
                context=context,
                replay=True,
            )
            assert await shadow.receive_once(timeout=3) is Outcome.PROCESSED
            await js.publish(binding.subject, b'{"event_id":"replay"}')
            assert await shadow.receive_once(timeout=3) is Outcome.DUPLICATE
            assert counts(database) == (1, 1)
            await shadow.close()

    asyncio.run(run())


def test_commit_failure_rolls_back_before_nak(database: Database) -> None:
    with psycopg.connect(database.migration_dsn) as conn:
        conn.execute(
            "ALTER TABLE consumer.effect ADD CONSTRAINT deferred_effect "
            "UNIQUE (event_id) DEFERRABLE INITIALLY DEFERRED"
        )
    try:
        with psycopg.connect(database.runtime_dsn) as conn:
            conn.execute("INSERT INTO consumer.effect VALUES ('commit-failure')")

        async def run() -> None:
            async with broker() as (_, js, binding):
                consumer = await boundary(js, binding, database)
                await js.publish(binding.subject, b'{"event_id":"commit-failure"}')
                with pytest.raises(psycopg.errors.UniqueViolation):
                    await consumer.receive_once(timeout=3)
                assert counts(database) == (1, 0)
                redelivery = (await consumer.subscription.fetch(1, timeout=3))[0]
                assert redelivery.metadata.num_delivered >= 2
                await consumer.close()

        asyncio.run(run())
    finally:
        with psycopg.connect(database.migration_dsn) as conn:
            conn.execute("ALTER TABLE consumer.effect DROP CONSTRAINT deferred_effect")


def test_binding_mismatch_and_shutdown(database: Database) -> None:
    async def run() -> None:
        async with broker() as (_, js, binding):
            consumer = await boundary(js, binding, database)
            incompatible = Binding(
                binding.stream,
                binding.subject,
                binding.durable,
                99,
                binding.max_deliver,
                binding.deliver_policy,
            )
            with pytest.raises(ValueError, match="differs"):
                await boundary(js, incompatible, database)
            pending = asyncio.create_task(consumer.receive_once(timeout=3))
            await asyncio.sleep(0)
            await consumer.close()
            with pytest.raises(asyncio.CancelledError):
                await pending
            with pytest.raises(RuntimeError, match="closed"):
                await consumer.receive_once(timeout=3)
            # Close preserves the server durable and does not delete its work.
            assert (
                await js.consumer_info(binding.stream, binding.durable)
            ).name == binding.durable

    asyncio.run(run())
