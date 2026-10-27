from __future__ import annotations

import psycopg
import pytest
from conftest import Database
from manufacturing_core.commands import (
    DispatchLot,
    OutcomeStatus,
    PlaceLotOnHold,
    ReleaseMaterialHold,
)
from manufacturing_core.enforcement import AuthorizationDenied
from manufacturing_core.transitions import CoreTransitionService
from psycopg.rows import DictRow, dict_row

pytestmark = pytest.mark.integration


def setup_lot(connection: psycopg.Connection[DictRow]) -> None:
    connection.execute(
        "INSERT INTO core.manufacturing_route(id, revision) VALUES ('R-1', 'route-r1')"
    )
    connection.execute(
        "INSERT INTO core.production_order(id, revision, route_id) VALUES ('O-1', 'o-r1', 'R-1')"
    )
    connection.execute(
        "INSERT INTO core.lot(id, revision, order_id) VALUES ('L-1', 'l-r1', 'O-1')"
    )
    connection.execute(
        "INSERT INTO core.lot_state(id, revision) VALUES ('L-1', 'l-r1')"
    )


def hold_command(key: str = "hold-1") -> PlaceLotOnHold:
    return PlaceLotOnHold.model_validate(
        {
            "idempotency_key": key,
            "world_id": "primary",
            "correlation_id": "corr-hold",
            "target": {"entity_type": "Lot", "entity_id": "L-1"},
            "expected": {"expected_revision": "l-r1"},
            "hold_reason": "inspection anomaly",
            "material_hold_id": "H-1",
        }
    )


def release_command(key: str = "release-1") -> ReleaseMaterialHold:
    return ReleaseMaterialHold.model_validate(
        {
            "idempotency_key": key,
            "world_id": "primary",
            "correlation_id": "corr-release",
            "target": {"entity_type": "Lot", "entity_id": "L-1"},
            "expected": {"expected_revision": "l-r1"},
            "hold_id": "H-1",
            "release_reason": "review complete",
        }
    )


def test_hold_release_is_atomic_retained_and_idempotent(
    database: Database,
) -> None:
    with psycopg.Connection[DictRow].connect(
        database.runtime_dsn, row_factory=dict_row
    ) as connection:
        setup_lot(connection)
        service = CoreTransitionService(connection)
        permissions = {"core.lot.place_hold", "core.material.release_hold"}
        placed = service.place_lot_on_hold(permissions, hold_command())
        assert placed.status is OutcomeStatus.ACCEPTED
        duplicate = service.place_lot_on_hold(permissions, hold_command("hold-2"))
        assert duplicate.status is OutcomeStatus.REJECTED
        assert duplicate.error_code == "HOLD_ALREADY_ACTIVE"
        released = service.release_material_hold(permissions, release_command())
        assert released.status is OutcomeStatus.ACCEPTED
        retry = service.release_material_hold(permissions, release_command())
        assert retry == released
        row = connection.execute(
            "SELECT status, released_at, release_reason FROM core.material_hold WHERE id = 'H-1'"
        ).fetchone()
        assert row is not None
        assert row["status"] == "RELEASED"
        assert row["released_at"] is not None
        assert row["release_reason"] == "review complete"
        revision = connection.execute(
            "SELECT revision FROM core.lot WHERE id = 'L-1'"
        ).fetchone()
        assert revision is not None
        assert revision["revision"] == "l-r1"


def test_hold_dispatch_and_authorization_negative_paths(
    connection: psycopg.Connection[DictRow],
) -> None:
    setup_lot(connection)
    service = CoreTransitionService(connection)
    command = hold_command()
    with pytest.raises(AuthorizationDenied):
        service.place_lot_on_hold(set(), command)
    accepted = service.place_lot_on_hold({"core.lot.place_hold"}, command)
    assert accepted.status is OutcomeStatus.ACCEPTED
    dispatch = DispatchLot.model_validate(
        {
            "idempotency_key": "dispatch-1",
            "world_id": "primary",
            "correlation_id": "corr-dispatch",
            "target": {"entity_type": "Lot", "entity_id": "L-1"},
            "expected": {"expected_revision": "l-r1"},
            "operation_id": "OP-1",
            "resource_id": "E-1",
        }
    )
    # The fixture's initial execution is READY, so this exercises the guard
    # before physical dispatch and confirms a hold never mutates lifecycle.
    outcome = service.dispatch_lot(set(), dispatch, resource_available=True)
    assert outcome.status is OutcomeStatus.REJECTED
    assert outcome.error_code == "DISPATCH_REQUIRES_QUEUED"
    replay = service.dispatch_lot(set(), dispatch, resource_available=True)
    assert replay == outcome
