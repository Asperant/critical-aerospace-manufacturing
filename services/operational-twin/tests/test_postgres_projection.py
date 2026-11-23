"""Real PostgreSQL persistence for the rebuildable Twin projection."""

from __future__ import annotations

import asyncio
import json
import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any, LiteralString, cast

import psycopg
import pytest
from cap_event_consumer.consumer import DeliveryContext
from cap_event_consumer.ledger import Outcome, ProcessedMessageLedger
from operational_twin import (
    PostgresProjectionStore,
    ProjectionEvent,
    ProjectionState,
    Projector,
)
from operational_twin.nats_consumer import build_consumer
from psycopg import Connection, sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow, dict_row

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def twin_database_dsn() -> Iterator[str]:
    admin_dsn = os.environ.get("CI_PG_DSN")
    if not admin_dsn or os.environ.get("TWIN_TEST_DISPOSABLE") != "1":
        pytest.fail("real disposable CI PostgreSQL DSN and explicit opt-in required")
    name = "twin_test_" + uuid.uuid4().hex[:12]
    with psycopg.connect(admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    dsn = make_conninfo(admin_dsn, dbname=name)
    try:
        with psycopg.connect(dsn) as connection:
            migration_dir = Path(__file__).parents[1] / "migrations"
            for migration_path in sorted(migration_dir.glob("*.sql")):
                migration = migration_path.read_text(encoding="utf-8")
                for statement in migration.split(";\n"):
                    if statement.strip():
                        connection.execute(sql.SQL(cast(LiteralString, statement)))
            connection.execute("CREATE SCHEMA twin_consumer")
            consumer_migration = (
                Path(__file__).parents[3]
                / "packages/event-consumer/src/cap_event_consumer/migrations/0001_processed_message.sql"
            ).read_text(encoding="utf-8")
            for statement in consumer_migration.split(";\n"):
                if statement.strip():
                    connection.execute(
                        sql.SQL(cast(LiteralString, statement.format(schema="twin_consumer")))
                    )
        yield dsn
    finally:
        with psycopg.connect(admin_dsn, autocommit=True) as admin:
            admin.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


def event(
    event_id: str,
    version: int,
    *,
    world_id: str = "PRIMARY",
    branch_id: str = "PRIMARY",
    aggregate_id: str = "LOT-1",
) -> ProjectionEvent:
    return ProjectionEvent(
        event_id=event_id,
        event_type="production.lot-held",
        world_id=world_id,
        aggregate_type="Lot",
        aggregate_id=aggregate_id,
        aggregate_version=version,
        payload={
            "event_type": "production.lot-held",
            "aggregate_type": "Lot",
            "aggregate_id": aggregate_id,
            "aggregate_version": version,
            "material_hold_id": f"H-{version}",
            "reason": "quality",
            "source_revision": f"CORE-{version}",
        },
        branch_id=branch_id,
    )


def connect_dict(dsn: str) -> Connection[DictRow]:
    return cast(
        Connection[DictRow],
        psycopg.connect(dsn, row_factory=cast(Any, dict_row)),
    )


def apply_event(
    dsn: str,
    store: PostgresProjectionStore,
    projector: Projector,
    item: ProjectionEvent,
) -> str:
    with (
        connect_dict(dsn) as connection,
        connection.transaction(),
    ):
        return store.apply(connection, projector, item).outcome


def restore(
    dsn: str,
    store: PostgresProjectionStore,
    world_id: str,
    branch_id: str = "PRIMARY",
) -> Projector:
    with (
        connect_dict(dsn) as connection,
        connection.transaction(),
    ):
        return store.restore_projector(
            connection, world_id=world_id, branch_id=branch_id
        )


def test_projection_revision_and_event_ledger_survive_restart(
    twin_database_dsn: str,
) -> None:
    store = PostgresProjectionStore("twin-test-live")
    projector = restore(twin_database_dsn, store, "PRIMARY")

    assert apply_event(twin_database_dsn, store, projector, event("E-1", 1)) == (
        "PROCESSED"
    )
    restored = restore(twin_database_dsn, store, "PRIMARY")
    assert restored.health()["source_revision"] == "E-1"
    assert restored.query("Lot", "LOT-1")["source_event_id"] == "E-1"  # type: ignore[index]

    assert apply_event(twin_database_dsn, store, restored, event("E-1", 1)) == (
        "DUPLICATE"
    )
    assert apply_event(twin_database_dsn, store, restored, event("E-2", 2)) == (
        "PROCESSED"
    )

    restarted = restore(twin_database_dsn, store, "PRIMARY")
    query = restarted.query("Lot", "LOT-1")
    assert query is not None
    assert query["source_event_id"] == "E-2"
    assert query["source_revision"] == "CORE-2"
    assert restarted.health()["source_revision"] == "E-2"
    with psycopg.connect(twin_database_dsn) as connection, connection.transaction():
        row = connection.execute(
            "SELECT count(*) FROM twin.applied_event " "WHERE consumer_scope = %s",
            (store.consumer_scope,),
        ).fetchone()
    assert row is not None and row[0] == 2


def test_world_and_branch_projections_restore_independently(
    twin_database_dsn: str,
) -> None:
    store = PostgresProjectionStore("twin-test-live")
    primary = Projector(ProjectionState("SHOP-2", "PRIMARY"))
    alternate = Projector(ProjectionState("SIM-1", "BRANCH-1"))

    assert (
        apply_event(
            twin_database_dsn,
            store,
            primary,
            event("E-P", 1, world_id="SHOP-2"),
        )
        == "PROCESSED"
    )
    assert (
        apply_event(
            twin_database_dsn,
            store,
            alternate,
            event("E-S", 1, world_id="SIM-1", branch_id="BRANCH-1"),
        )
        == "PROCESSED"
    )

    primary_state = restore(twin_database_dsn, store, "SHOP-2")
    alternate_state = restore(twin_database_dsn, store, "SIM-1", "BRANCH-1")
    assert primary_state.health()["source_revision"] == "E-P"
    assert alternate_state.health()["source_revision"] == "E-S"
    assert primary_state.state.applied_events == {"E-P": 1}
    assert alternate_state.state.applied_events == {"E-S": 1}


def _wire_event(
    event_id: str,
    version: int,
    *,
    world_id: str = "PRIMARY",
    aggregate_id: str = "LOT-GAP",
) -> bytes:
    event_type = "production.lot-held"
    return json.dumps(
        {
            "envelope": {
                "event_id": event_id,
                "event_type": event_type,
                "schema_version": 1,
                "producer": "manufacturing-core",
                "world_id": world_id,
                "correlation_id": f"CORR-{event_id}",
                "causation_id": None,
                "trace_id": f"TRACE-{event_id}",
                "occurred_at": {"clock": "UTC", "value": "2026-01-01T00:00:00Z"},
                "observed_at": "2026-01-01T00:00:01Z",
                "entity_refs": [
                    {"entity_type": "Lot", "id": aggregate_id, "revision": f"CORE-{version}"}
                ],
            },
            "payload": {
                "event_type": event_type,
                "aggregate_type": "Lot",
                "aggregate_id": aggregate_id,
                "aggregate_version": version,
                "source_revision": f"CORE-{version}",
                "material_hold_id": f"H-{version}",
                "reason": "quality",
            },
        }
    ).encode()


class _Delivery:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.acked = False
        self.naked = False

    async def ack(self) -> None:
        self.acked = True

    async def nak(self) -> None:
        self.naked = True


def test_consumer_persists_gap_staleness_until_the_missing_event_arrives(
    twin_database_dsn: str,
) -> None:
    store = PostgresProjectionStore("twin-test-gap")

    def connect() -> Connection[DictRow]:
        return connect_dict(twin_database_dsn)

    projector = Projector(ProjectionState("PRIMARY"))
    consumer = build_consumer(
        ledger=ProcessedMessageLedger("twin_consumer"),
        scope="twin-test-gap",
        connect=connect,
        projector=projector,
        projection_store=store,
        expected_world_id="PRIMARY",
    )
    context = DeliveryContext()

    first = _Delivery(_wire_event("E-1", 1))
    assert asyncio.run(consumer.handle(first, context)) == Outcome.PROCESSED
    assert first.acked and not first.naked

    gap = _Delivery(_wire_event("E-3", 3))
    with pytest.raises(ValueError, match="revision gap"):
        asyncio.run(consumer.handle(gap, context))
    assert gap.naked and not gap.acked

    later_gap = _Delivery(_wire_event("E-4", 4))
    with pytest.raises(ValueError, match="revision gap"):
        asyncio.run(consumer.handle(later_gap, context))
    assert later_gap.naked and not later_gap.acked

    unrelated = _Delivery(
        _wire_event("E-OTHER", 1, aggregate_id="LOT-OTHER")
    )
    assert asyncio.run(consumer.handle(unrelated, context)) == Outcome.PROCESSED
    assert projector.health()["status"] == "STALE"

    restored = restore(twin_database_dsn, store, "PRIMARY")
    assert restored.health()["status"] == "STALE"
    assert restored.health()["source_revision"] == "E-OTHER"

    missing = _Delivery(_wire_event("E-2", 2))
    assert asyncio.run(consumer.handle(missing, context)) == Outcome.PROCESSED
    assert projector.health()["status"] == "STALE"
    redelivery = _Delivery(_wire_event("E-3", 3))
    assert asyncio.run(consumer.handle(redelivery, context)) == Outcome.PROCESSED
    assert redelivery.acked and not redelivery.naked
    assert projector.health()["status"] == "STALE"

    last_gap = _Delivery(_wire_event("E-4", 4))
    assert asyncio.run(consumer.handle(last_gap, context)) == Outcome.PROCESSED
    assert last_gap.acked and not last_gap.naked

    caught_up = restore(twin_database_dsn, store, "PRIMARY")
    assert caught_up.health()["status"] == "FRESH"
    assert caught_up.health()["source_revision"] == "E-4"


def test_initial_gap_persists_without_fabricating_a_source_revision(
    twin_database_dsn: str,
) -> None:
    store = PostgresProjectionStore("twin-test-initial-gap")

    def connect() -> Connection[DictRow]:
        return connect_dict(twin_database_dsn)

    consumer = build_consumer(
        ledger=ProcessedMessageLedger("twin_consumer"),
        scope="twin-test-initial-gap",
        connect=connect,
        projector=Projector(ProjectionState("EMPTY")),
        projection_store=store,
        expected_world_id="EMPTY",
    )
    context = DeliveryContext()
    gap = _Delivery(_wire_event("E-2", 2, world_id="EMPTY", aggregate_id="LOT-FIRST"))

    with pytest.raises(ValueError, match="revision gap"):
        asyncio.run(consumer.handle(gap, context))
    assert gap.naked and not gap.acked

    stale = restore(twin_database_dsn, store, "EMPTY")
    assert stale.health()["status"] == "STALE"
    assert stale.health()["source_revision"] is None

    first = _Delivery(_wire_event("E-1", 1, world_id="EMPTY", aggregate_id="LOT-FIRST"))
    assert asyncio.run(consumer.handle(first, context)) == Outcome.PROCESSED
    assert restore(twin_database_dsn, store, "EMPTY").health()["status"] == "STALE"

    recovered = _Delivery(_wire_event("E-2", 2, world_id="EMPTY", aggregate_id="LOT-FIRST"))
    assert asyncio.run(consumer.handle(recovered, context)) == Outcome.PROCESSED
    fresh = restore(twin_database_dsn, store, "EMPTY")
    assert fresh.health()["status"] == "FRESH"
    assert fresh.health()["source_revision"] == "E-2"
