"""DEP-038 producer contract: re-entrant lifecycle, hold and rework semantics.

The fixtures are validated against the published schema and the Core models, and
the semantic claims are bound to the merged WP-CORE-002 guards, not restated.
"""

import copy
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator
from manufacturing_core.lifecycle import ExecutionState, LotLifecycle
from manufacturing_core.operational_semantics_v1 import (
    CONTRACT_VERSION,
    LotOperationalSemanticsV1,
    MaterialHoldRecordV1,
)
from manufacturing_core.transitions import (
    MaterialHold,
    TransitionRejected,
    validate_dispatch,
    validate_execution_transition,
    validate_rework,
)
from pydantic import ValidationError

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts" / "v1"
SCHEMA = CONTRACTS / "lot-operational-semantics.v1.schema.json"
FIXTURES = ("reentrant-rework", "held")


def load(scenario: str) -> dict[str, Any]:
    path = CONTRACTS / f"lot-operational-semantics.{scenario}.json"
    return json.loads(path.read_text())


def schema_validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA.read_text()))


def test_published_schema_matches_models() -> None:
    published = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(published)
    assert published == LotOperationalSemanticsV1.model_json_schema()


@pytest.mark.parametrize("scenario", FIXTURES)
def test_fixture_validates_against_schema_and_round_trips(scenario: str) -> None:
    data = load(scenario)
    schema_validator().validate(data)
    assert data["contract_version"] == CONTRACT_VERSION
    model = LotOperationalSemanticsV1.model_validate(data)
    assert model.model_dump(mode="json") == data


def test_reentrant_fixture_revisits_an_operation_class_with_distinct_visits() -> None:
    model = LotOperationalSemanticsV1.model_validate(load("reentrant-rework"))
    history = model.component_histories[0]
    visits = history.original.route.visits
    classes = [visit.operation_class_id for visit in visits]
    assert len(set(classes)) < len(classes)
    assert len({visit.id for visit in visits}) == len(visits)
    # Traversal order is semantic; it is not identity order.
    assert [visit.id for visit in visits] == ["VISIT-A-01", "VISIT-A-02", "VISIT-A-03"]
    cited = [record.route_visit_id for record in history.original.executions]
    assert len(set(cited)) == len(cited)


def test_reentry_is_an_execution_cycle_not_a_lifecycle_change() -> None:
    validate_execution_transition(ExecutionState.STEP_COMPLETED, ExecutionState.READY)
    lot = LotOperationalSemanticsV1.model_validate(load("reentrant-rework")).lot
    assert lot.lifecycle_state is LotLifecycle.IN_PRODUCTION
    assert lot.execution_state is ExecutionState.READY


def test_rework_is_directive_linked_history_returning_to_the_original_route() -> None:
    model = LotOperationalSemanticsV1.model_validate(load("reentrant-rework"))
    history = model.component_histories[0]
    segment = history.rework[0]
    original_visits = {visit.id for visit in history.original.route.visits}
    origin_ids = {record.id for record in history.original.executions}
    assert segment.directive.origin_execution_id in origin_ids
    assert segment.directive.return_visit_id in original_visits
    assert segment.route.id != history.original.route.id
    assert not model.component_histories[1].rework
    # The original history is preserved verbatim when rework is appended.
    assert history.original.executions[0].id == "EXEC-001"


def test_rework_guard_requires_directive_and_forbids_terminal_material() -> None:
    validate_rework(LotLifecycle.IN_PRODUCTION, has_directive=True)
    with pytest.raises(TransitionRejected) as missing:
        validate_rework(LotLifecycle.IN_PRODUCTION, has_directive=False)
    assert missing.value.code == "REWORK_DIRECTIVE_REQUIRED"
    with pytest.raises(TransitionRejected) as scrapped:
        validate_rework(LotLifecycle.SCRAPPED, has_directive=True)
    assert scrapped.value.code == "TERMINAL_STATE"
    with pytest.raises(TransitionRejected) as completed:
        validate_rework(LotLifecycle.COMPLETED, has_directive=True)
    assert completed.value.code == "REWORK_REOPEN_REQUIRED"
    validate_rework(LotLifecycle.COMPLETED, has_directive=True, governed_reopen=True)


def test_active_hold_is_independent_state_and_blocks_dispatch() -> None:
    model = LotOperationalSemanticsV1.model_validate(load("held"))
    active = [hold for hold in model.holds if hold.status == "ACTIVE"]
    assert len(active) == 1
    assert model.lot.lifecycle_state is LotLifecycle.IN_PRODUCTION
    assert model.lot.execution_state is ExecutionState.QUEUED
    with pytest.raises(TransitionRejected) as blocked:
        validate_dispatch(
            model.lot.execution_state, active_hold=bool(active), resource_available=True
        )
    assert blocked.value.code == "ACTIVE_HOLD"
    validate_dispatch(
        model.lot.execution_state, active_hold=False, resource_available=True
    )


def test_released_holds_are_retained_history() -> None:
    for scenario in FIXTURES:
        model = LotOperationalSemanticsV1.model_validate(load(scenario))
        assert any(hold.status == "RELEASED" for hold in model.holds)


def test_hold_record_is_the_core_material_hold_without_command_internals() -> None:
    for hold in LotOperationalSemanticsV1.model_validate(load("held")).holds:
        row = hold.model_dump(mode="python") | {"placed_command_id": uuid4()}
        if hold.status == "RELEASED":
            row["released_command_id"] = uuid4()
        core = MaterialHold.model_validate(row)
        assert (
            MaterialHoldRecordV1.model_validate(
                core.model_dump(
                    mode="python", exclude={"placed_command_id", "released_command_id"}
                )
            )
            == hold
        )
    assert set(MaterialHoldRecordV1.model_fields) < set(MaterialHold.model_fields)


def corrupt(scenario: str, mutate: Any) -> dict[str, Any]:
    data = copy.deepcopy(load(scenario))
    mutate(data)
    return data


def set_path(*path: Any, value: Any) -> Any:
    def mutate(data: dict[str, Any]) -> None:
        target: Any = data
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


def del_path(*path: Any) -> Any:
    def mutate(data: dict[str, Any]) -> None:
        target: Any = data
        for key in path[:-1]:
            target = target[key]
        del target[path[-1]]

    return mutate


def second_active_hold(data: dict[str, Any]) -> None:
    extra = copy.deepcopy(data["holds"][-1])
    extra["id"] = "HOLD-004"
    extra["placed_at"] = "2026-10-27T12:00:00Z"
    data["holds"].append(extra)


def reverse_holds(data: dict[str, Any]) -> None:
    data["holds"].reverse()


def duplicate_component(data: dict[str, Any]) -> None:
    data["component_histories"].append(copy.deepcopy(data["component_histories"][0]))


def reverse_components(data: dict[str, Any]) -> None:
    data["component_histories"].reverse()


STRUCTURAL = [
    ("held", del_path("contract_version")),
    ("held", set_path("contract_version", value="core.lot-operational-semantics.v2")),
    ("held", set_path("lot", "lifecycle_state", value="SUSPENDED")),
    ("held", set_path("lot", "execution_state", value="PAUSED")),
    ("held", set_path("holds", 0, "status", value="PENDING")),
    ("held", set_path("oracle_state", value={"hidden_failure": True})),
    ("held", del_path("holds", 0, "reason")),
    ("held", set_path("lot", "revision", value=" ")),
]
SEMANTIC = [
    ("held", set_path("holds", 0, "lot_id", value="LOT-OTHER")),
    ("held", second_active_hold),
    ("held", reverse_holds),
    ("held", set_path("holds", 1, "release_reason", value="x")),
    ("held", set_path("holds", 1, "status", value="RELEASED")),
    ("held", set_path("holds", 0, "release_reason", value=None)),
    ("held", set_path("holds", 0, "released_at", value="2026-10-27T06:00:00Z")),
    ("reentrant-rework", duplicate_component),
    ("reentrant-rework", reverse_components),
    (
        "reentrant-rework",
        set_path(
            "component_histories",
            0,
            "rework",
            0,
            "directive",
            "origin_execution_id",
            value="EXEC-MISSING",
        ),
    ),
    (
        "reentrant-rework",
        set_path(
            "component_histories",
            0,
            "rework",
            0,
            "directive",
            "return_visit_id",
            value="VISIT-RW-01",
        ),
    ),
    (
        "reentrant-rework",
        set_path(
            "component_histories",
            0,
            "rework",
            0,
            "directive",
            "rework_route_revision",
            value="other-revision",
        ),
    ),
    (
        "reentrant-rework",
        set_path(
            "component_histories",
            0,
            "original",
            "executions",
            0,
            "route_visit_id",
            value="VISIT-NOPE",
        ),
    ),
    (
        "reentrant-rework",
        set_path(
            "component_histories",
            0,
            "original",
            "route",
            "visits",
            2,
            "id",
            value="VISIT-A-01",
        ),
    ),
]


@pytest.mark.parametrize(("scenario", "mutate"), STRUCTURAL)
def test_structural_violations_fail_schema_and_model(
    scenario: str, mutate: Any
) -> None:
    data = corrupt(scenario, mutate)
    assert list(schema_validator().iter_errors(data))
    with pytest.raises(ValidationError):
        LotOperationalSemanticsV1.model_validate(data)


@pytest.mark.parametrize(("scenario", "mutate"), SEMANTIC)
def test_semantic_violations_fail_the_model(scenario: str, mutate: Any) -> None:
    with pytest.raises(ValidationError):
        LotOperationalSemanticsV1.model_validate(corrupt(scenario, mutate))
