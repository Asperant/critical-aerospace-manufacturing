import json
import logging

import pytest
from conftest import Database
from manufacturing_core.database import connect_runtime
from manufacturing_core.observability import health
from manufacturing_core.query_v1 import (
    OrderQueryRequestV1,
    QueryReferenceError,
    query_order_v1,
)
from manufacturing_core.repository import CoreRepository

pytestmark = pytest.mark.integration


def test_runtime_health_and_admin_rejection(database: Database) -> None:
    assert health(database.runtime_dsn).status == "READY"
    assert health(database.admin_dsn).status == "UNAVAILABLE"
    assert health(database.migration_dsn).status == "UNAVAILABLE"


def test_query_failure_propagates_correlation(
    database: Database, caplog: pytest.LogCaptureFixture
) -> None:
    with (
        connect_runtime(database.runtime_dsn) as conn,
        caplog.at_level(logging.INFO, logger="manufacturing_core"),
        pytest.raises(QueryReferenceError),
    ):
        query_order_v1(
            CoreRepository(conn),
            OrderQueryRequestV1(
                contract_version="core.order-query.v1",
                order_id="absent",
            ),
            correlation_id="caller-123",
        )
    event = json.loads(caplog.records[-1].message)
    assert event["correlation_id"] == "caller-123"
    assert event["outcome"] == "FAILED"
    assert event["operation"] == "order-query.v1"
