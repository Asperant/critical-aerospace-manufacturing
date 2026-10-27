"""DEP-030 producer contract: bounded SchedulingSnapshot shape and negatives."""

import copy
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts" / "v1"


def snapshot() -> dict:
    return json.loads((CONTRACTS / "scheduling-snapshot.normal.json").read_text())


def test_snapshot_fixture_has_the_exact_dep030_fields() -> None:
    data = snapshot()
    schema = json.loads((CONTRACTS / "scheduling-snapshot.v1.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    assert data["contract_version"] == "core.scheduling-snapshot.v1"
    assert data["world_id"] == "PRIMARY"
    assert data["snapshot_revision"]
    assert data["freshness"]["status"] == "FRESH"
    assert {
        "id",
        "revision",
        "route_position",
        "priority",
        "due_at",
        "eligible_equipment_ids",
    } <= set(data["lots"][0])
    assert {"route_id", "visit_id", "position", "operation_class_id"} == set(
        data["lots"][0]["route_position"]
    )
    assert {"id", "revision", "maintenance_state"} == set(data["equipment"][0])


@pytest.mark.parametrize(
    "path",
    [
        ("lots", 0, "revision"),
        ("lots", 0, "route_position", "position"),
        ("lots", 0, "eligible_equipment_ids"),
        ("lots", 0, "priority"),
        ("lots", 0, "due_at"),
        ("equipment", 0, "maintenance_state"),
    ],
)
def test_dep030_required_state_dimensions_are_required(
    path: tuple[object, ...],
) -> None:
    data = snapshot()
    target: dict = data
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    del target[path[-1]]
    schema = json.loads((CONTRACTS / "scheduling-snapshot.v1.schema.json").read_text())
    with pytest.raises(ValidationError):
        Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)


def test_oracle_state_is_rejected() -> None:
    data = copy.deepcopy(snapshot())
    data["oracle_state"] = {"hidden_failure": True}
    schema = json.loads((CONTRACTS / "scheduling-snapshot.v1.schema.json").read_text())
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(data)


def test_stale_snapshot_is_structurally_valid_but_explicit() -> None:
    data = snapshot()
    data["freshness"]["status"] = "STALE"
    schema = json.loads((CONTRACTS / "scheduling-snapshot.v1.schema.json").read_text())
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(data)
    assert data["freshness"]["status"] == "STALE"
