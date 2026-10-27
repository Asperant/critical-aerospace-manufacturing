"""Real PostgreSQL migration/mapping and scoped-role negative tests."""

from typing import LiteralString

import psycopg
import pytest
from conftest import Database
from manufacturing_core.database import connect, connect_runtime
from manufacturing_core.domain import (
    Equipment,
    Lot,
    ManufacturingRoute,
    ProductionOrder,
    RouteVisit,
    SerializedComponent,
)
from manufacturing_core.lifecycle import (
    ExecutionState,
    LotLifecycle,
    LotState,
    ProductionOrderLifecycle,
    ProductionOrderState,
    SerializedComponentLifecycle,
    SerializedComponentState,
)
from manufacturing_core.migrate import migrate
from manufacturing_core.repository import CoreRepository
from psycopg import errors, sql
from psycopg.rows import DictRow

pytestmark = pytest.mark.integration


def sample_route() -> ManufacturingRoute:
    return ManufacturingRoute(
        id="R-1",
        revision="route-r2",
        visits=tuple(
            RouteVisit(
                id=identity,
                revision="visit-r3",
                route_id="R-1",
                operation_class_id=operation,
                equipment_id="E-1",
            )
            for identity, operation in (
                ("V-9", "CNC"),
                ("V-2", "METROLOGY"),
                ("V-1", "CNC"),
            )
        ),
    )


def test_schema_creation_and_replay(database: Database) -> None:
    assert migrate(database.migration_dsn, database.runtime_role) is False
    with psycopg.connect(database.admin_dsn) as admin:
        tables = {
            row[0]
            for row in admin.execute(
                "SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'core'"
            ).fetchall()
        }
        assert tables == {
            "alembic_version",
            "schema_migration",
            "equipment",
            "manufacturing_route",
            "route_visit",
            "production_order",
            "lot",
            "serialized_component",
            "command_idempotency",
            "command_outcome",
            "production_order_state",
            "lot_state",
            "serialized_component_state",
            "material_hold",
        }
        assert admin.execute(
            "SELECT pg_catalog.pg_get_userbyid(nspowner) FROM pg_catalog.pg_namespace WHERE nspname = 'core'"
        ).fetchone() == (database.migration_role,)


def test_full_round_trip(connection: psycopg.Connection[DictRow]) -> None:
    repo = CoreRepository(connection)
    entities = (
        Equipment(id="E-1", revision="eq-r1"),
        sample_route(),
        ProductionOrder(id="O-1", revision="order-r3", route_id="R-1"),
        Lot(id="L-1", revision="lot-r4", order_id="O-1"),
        SerializedComponent(id="C-1", revision="component-r5", lot_id="L-1"),
    )
    for entity in entities:
        repo.insert(entity)
    for entity in entities:
        restored = repo.get(type(entity), entity.id)
        assert restored == entity
        assert restored is not None
        assert restored.model_dump_json() == entity.model_dump_json()
    restored_route = repo.get(ManufacturingRoute, "R-1")
    assert restored_route is not None
    assert [visit.id for visit in restored_route.visits] == ["V-9", "V-2", "V-1"]
    assert [visit.operation_class_id for visit in restored_route.visits] == [
        "CNC",
        "METROLOGY",
        "CNC",
    ]
    assert repo.get(Lot, "absent") is None


def test_lifecycle_state_round_trip(connection: psycopg.Connection[DictRow]) -> None:
    repo = CoreRepository(connection)
    repo.insert(Equipment(id="E-1", revision="eq-r1"))
    repo.insert(sample_route())
    repo.insert(ProductionOrder(id="O-1", revision="order-r1", route_id="R-1"))
    repo.insert(Lot(id="L-1", revision="lot-r1", order_id="O-1"))
    repo.insert(SerializedComponent(id="C-1", revision="component-r1", lot_id="L-1"))

    assert repo.get_state(ProductionOrderState, "O-1") == ProductionOrderState(
        id="O-1", revision="order-r1", lifecycle_state=ProductionOrderLifecycle.CREATED
    )
    assert repo.get_state(LotState, "L-1") == LotState(
        id="L-1",
        revision="lot-r1",
        lifecycle_state=LotLifecycle.CREATED,
        execution_state=ExecutionState.READY,
    )
    assert repo.get_state(SerializedComponentState, "C-1") == SerializedComponentState(
        id="C-1",
        revision="component-r1",
        lifecycle_state=SerializedComponentLifecycle.CREATED,
        execution_state=ExecutionState.READY,
    )


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO core.production_order VALUES ('O', 'r1', 'missing')",
        "INSERT INTO core.lot VALUES ('L', 'r1', 'missing')",
        "INSERT INTO core.serialized_component VALUES ('C', 'r1', 'missing')",
        "INSERT INTO core.route_visit VALUES ('missing', 'V', 'r1', 0, 'CNC', 'missing')",
    ],
)
def test_foreign_keys(
    connection: psycopg.Connection[DictRow], statement: LiteralString
) -> None:
    with pytest.raises(errors.ForeignKeyViolation), connection.transaction():
        connection.execute(statement)


@pytest.mark.parametrize("column", ["id", "revision"])
@pytest.mark.parametrize("value", ["", " \t\n", None])
def test_database_rejects_invalid_identity_revision(
    connection: psycopg.Connection[DictRow], column: str, value: str | None
) -> None:
    values: dict[str, str | None] = {"id": "E-1", "revision": "r1"}
    values[column] = value
    with pytest.raises(errors.IntegrityError), connection.transaction():
        connection.execute(
            "INSERT INTO core.equipment VALUES (%s, %s)",
            (values["id"], values["revision"]),
        )


def test_duplicate_identity(connection: psycopg.Connection[DictRow]) -> None:
    repo = CoreRepository(connection)
    equipment = Equipment(id="E-1", revision="r1")
    repo.insert(equipment)
    with pytest.raises(errors.UniqueViolation):
        repo.insert(equipment)
    assert repo.get(Equipment, "E-1") == equipment


@pytest.mark.parametrize(
    "visit_id,position,equipment",
    [("V-9", 9, "E-1"), ("new", 0, "E-1"), ("new", 9, "missing")],
)
def test_visit_integrity(
    connection: psycopg.Connection[DictRow],
    visit_id: str,
    position: int,
    equipment: str,
) -> None:
    repo = CoreRepository(connection)
    repo.insert(Equipment(id="E-1", revision="r1"))
    repo.insert(sample_route())
    with pytest.raises(errors.IntegrityError), connection.transaction():
        connection.execute(
            "INSERT INTO core.route_visit VALUES ('R-1', %s, 'r1', %s, 'CNC', %s)",
            (visit_id, position, equipment),
        )


def test_partial_route_rolled_back(connection: psycopg.Connection[DictRow]) -> None:
    repo = CoreRepository(connection)
    with pytest.raises(errors.ForeignKeyViolation):
        repo.insert(sample_route())
    assert repo.get(ManufacturingRoute, "R-1") is None


@pytest.mark.parametrize(
    "statement",
    [
        "CREATE TABLE core.forbidden (id text)",
        "SELECT * FROM core.schema_migration",
        "UPDATE core.equipment SET id = 'changed'",
        "DELETE FROM core.equipment",
    ],
)
def test_runtime_is_not_migrator(
    connection: psycopg.Connection[DictRow], statement: LiteralString
) -> None:
    with pytest.raises(errors.InsufficientPrivilege), connection.transaction():
        connection.execute(statement)


def test_runtime_transition_grants_are_column_scoped(
    connection: psycopg.Connection[DictRow],
) -> None:
    privileges = connection.execute(
        "SELECT pg_catalog.has_table_privilege(current_user, 'core.lot', 'UPDATE') AS lot_update, "
        "pg_catalog.has_column_privilege(current_user, 'core.lot', 'revision', 'UPDATE') AS lot_revision_update, "
        "pg_catalog.has_column_privilege(current_user, 'core.lot', 'order_id', 'UPDATE') AS lot_order_update, "
        "pg_catalog.has_table_privilege(current_user, 'core.material_hold', 'INSERT') AS hold_insert"
    ).fetchone()
    assert privileges == {
        "lot_update": False,
        "lot_revision_update": True,
        "lot_order_update": False,
        "hold_insert": True,
    }
    with pytest.raises(errors.InsufficientPrivilege), connection.transaction():
        connection.execute(
            "UPDATE core.lot SET order_id = 'forbidden' WHERE id = 'missing'"
        )


def test_cross_schema_write_denied(
    database: Database, connection: psycopg.Connection[DictRow]
) -> None:
    with psycopg.connect(database.admin_dsn, autocommit=True) as admin:
        admin.execute("CREATE SCHEMA twin")
        admin.execute("CREATE TABLE twin.private_state (id text)")
        try:
            with pytest.raises(errors.InsufficientPrivilege), connection.transaction():
                connection.execute(
                    "INSERT INTO twin.private_state VALUES ('forbidden')"
                )
        finally:
            admin.execute("DROP SCHEMA twin CASCADE")


def test_administrative_connection_rejected(database: Database) -> None:
    with pytest.raises(ValueError, match="administrative"):
        connect(database.admin_dsn)


def test_runtime_cannot_use_migration_identity(database: Database) -> None:
    with pytest.raises(ValueError, match="separately owned"):
        connect_runtime(database.migration_dsn)
    with pytest.raises(ValueError, match="differ"):
        migrate(database.migration_dsn, database.migration_role)


def test_runtime_membership_rejected(database: Database) -> None:
    with psycopg.connect(database.admin_dsn, autocommit=True) as admin:
        admin.execute(
            sql.SQL("GRANT {} TO {}").format(
                sql.Identifier(database.migration_role),
                sql.Identifier(database.runtime_role),
            )
        )
        try:
            with pytest.raises(ValueError, match="member|owned"):
                connect_runtime(database.runtime_dsn)
            with pytest.raises(ValueError, match="inherit"):
                migrate(database.migration_dsn, database.runtime_role)
        finally:
            admin.execute(
                sql.SQL("REVOKE {} FROM {}").format(
                    sql.Identifier(database.migration_role),
                    sql.Identifier(database.runtime_role),
                )
            )


def test_ledger_tampering_rejected(database: Database) -> None:
    with psycopg.connect(database.admin_dsn, autocommit=True) as admin:
        checksum = admin.execute("SELECT sha256 FROM core.schema_migration").fetchone()
        assert checksum is not None
        admin.execute("UPDATE core.schema_migration SET sha256 = 'tampered'")
        try:
            with pytest.raises(ValueError, match="checksum"):
                migrate(database.migration_dsn, database.runtime_role)
        finally:
            admin.execute(
                "UPDATE core.schema_migration SET sha256 = %s", (checksum[0],)
            )
