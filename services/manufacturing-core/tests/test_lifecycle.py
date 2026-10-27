"""TEST-CORE-LIFECYCLE: state representation without transition semantics."""

import json

import pytest
from manufacturing_core.lifecycle import (
    ExecutionState,
    LotLifecycle,
    LotState,
    ProductionOrderState,
    SerializedComponentLifecycle,
    SerializedComponentState,
)
from pydantic import ValidationError


def test_canonical_states_serialize_as_stable_values() -> None:
    order = ProductionOrderState(id="O-1", revision="r1")
    lot = LotState(
        id="L-1",
        revision="r2",
        lifecycle_state=LotLifecycle.IN_PRODUCTION,
        execution_state=ExecutionState.QUEUED,
    )
    component = SerializedComponentState(
        id="C-1", revision="r3", lifecycle_state=SerializedComponentLifecycle.SCRAPPED
    )

    assert json.loads(order.model_dump_json()) == {
        "id": "O-1",
        "revision": "r1",
        "lifecycle_state": "CREATED",
    }
    assert lot.model_dump(mode="json")["execution_state"] == "QUEUED"
    assert component.model_dump(mode="json")["lifecycle_state"] == "SCRAPPED"


def test_lifecycle_and_execution_are_independent_dimensions() -> None:
    state = LotState(
        id="L-1",
        revision="r1",
        lifecycle_state=LotLifecycle.IN_PRODUCTION,
        execution_state=ExecutionState.QUEUED,
    )
    assert state.lifecycle_state is LotLifecycle.IN_PRODUCTION
    assert state.execution_state is ExecutionState.QUEUED
    assert state.lifecycle_state != state.execution_state


@pytest.mark.parametrize(
    "model,field,value",
    [
        (ProductionOrderState, "lifecycle_state", "PROCESSING"),
        (LotState, "lifecycle_state", "PROCESSING"),
        (LotState, "execution_state", "NOT_A_STATE"),
        (SerializedComponentState, "lifecycle_state", "RELEASED"),
    ],
)
def test_invalid_state_values_are_rejected(
    model: type[object], field: str, value: str
) -> None:
    data: dict[str, object] = {"id": "X-1", "revision": "r1", field: value}
    with pytest.raises(ValidationError):
        model.model_validate(data)  # type: ignore[attr-defined]


def test_state_records_are_immutable_and_do_not_offer_transitions() -> None:
    state = LotState(id="L-1", revision="r1")
    with pytest.raises(ValidationError):
        state.execution_state = ExecutionState.PROCESSING
    assert not hasattr(state, "transition_to")


@pytest.mark.parametrize("field", ["id", "revision"])
def test_identity_and_revision_are_immutable(field: str) -> None:
    state = SerializedComponentState(id="C-1", revision="r1")
    with pytest.raises(ValidationError):
        setattr(state, field, "replacement")
