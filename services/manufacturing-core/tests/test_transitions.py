from __future__ import annotations

import pytest
from manufacturing_core.lifecycle import (
    ExecutionState,
    LotLifecycle,
    ProductionOrderLifecycle,
    SerializedComponentLifecycle,
)
from manufacturing_core.transitions import (
    COMPONENT_TRANSITIONS,
    EXECUTION_TRANSITIONS,
    LOT_TRANSITIONS,
    ORDER_TRANSITIONS,
    TransitionRejected,
    validate_component_transition,
    validate_dispatch,
    validate_execution_transition,
    validate_lot_transition,
    validate_order_transition,
    validate_process_start,
    validate_rework,
)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (source, target)
        for source, targets in ORDER_TRANSITIONS.items()
        for target in targets
    ],
)
def test_every_order_matrix_edge_is_legal(current, target) -> None:
    validate_order_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (source, target)
        for source, targets in LOT_TRANSITIONS.items()
        for target in targets
    ],
)
def test_every_lot_matrix_edge_is_legal(current, target) -> None:
    validate_lot_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (source, target)
        for source, targets in COMPONENT_TRANSITIONS.items()
        for target in targets
    ],
)
def test_every_component_matrix_edge_is_legal(current, target) -> None:
    validate_component_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (source, target)
        for source, targets in EXECUTION_TRANSITIONS.items()
        for target in targets
    ],
)
def test_every_execution_matrix_edge_is_legal(current, target) -> None:
    validate_execution_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target", "code"),
    [
        (
            ProductionOrderLifecycle.CREATED,
            ProductionOrderLifecycle.COMPLETED,
            "INVALID_TRANSITION",
        ),
        (LotLifecycle.SCRAPPED, LotLifecycle.IN_PRODUCTION, "TERMINAL_STATE"),
        (
            SerializedComponentLifecycle.COMPLETED,
            SerializedComponentLifecycle.IN_PRODUCTION,
            "TERMINAL_STATE",
        ),
        (
            ExecutionState.QUEUED,
            ExecutionState.PROCESSING,
            "INVALID_EXECUTION_TRANSITION",
        ),
    ],
)
def test_illegal_and_terminal_transitions_are_explicitly_rejected(
    current, target, code: str
) -> None:
    with pytest.raises(TransitionRejected, match=code):
        if isinstance(current, ProductionOrderLifecycle):
            validate_order_transition(current, target)
        elif isinstance(current, LotLifecycle):
            validate_lot_transition(current, target)
        elif isinstance(current, SerializedComponentLifecycle):
            validate_component_transition(current, target)
        else:
            validate_execution_transition(current, target)


def test_dispatch_requires_queue_resource_and_no_active_hold() -> None:
    with pytest.raises(TransitionRejected, match="DISPATCH_REQUIRES_QUEUED"):
        validate_dispatch(
            ExecutionState.READY, active_hold=False, resource_available=True
        )
    with pytest.raises(TransitionRejected, match="ACTIVE_HOLD"):
        validate_dispatch(
            ExecutionState.QUEUED, active_hold=True, resource_available=True
        )
    with pytest.raises(TransitionRejected, match="RESOURCE_UNAVAILABLE"):
        validate_dispatch(
            ExecutionState.QUEUED, active_hold=False, resource_available=False
        )


def test_processing_requires_dispatch_and_available_resource() -> None:
    with pytest.raises(TransitionRejected, match="PROCESS_START_REQUIRES_DISPATCH"):
        validate_process_start(ExecutionState.QUEUED, resource_available=True)
    with pytest.raises(TransitionRejected, match="RESOURCE_UNAVAILABLE"):
        validate_process_start(ExecutionState.DISPATCHED, resource_available=False)


def test_rework_requires_directive_and_governed_reopen() -> None:
    with pytest.raises(TransitionRejected, match="REWORK_DIRECTIVE_REQUIRED"):
        validate_rework(LotLifecycle.IN_PRODUCTION, has_directive=False)
    with pytest.raises(TransitionRejected, match="REWORK_REOPEN_REQUIRED"):
        validate_rework(LotLifecycle.COMPLETED, has_directive=True)
    with pytest.raises(TransitionRejected, match="TERMINAL_STATE"):
        validate_rework(LotLifecycle.SCRAPPED, has_directive=True, governed_reopen=True)
