from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from operational_twin import (
    SCHEDULING_SNAPSHOT_READ,
    ReadScopeDenied,
    SnapshotQueryError,
    TwinQueryAPI,
    TwinReadContext,
)

FIXTURE = (
    Path(__file__).parents[2]
    / "manufacturing-core"
    / "contracts"
    / "v1"
    / "scheduling-snapshot.normal.json"
)


def snapshot() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def api(value: dict[str, object] | None = None) -> TwinQueryAPI:
    stored = value or snapshot()
    return TwinQueryAPI(
        lambda world_id: stored if world_id == "PRIMARY" else {},
        {"scheduler-service": frozenset({SCHEDULING_SNAPSHOT_READ})},
    )


def context() -> TwinReadContext:
    return TwinReadContext("scheduler-service", frozenset({SCHEDULING_SNAPSHOT_READ}))


def test_versioned_query_returns_contract_fixture_and_defensive_copy() -> None:
    result = api().get_scheduling_snapshot_v1(context(), world_id="PRIMARY")
    assert result["contract_version"] == "core.scheduling-snapshot.v1"
    assert result["lots"][0]["route_position"]["position"] == 2  # type: ignore[index]
    result["lots"].clear()  # type: ignore[union-attr]
    assert len(snapshot()["lots"]) == 2  # type: ignore[arg-type]


def test_unknown_identity_and_missing_scope_are_denied() -> None:
    with pytest.raises(ReadScopeDenied):
        api().get_scheduling_snapshot_v1(
            TwinReadContext("unknown", frozenset({SCHEDULING_SNAPSHOT_READ})),
            world_id="PRIMARY",
        )
    with pytest.raises(ReadScopeDenied):
        api().get_scheduling_snapshot_v1(
            TwinReadContext("scheduler-service", frozenset()), world_id="PRIMARY"
        )


def test_world_scope_is_explicit_and_provider_cannot_return_another_world() -> None:
    with pytest.raises(SnapshotQueryError, match="world_id"):
        api().get_scheduling_snapshot_v1(context(), world_id="OTHER")
    wrong = snapshot()
    wrong["world_id"] = "OTHER"
    with pytest.raises(SnapshotQueryError, match="world_id"):
        api(copy.deepcopy(wrong)).get_scheduling_snapshot_v1(
            context(), world_id="PRIMARY"
        )


def test_hidden_oracle_fields_and_shape_drift_fail_closed() -> None:
    hidden = snapshot()
    hidden["oracle_state"] = {"secret": True}
    with pytest.raises(SnapshotQueryError, match="extra"):
        api(hidden).get_scheduling_snapshot_v1(context(), world_id="PRIMARY")

    missing = snapshot()
    del missing["current_schedule_version"]
    with pytest.raises(SnapshotQueryError, match="missing"):
        api(missing).get_scheduling_snapshot_v1(context(), world_id="PRIMARY")


def test_query_api_has_no_command_or_mutation_surface() -> None:
    query = api()
    assert not hasattr(query, "mutate")
    assert not hasattr(query, "execute_command")
