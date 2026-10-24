"""WP-CORE-004 slice 4: real disposable PostgreSQL, synthetic lineage facts."""

from collections.abc import Iterator
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import LiteralString
from uuid import uuid4

import psycopg
import pytest
from conftest import Database
from manufacturing_core.database import connect_runtime
from manufacturing_core.domain import (
    Lot,
    ManufacturingRoute,
    ProductionOrder,
    SerializedComponent,
)
from manufacturing_core.lineage import (
    LotLineageEvent,
    LotLineageHistory,
    LotMembershipSnapshot,
)
from manufacturing_core.lineage_migrate import TABLES, migrate
from manufacturing_core.lineage_repository import LotLineageRepository
from manufacturing_core.repository import CoreRepository
from psycopg import errors, sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow
from pydantic import ValidationError

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def lineage_database(database: Database) -> Iterator[Database]:
    # Separate DB preserves the unchanged initial-schema tests, regardless of
    # collection order. Reuse only the fixture's nonadministrative role identities.
    name = "lineage_test_" + uuid4().hex[:12]
    with psycopg.connect(database.admin_dsn, autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        try:
            admin.execute(
                sql.SQL("GRANT CREATE ON DATABASE {} TO {}").format(
                    sql.Identifier(name), sql.Identifier(database.migration_role)
                )
            )
            settings = replace(
                database,
                admin_dsn=make_conninfo(database.admin_dsn, dbname=name),
                migration_dsn=make_conninfo(database.migration_dsn, dbname=name),
                runtime_dsn=make_conninfo(database.runtime_dsn, dbname=name),
            )
            assert migrate(settings.migration_dsn, settings.runtime_role) is True
            admin.execute(
                sql.SQL("REVOKE CREATE ON DATABASE {} FROM {}").format(
                    sql.Identifier(name), sql.Identifier(database.migration_role)
                )
            )
            yield settings
        finally:
            admin.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )


@pytest.fixture
def lineage_connection(
    lineage_database: Database,
) -> Iterator[psycopg.Connection[DictRow]]:
    with (
        connect_runtime(lineage_database.runtime_dsn) as conn,
        conn.transaction(force_rollback=True),
    ):
        yield conn


def facts() -> LotLineageHistory:
    world = uuid4().hex

    def lot(name: str, *components: str) -> LotMembershipSnapshot:
        return LotMembershipSnapshot(
            world_id=world, lot_id=name, component_ids=components
        )

    def event(
        kind: str,
        parents: tuple[str, ...],
        children: tuple[LotMembershipSnapshot, ...],
        n: int,
    ) -> LotLineageEvent:
        return LotLineageEvent.model_validate(
            {
                "id": f"E{n}",
                "revision": "opaque-rev",
                "kind": kind,
                "source_event_id": f"SOURCE{n}",
                "world_id": world,
                "reason": "synthetic governed fact",
                "parent_lot_ids": parents,
                "children": children,
                "occurred_at": datetime(2026, 10, 24, 10, tzinfo=UTC)
                + timedelta(minutes=n),
                "effective_from": datetime(2026, 10, 24, 11, tzinfo=UTC)
                + timedelta(minutes=n),
                "recorded_at": datetime(2026, 10, 23, tzinfo=UTC),
            }
        )

    return LotLineageHistory(
        world_id=world,
        roots=(lot("ROOT", "C2", "C1", "C3"),),
        events=(
            event("SPLIT", ("ROOT",), (lot("A", "C2", "C1"), lot("B", "C3")), 1),
            event("SPLIT", ("A",), (lot("A1", "C1"), lot("A2", "C2")), 2),
            event("MERGE", ("B", "A1"), (lot("M", "C3", "C1"),), 3),
            event("MERGE", ("M", "A2"), (lot("FINAL", "C2", "C3", "C1"),), 4),
        ),
    )


def seed(conn: psycopg.Connection[DictRow]) -> LotLineageHistory:
    history = facts()
    repo = CoreRepository(conn)
    repo.insert(ManufacturingRoute(id="R", revision="r", visits=()))
    repo.insert(ProductionOrder(id="O", revision="r", route_id="R"))
    for name in ("ROOT", "A", "B", "A1", "A2", "M", "FINAL"):
        repo.insert(Lot(id=name, revision="r", order_id="O"))
    for name in ("C1", "C2", "C3"):
        repo.insert(SerializedComponent(id=name, revision="r", lot_id="ROOT"))
    return history


def counts(conn: psycopg.Connection[DictRow]) -> list[int]:
    result: list[int] = []
    for table in TABLES:
        row = conn.execute(
            sql.SQL("SELECT count(*) AS n FROM core.{}").format(sql.Identifier(table))
        ).fetchone()
        assert row is not None
        result.append(row["n"])
    return result


@pytest.mark.parametrize(
    "variant", ["split", "merge", "generations", "out_of_order", "empty"]
)
def test_round_trip(
    lineage_connection: psycopg.Connection[DictRow], variant: str
) -> None:
    h = seed(lineage_connection)
    if variant == "split":
        h = LotLineageHistory(world_id=h.world_id, roots=h.roots, events=h.events[:1])
    elif variant == "merge":
        h = LotLineageHistory(
            world_id=h.world_id,
            roots=h.events[0].children,
            events=(
                LotLineageEvent.model_validate(
                    {**h.events[3].model_dump(), "parent_lot_ids": ("B", "A")}
                ),
            ),
        )
    elif variant == "out_of_order":
        h = LotLineageHistory(
            world_id=h.world_id, roots=h.roots, events=tuple(reversed(h.events))
        )
    elif variant == "empty":
        h = LotLineageHistory(world_id=h.world_id, roots=())
    repo = LotLineageRepository(lineage_connection)
    assert repo.get(h.world_id) is None
    repo.create(h)
    assert repo.get(h.world_id) == h
    # History storage must not change canonical current membership.
    assert CoreRepository(lineage_connection).get(
        SerializedComponent, "C1"
    ) == SerializedComponent(id="C1", revision="r", lot_id="ROOT")


def test_append_preserves_history(
    lineage_connection: psycopg.Connection[DictRow],
) -> None:
    h = seed(lineage_connection)
    repo = LotLineageRepository(lineage_connection)
    current = LotLineageHistory(world_id=h.world_id, roots=h.roots)
    repo.create(current)
    for event in h.events:
        before = current
        current = repo.append(h.world_id, event)
        assert current.events[:-1] == before.events
        assert repo.get(h.world_id) == current
    assert current == h


def test_duplicate_create_and_append_cannot_overwrite(
    lineage_connection: psycopg.Connection[DictRow],
) -> None:
    h = seed(lineage_connection)
    repo = LotLineageRepository(lineage_connection)
    repo.create(h)
    before = counts(lineage_connection)
    with pytest.raises(errors.UniqueViolation):
        repo.create(LotLineageHistory(world_id=h.world_id, roots=()))
    with pytest.raises(ValidationError):
        repo.append(h.world_id, h.events[0])
    assert repo.get(h.world_id) == h
    assert counts(lineage_connection) == before


@pytest.mark.parametrize(
    "statement",
    [
        "UPDATE core.lineage_history SET world_id = world_id",
        "UPDATE core.lineage_event SET reason = 'changed'",
        "UPDATE core.lineage_lot SET child_position = 99",
        "UPDATE core.lineage_parent SET lot_id = 'FINAL'",
        "UPDATE core.lineage_membership SET component_id = 'C3'",
        "DELETE FROM core.lineage_event",
        "TRUNCATE core.lineage_history CASCADE",
    ],
)
def test_runtime_cannot_rewrite(
    lineage_connection: psycopg.Connection[DictRow], statement: LiteralString
) -> None:
    h = seed(lineage_connection)
    repo = LotLineageRepository(lineage_connection)
    repo.create(h)
    with pytest.raises(errors.InsufficientPrivilege), lineage_connection.transaction():
        lineage_connection.execute(statement)
    assert repo.get(h.world_id) == h


@pytest.mark.parametrize(
    "invalid",
    ["unknown", "conservation", "reversed_time", "consumed", "world", "cycle"],
)
@pytest.mark.parametrize("path", ["create", "append"])
def test_invalid_ancestry_rejected(
    lineage_connection: psycopg.Connection[DictRow], invalid: str, path: str
) -> None:
    h = seed(lineage_connection)
    repo = LotLineageRepository(lineage_connection)
    prefix = LotLineageHistory(world_id=h.world_id, roots=h.roots, events=h.events[:1])
    repo.create(prefix)
    data = h.events[1].model_dump()
    if invalid == "unknown":
        data["parent_lot_ids"] = ("UNKNOWN",)
    elif invalid == "conservation":
        data["children"][0]["component_ids"] = ("C3",)
    elif invalid == "reversed_time":
        data["effective_from"] = h.events[0].effective_from - timedelta(days=1)
    elif invalid == "consumed":
        data["parent_lot_ids"] = ("ROOT",)
    elif invalid == "world":
        data["world_id"] = "OTHER"
    else:
        data["parent_lot_ids"] = ("A1",)
    # model_construct bypass must not bypass repository revalidation.
    data["children"] = tuple(
        LotMembershipSnapshot.model_validate(c) for c in data["children"]
    )
    bad = LotLineageEvent.model_construct(**data)
    before = counts(lineage_connection)
    with pytest.raises(ValidationError):
        if path == "append":
            repo.append(h.world_id, bad)
        else:
            repo.create(
                LotLineageHistory.model_construct(
                    world_id=h.world_id, roots=h.roots, events=(h.events[0], bad)
                )
            )
    assert counts(lineage_connection) == before
    assert repo.get(h.world_id) == prefix


@pytest.mark.parametrize("path", ["create", "append"])
def test_foreign_key_failure_rolls_back_partial_rows(
    lineage_connection: psycopg.Connection[DictRow], path: str
) -> None:
    h = seed(lineage_connection)
    data = h.events[0].model_dump()
    data["children"][1]["lot_id"] = "NOT_CREATED"
    bad = LotLineageEvent.model_validate(data)
    repo = LotLineageRepository(lineage_connection)
    prefix = LotLineageHistory(world_id=h.world_id, roots=h.roots)
    if path == "append":
        repo.create(prefix)
    before = counts(lineage_connection)
    with pytest.raises(errors.ForeignKeyViolation):
        if path == "append":
            repo.append(h.world_id, bad)
        else:
            repo.create(prefix.append(bad))
    assert counts(lineage_connection) == before
    assert repo.get(h.world_id) == (prefix if path == "append" else None)


def test_caller_rollback_removes_successful_history(
    lineage_connection: psycopg.Connection[DictRow],
) -> None:
    h = seed(lineage_connection)
    repo = LotLineageRepository(lineage_connection)
    before = counts(lineage_connection)
    with lineage_connection.transaction(force_rollback=True):
        repo.create(LotLineageHistory(world_id=h.world_id, roots=h.roots))
        for event in h.events:
            repo.append(h.world_id, event)
        assert repo.get(h.world_id) == h
    assert counts(lineage_connection) == before
    assert repo.get(h.world_id) is None


def test_migration_replay(lineage_database: Database) -> None:
    assert (
        migrate(lineage_database.migration_dsn, lineage_database.runtime_role) is False
    )
