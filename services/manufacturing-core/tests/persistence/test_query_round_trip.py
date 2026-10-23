"""Transport-free query contract from real PostgreSQL via Core's repository."""

from pathlib import Path

import psycopg
import pytest
from conftest import Database
from manufacturing_core.database import connect_runtime
from manufacturing_core.domain import Lot, ProductionOrder, SerializedComponent
from manufacturing_core.query_v1 import (
    CONTRACT_VERSION,
    OrderQueryRequestV1,
    OrderQueryResultV1,
    QueryReferenceError,
    query_order_v1,
)
from manufacturing_core.repository import CoreRepository
from psycopg.rows import DictRow

pytestmark = pytest.mark.integration
CONTRACTS = Path(__file__).resolve().parents[2] / "contracts" / "v1"


@pytest.mark.parametrize("scenario", ["normal", "reentrant"])
def test_persistence_to_read_only_query(database: Database, scenario: str) -> None:
    expected = OrderQueryResultV1.model_validate_json(
        (CONTRACTS / f"order-query.{scenario}.json").read_text()
    )
    try:
        with connect_runtime(database.runtime_dsn) as setup:
            repo = CoreRepository(setup)
            with setup.transaction():
                for entity in (
                    *reversed(expected.equipment),
                    expected.route,
                    expected.order,
                    *reversed(expected.lots),
                    *reversed(expected.components),
                ):
                    repo.insert(entity)
                # A second order sharing the route must not leak into the result.
                repo.insert(
                    ProductionOrder(
                        id="O-UNRELATED", revision="r1", route_id=expected.route.id
                    )
                )
                repo.insert(
                    Lot(id="L-UNRELATED", revision="r1", order_id="O-UNRELATED")
                )
                repo.insert(
                    SerializedComponent(
                        id="C-UNRELATED", revision="r1", lot_id="L-UNRELATED"
                    )
                )
        with connect_runtime(database.runtime_dsn) as reader, reader.transaction():
            reader.execute("SET TRANSACTION READ ONLY")
            result = query_order_v1(
                CoreRepository(reader),
                OrderQueryRequestV1(
                    contract_version=CONTRACT_VERSION,
                    order_id=expected.order.id,
                ),
            )
            assert result == expected
            assert result.model_dump_json() == expected.model_dump_json()
            assert reader.execute("SHOW transaction_read_only").fetchone() == {
                "transaction_read_only": "on"
            }
    finally:
        # Only this test fixture's isolated database; runtime cannot DELETE.
        with psycopg.connect(database.admin_dsn) as admin:
            admin.execute(
                "TRUNCATE core.serialized_component, core.lot, core.production_order, core.route_visit, core.manufacturing_route, core.equipment"
            )


def test_missing_order_is_explicit(connection: psycopg.Connection[DictRow]) -> None:
    with pytest.raises(QueryReferenceError) as failure:
        query_order_v1(
            CoreRepository(connection),
            OrderQueryRequestV1(
                contract_version=CONTRACT_VERSION,
                order_id="O-MISSING",
            ),
        )
    assert failure.value.code == "ORDER_NOT_FOUND"
