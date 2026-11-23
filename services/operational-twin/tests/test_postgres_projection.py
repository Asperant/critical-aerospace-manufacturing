"""Real PostgreSQL persistence for the rebuildable Twin projection."""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any, LiteralString, cast

import psycopg
import pytest
from operational_twin import (
    PostgresProjectionStore,
    ProjectionEvent,
    ProjectionState,
    Projector,
)
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
        migration = (Path(__file__).parents[1] / "migrations/0001_twin.sql").read_text(
            encoding="utf-8"
        )
        with psycopg.connect(dsn) as connection:
            for statement in migration.split(";"):
                if statement.strip():
                    connection.execute(sql.SQL(cast(LiteralString, statement)))
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
