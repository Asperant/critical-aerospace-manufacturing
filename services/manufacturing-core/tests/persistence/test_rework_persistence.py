"""WP-CORE-004 slice 2; real disposable PostgreSQL, restricted runtime role."""

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
    Equipment,
    Lot,
    ManufacturingRoute,
    ProductionOrder,
    RouteVisit,
    SerializedComponent,
)
from manufacturing_core.migrate import REWORK_TABLES, migrate
from manufacturing_core.repository import CoreRepository
from manufacturing_core.rework import (
    ComponentExecutionHistory,
    ExecutionSegment,
    ProcessExecutionRecord,
    ReworkDirective,
    ReworkExecutionSegment,
)
from manufacturing_core.rework_repository import ReworkHistoryRepository
from psycopg import errors, sql
from psycopg.conninfo import make_conninfo
from psycopg.rows import DictRow

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def rework_database(database: Database) -> Iterator[Database]:
    # Separate DB preserves the unchanged initial-schema tests, regardless of
    # collection order. Reuse only the fixture's nonadministrative role identities.
    name = "rework_test_" + uuid4().hex[:12]
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
def rework_connection(
    rework_database: Database,
) -> Iterator[psycopg.Connection[DictRow]]:
    with (
        connect_runtime(rework_database.runtime_dsn) as conn,
        conn.transaction(force_rollback=True),
    ):
        yield conn


def seed(
    conn: psycopg.Connection[DictRow],
) -> tuple[ComponentExecutionHistory, ReworkExecutionSegment]:
    identity = uuid4().hex
    equipment_id, lot_id, component_id = (
        "E-" + identity,
        "L-" + identity,
        "C-" + identity,
    )
    route = ManufacturingRoute(
        id="R-" + identity,
        revision="route-r1",
        visits=tuple(
            RouteVisit(
                id=step,
                revision="visit-r1",
                route_id="R-" + identity,
                operation_class_id=operation,
                equipment_id=equipment_id,
            )
            for step, operation in (("060", "CNC"), ("090", "INSPECTION"))
        ),
    )
    repo = CoreRepository(conn)
    for entity in (
        Equipment(id=equipment_id, revision="equipment-r1"),
        route,
        ProductionOrder(id="O-" + identity, revision="order-r1", route_id=route.id),
        Lot(id=lot_id, revision="lot-r1", order_id="O-" + identity),
        SerializedComponent(id=component_id, revision="component-r1", lot_id=lot_id),
    ):
        repo.insert(entity)

    def executions(prefix: str, hour: int) -> tuple[ProcessExecutionRecord, ...]:
        return tuple(
            ProcessExecutionRecord(
                id=prefix + "-" + identity + "-" + step,
                revision="execution-r1",
                component_id=component_id,
                lot_id=lot_id,
                route_visit_id=step,
                equipment_id=equipment_id,
                started_at=datetime(2026, 10, 24, hour, index * 2, tzinfo=UTC),
                ended_at=datetime(2026, 10, 24, hour, index * 2, tzinfo=UTC)
                + timedelta(minutes=1),
            )
            for index, step in enumerate(("060", "090"))
        )

    original = ComponentExecutionHistory(
        component_id=component_id,
        original=ExecutionSegment(route=route, executions=executions("original", 10)),
    )
    # Same route identity, new historical revision: never overwrite current route.
    rework_route = ManufacturingRoute.model_validate(
        {**route.model_dump(), "revision": "route-r2"}
    )
    segment = ReworkExecutionSegment(
        route=rework_route,
        executions=executions("rework", 11),
        directive=ReworkDirective(
            id="D-" + identity,
            revision="directive-r1",
            component_id=component_id,
            reason="inspection anomaly",
            originating_inspection_id="I-" + identity,
            origin_execution_id=original.original.executions[-1].id,
            return_visit_id="060",
            rework_route_id=route.id,
            rework_route_revision="route-r2",
            related_defect_id="DEFECT-" + identity,
            related_incident_id="INCIDENT-" + identity,
            current_rework_count=0,
            approval_state="APPROVED",
            policy_state="RECORDED_BY_CORE",
        ),
    )
    return original, segment


def counts(conn: psycopg.Connection[DictRow]) -> dict[str, int]:
    result = {}
    for table in REWORK_TABLES:
        row = conn.execute(
            sql.SQL("SELECT count(*) AS n FROM core.{}").format(sql.Identifier(table))
        ).fetchone()
        assert row is not None
        result[table] = row["n"]
    return result


@pytest.mark.parametrize("count", [0, 2**70])
def test_committed_append_round_trip_and_directive_linkage(
    rework_database: Database, count: int
) -> None:
    with connect_runtime(rework_database.runtime_dsn) as conn:
        original, segment = seed(conn)
        data = segment.model_dump()
        data["directive"]["current_rework_count"] = count
        if count:
            data["directive"]["related_defect_id"] = None
            data["directive"]["related_incident_id"] = None
        segment = ReworkExecutionSegment.model_validate(data)
        repo = ReworkHistoryRepository(conn)
        repo.create(original)
        assert repo.append_rework(
            original.component_id, segment
        ) == original.append_rework(segment)
        second_data = segment.model_dump()
        second_data["directive"]["id"] += "-second"
        second_data["directive"]["origin_execution_id"] = segment.executions[-1].id
        second_data["directive"]["current_rework_count"] = count + 1
        for record in second_data["executions"]:
            record["id"] += "-second"
            record["started_at"] += timedelta(hours=1)
            record["ended_at"] += timedelta(hours=1)
        second = ReworkExecutionSegment.model_validate(second_data)
        expected = original.append_rework(segment).append_rework(second)
        assert repo.append_rework(original.component_id, second) == expected
    # A distinct read-only runtime connection reads committed relational records.
    with connect_runtime(rework_database.runtime_dsn) as conn, conn.transaction():
        conn.execute("SET TRANSACTION READ ONLY")
        restored = ReworkHistoryRepository(conn).get(original.component_id)
        assert restored == expected
        assert restored is not None
        assert restored.model_dump_json() == expected.model_dump_json()
        linkage = conn.execute(
            "SELECT d.id, d.origin_execution_id, e.component_id FROM core.rework_segment s "
            "JOIN core.rework_directive d ON d.id = s.directive_id "
            "JOIN core.rework_execution e ON e.id = d.origin_execution_id "
            "WHERE s.component_id = %s AND s.position = 1",
            (original.component_id,),
        ).fetchone()
        assert linkage == {
            "id": segment.directive.id,
            "origin_execution_id": segment.directive.origin_execution_id,
            "component_id": original.component_id,
        }
        current = CoreRepository(conn).get(
            ManufacturingRoute, original.original.route.id
        )
        assert current == original.original.route


def test_existing_history_cannot_be_replaced(
    rework_connection: psycopg.Connection[DictRow],
) -> None:
    original, segment = seed(rework_connection)
    repo = ReworkHistoryRepository(rework_connection)
    expected = original.append_rework(segment)
    repo.create(expected)
    altered = expected.model_dump()
    altered["original"]["route"]["revision"] = "replacement"
    with pytest.raises(errors.UniqueViolation):
        repo.create(ComponentExecutionHistory.model_validate(altered))
    assert repo.get(original.component_id) == expected
    with pytest.raises(ValueError, match="duplicate rework directive"):
        repo.append_rework(original.component_id, segment)
    assert repo.get(original.component_id) == expected


def test_failed_append_rolls_back_all_partial_rows(
    rework_connection: psycopg.Connection[DictRow],
) -> None:
    original, segment = seed(rework_connection)
    repo = ReworkHistoryRepository(rework_connection)
    repo.create(original)
    before = counts(rework_connection)
    invalid = segment.model_dump()
    invalid["executions"][-1]["equipment_id"] = "missing-equipment"
    with pytest.raises(errors.ForeignKeyViolation):
        repo.append_rework(
            original.component_id, ReworkExecutionSegment.model_validate(invalid)
        )
    assert counts(rework_connection) == before
    assert repo.get(original.component_id) == original
    # Failed savepoint did not abort caller transaction; valid retry can append.
    repo.append_rework(original.component_id, segment)
    assert repo.get(original.component_id) == original.append_rework(segment)


def test_failed_create_rolls_back_original_and_rework(
    rework_connection: psycopg.Connection[DictRow],
) -> None:
    original, segment = seed(rework_connection)
    repo = ReworkHistoryRepository(rework_connection)
    before = counts(rework_connection)
    invalid = segment.model_dump()
    invalid["executions"][-1]["equipment_id"] = "missing-equipment"
    with pytest.raises(errors.ForeignKeyViolation):
        repo.create(
            original.append_rework(ReworkExecutionSegment.model_validate(invalid))
        )
    assert repo.get(original.component_id) is None
    assert counts(rework_connection) == before


def test_outer_rollback_leaves_no_history(
    rework_connection: psycopg.Connection[DictRow],
) -> None:
    original, segment = seed(rework_connection)
    repo = ReworkHistoryRepository(rework_connection)
    before = counts(rework_connection)
    with rework_connection.transaction(force_rollback=True):
        repo.create(original)
        repo.append_rework(original.component_id, segment)
        assert repo.get(original.component_id) == original.append_rework(segment)
    assert repo.get(original.component_id) is None
    assert counts(rework_connection) == before


@pytest.mark.parametrize("table", REWORK_TABLES)
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE", "TRUNCATE"])
def test_runtime_cannot_rewrite_history(
    rework_connection: psycopg.Connection[DictRow], table: str, operation: str
) -> None:
    original, segment = seed(rework_connection)
    repo = ReworkHistoryRepository(rework_connection)
    expected = original.append_rework(segment)
    repo.create(expected)
    templates: dict[str, LiteralString] = {
        "UPDATE": "UPDATE core.{} SET component_id = component_id",
        "DELETE": "DELETE FROM core.{}",
        "TRUNCATE": "TRUNCATE core.{}",
    }
    with pytest.raises(errors.InsufficientPrivilege), rework_connection.transaction():
        rework_connection.execute(
            sql.SQL(templates[operation]).format(sql.Identifier(table))
        )
    assert repo.get(original.component_id) == expected


def test_append_requires_existing_history(
    rework_connection: psycopg.Connection[DictRow],
) -> None:
    original, segment = seed(rework_connection)
    repo = ReworkHistoryRepository(rework_connection)
    before = counts(rework_connection)
    assert repo.get(original.component_id) is None
    with pytest.raises(ValueError, match="history does not exist"):
        repo.append_rework(original.component_id, segment)
    assert counts(rework_connection) == before


def test_migration_replay_preserves_base_runner(rework_database: Database) -> None:
    assert migrate(rework_database.migration_dsn, rework_database.runtime_role) is False


def test_migration_checksum_tampering_rejected(rework_database: Database) -> None:
    with psycopg.connect(rework_database.admin_dsn, autocommit=True) as admin:
        checksum = admin.execute(
            "SELECT sha256 FROM core.schema_migration "
            "WHERE version = '0006_rework_history'"
        ).fetchone()
        assert checksum is not None
        admin.execute(
            "UPDATE core.schema_migration SET sha256 = 'tampered' "
            "WHERE version = '0006_rework_history'"
        )
        try:
            with pytest.raises(ValueError, match="checksum"):
                migrate(rework_database.migration_dsn, rework_database.runtime_role)
        finally:
            admin.execute(
                "UPDATE core.schema_migration SET sha256 = %s "
                "WHERE version = '0006_rework_history'",
                (checksum[0],),
            )
