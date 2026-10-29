from __future__ import annotations

import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import psycopg
from manufacturing_core.commands import (
    CommandTarget,
    DispatchLot,
    FreshnessPrecondition,
)
from manufacturing_core.domain import (
    Equipment,
    Lot,
    ManufacturingRoute,
    ProductionOrder,
    RouteVisit,
)
from manufacturing_core.repository import CoreRepository
from manufacturing_core.transitions import CoreTransitionService
from psycopg.rows import DictRow, dict_row


def main() -> None:
    dsn = os.environ["CAP_CORE_DSN"]
    with psycopg.Connection[DictRow].connect(dsn, row_factory=dict_row) as connection:
        repository = CoreRepository(connection)
        with connection.transaction():
            if repository.get(Equipment, "DEMO-CNC-01") is None:
                repository.insert(
                    Equipment(id="DEMO-CNC-01", revision="equipment-rev-1")
                )
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
                    ProductionOrder(
                        id="DEMO-ORDER-001",
                        revision="order-rev-1",
                        route_id="DEMO-ROUTE",
                    )
                )
            if repository.get(Lot, "DEMO-LOT-001") is None:
                repository.insert(
                    Lot(
                        id="DEMO-LOT-001",
                        revision="lot-rev-1",
                        order_id="DEMO-ORDER-001",
                    )
                )
                # Provision one normal, visible Twin state before the presenter
                # runs the hold command.  The queued state is fixture setup; the
                # dispatch itself uses the real Core transition service and
                # transactional outbox, so the first Twin projection is still a
                # genuine Core event rather than a hand-written Twin row.
                connection.execute(
                    "UPDATE core.lot_state SET execution_state='QUEUED' "
                    "WHERE id='DEMO-LOT-001'"
                )
                dispatch = DispatchLot(
                    command_id=uuid5(
                        NAMESPACE_URL, "cap-demo/WP-DOC-004/DEMO-LOT-001/dispatch"
                    ),
                    idempotency_key="wp-doc-004-demo-dispatch",
                    world_id="DEMO-WORLD",
                    correlation_id="wp-doc-004-demo-dispatch",
                    target=CommandTarget(entity_type="Lot", entity_id="DEMO-LOT-001"),
                    expected=FreshnessPrecondition(expected_revision="lot-rev-1"),
                    operation_id="DEMO-VISIT-1",
                    resource_id="DEMO-CNC-01",
                )
                CoreTransitionService(connection).dispatch_lot(
                    (),
                    dispatch,
                    resource_available=True,
                    expected_world_id="DEMO-WORLD",
                )
    print("seeded DEMO-WORLD / DEMO-LOT-001 through Core repository")
    Path("/tmp/cap-demo-seed.done").touch()


if __name__ == "__main__":
    main()
