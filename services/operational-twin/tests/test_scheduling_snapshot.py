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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("generated_at", "2026-02-30T08:00:00Z"),
        ("generated_at", "2026-10-27T08:00:00+03:00"),
        ("freshness.valid_until", "2026-10-27T08:05:00"),
        ("lots[0].due_at", "not-a-timestamp"),
    ],
)
def test_invalid_or_non_utc_timestamps_are_rejected(
    field: str, value: str
) -> None:
    invalid = snapshot()
    if field == "generated_at":
        invalid[field] = value
    elif field == "freshness.valid_until":
        invalid["freshness"]["valid_until"] = value  # type: ignore[index]
    else:
        invalid["lots"][0]["due_at"] = value  # type: ignore[index]

    with pytest.raises(SnapshotQueryError, match="timestamp"):
        api(invalid).get_scheduling_snapshot_v1(context(), world_id="PRIMARY")


def test_snapshot_freshness_window_must_be_positive() -> None:
    invalid = snapshot()
    invalid["freshness"]["valid_until"] = invalid["generated_at"]  # type: ignore[index]

    with pytest.raises(SnapshotQueryError, match="after generated_at"):
        api(invalid).get_scheduling_snapshot_v1(context(), world_id="PRIMARY")


def test_query_api_has_no_command_or_mutation_surface() -> None:
    query = api()
    assert not hasattr(query, "mutate")
    assert not hasattr(query, "execute_command")
