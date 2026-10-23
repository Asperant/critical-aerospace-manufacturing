"""Internal insert/read mapping. Caller owns the transaction and authorization.

No endpoint, generic update, lifecycle transition or externally published query
contract is provided. Errors propagate so the caller can roll back the unit of work.
"""

from typing import TypeVar

import psycopg
from psycopg import sql
from psycopg.rows import DictRow

from manufacturing_core.domain import (
    Entity,
    Equipment,
    Lot,
    ManufacturingRoute,
    ProductionOrder,
    RouteVisit,
    SerializedComponent,
)

T = TypeVar("T", bound=Entity)
TABLES: dict[type[Entity], str] = {
    Equipment: "equipment",
    ManufacturingRoute: "manufacturing_route",
    ProductionOrder: "production_order",
    Lot: "lot",
    SerializedComponent: "serialized_component",
}


class CoreRepository:
    def __init__(self, connection: psycopg.Connection[DictRow]) -> None:
        self.connection = connection

    def insert(self, entity: Entity) -> None:
        table = TABLES[type(entity)]
        data = entity.model_dump(exclude={"visits"})
        # Nested transaction provides a savepoint when the caller is already
        # in a transaction; a failed visit cannot leave a partial route.
        with self.connection.transaction():
            self.connection.execute(
                sql.SQL("INSERT INTO core.{} ({}) VALUES ({})").format(
                    sql.Identifier(table),
                    sql.SQL(", ").join(map(sql.Identifier, data)),
                    sql.SQL(", ").join(sql.Placeholder() for _ in data),
                ),
                list(data.values()),
            )
            if isinstance(entity, ManufacturingRoute):
                for position, visit in enumerate(entity.visits):
                    self.connection.execute(
                        "INSERT INTO core.route_visit "
                        "(route_id, id, revision, position, operation_class_id, equipment_id) "
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (
                            visit.route_id,
                            visit.id,
                            visit.revision,
                            position,
                            visit.operation_class_id,
                            visit.equipment_id,
                        ),
                    )

    def get(self, model: type[T], identity: str) -> T | None:
        row = self.connection.execute(
            sql.SQL("SELECT * FROM core.{} WHERE id = %s").format(
                sql.Identifier(TABLES[model])
            ),
            (identity,),
        ).fetchone()
        if row is None:
            return None
        if model is ManufacturingRoute:
            visits = self.connection.execute(
                "SELECT route_id, id, revision, operation_class_id, equipment_id "
                "FROM core.route_visit WHERE route_id = %s ORDER BY position",
                (identity,),
            ).fetchall()
            row["visits"] = tuple(RouteVisit.model_validate(visit) for visit in visits)
        return model.model_validate(row)

    def lots_for_order(self, order_id: str) -> tuple[Lot, ...]:
        rows = self.connection.execute(
            "SELECT id, revision, order_id FROM core.lot WHERE order_id = %s ORDER BY id",
            (order_id,),
        ).fetchall()
        return tuple(Lot.model_validate(row) for row in rows)

    def components_for_lot(self, lot_id: str) -> tuple[SerializedComponent, ...]:
        rows = self.connection.execute(
            "SELECT id, revision, lot_id FROM core.serialized_component "
            "WHERE lot_id = %s ORDER BY id",
            (lot_id,),
        ).fetchall()
        return tuple(SerializedComponent.model_validate(row) for row in rows)
