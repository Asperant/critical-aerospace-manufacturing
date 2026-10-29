from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from manufacturing_core.domain import Equipment, Lot, ManufacturingRoute, ProductionOrder, RouteVisit
from manufacturing_core.repository import CoreRepository


def main() -> None:
    dsn = os.environ["CAP_CORE_DSN"]
    with psycopg.connect(dsn, row_factory=dict_row) as connection:
        repository = CoreRepository(connection)
        with connection.transaction():
            if repository.get(Equipment, "DEMO-CNC-01") is None:
                repository.insert(Equipment(id="DEMO-CNC-01", revision="equipment-rev-1"))
            if repository.get(ManufacturingRoute, "DEMO-ROUTE") is None:
                repository.insert(
                    ManufacturingRoute(
                        id="DEMO-ROUTE",
                        revision="route-rev-1",
                        visits=(
                            RouteVisit(
                                id="DEMO-VISIT-1",
                                revision="visit-rev-1",
                                route_id="DEMO-ROUTE",
                                operation_class_id="ROUGH-MACHINING",
                                equipment_id="DEMO-CNC-01",
                            ),
                        ),
                    )
                )
            if repository.get(ProductionOrder, "DEMO-ORDER-001") is None:
                repository.insert(
                    ProductionOrder(id="DEMO-ORDER-001", revision="order-rev-1", route_id="DEMO-ROUTE")
                )
            if repository.get(Lot, "DEMO-LOT-001") is None:
                repository.insert(
                    Lot(id="DEMO-LOT-001", revision="lot-rev-1", order_id="DEMO-ORDER-001")
                )
    print("seeded DEMO-WORLD / DEMO-LOT-001 through Core repository")
    Path("/tmp/cap-demo-seed.done").touch()


if __name__ == "__main__":
    main()
