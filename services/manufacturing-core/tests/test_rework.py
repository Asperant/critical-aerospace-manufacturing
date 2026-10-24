"""FR-CORE-009: TEST-CORE-GENEALOGY internal rework-history foundation.

Synthetic development values only; no protected command/integration acceptance.
"""

from copy import deepcopy
from datetime import UTC, datetime

import pytest
from manufacturing_core.domain import ManufacturingRoute, RouteVisit
from manufacturing_core.rework import (
    ComponentExecutionHistory,
    ExecutionSegment,
    ProcessExecutionRecord,
    ReworkDirective,
    ReworkExecutionSegment,
)
from pydantic import ValidationError


def route(identity: str) -> ManufacturingRoute:
    return ManufacturingRoute(
        id=identity,
        revision="route-r1",
        visits=tuple(
            RouteVisit(
                id=step,
                revision="visit-r1",
                route_id=identity,
                operation_class_id=operation,
                equipment_id="CNC-1" if operation == "CNC" else "INSPECT-1",
            )
            for step, operation in (
                ("060", "CNC"),
                ("070", "CNC"),
                ("090", "INSPECTION"),
            )
        ),
    )


def records(prefix: str) -> tuple[ProcessExecutionRecord, ...]:
    return tuple(
        ProcessExecutionRecord(
            id=f"{prefix}-{step}",
            revision="exec-r1",
            component_id="COMP-1",
            lot_id="LOT-1",
            route_visit_id=step,
            equipment_id="INSPECT-1" if step == "090" else "CNC-1",
            started_at=datetime(2026, 10, 24, 10, 0, tzinfo=UTC),
            ended_at=datetime(2026, 10, 24, 10, 1, tzinfo=UTC),
        )
        for step in ("060", "070", "090")
    )


def history() -> ComponentExecutionHistory:
    return ComponentExecutionHistory(
        component_id="COMP-1",
        original=ExecutionSegment(
            route=route("NORMAL"), executions=records("original")
        ),
    )


def rework(cycle: int = 1) -> ReworkExecutionSegment:
    return ReworkExecutionSegment(
        route=route("REWORK"),
        executions=records(f"rework-{cycle}"),
        directive=ReworkDirective(
            id=f"DIRECTIVE-{cycle}",
            revision="directive-r1",
            component_id="COMP-1",
            reason="inspection anomaly",
            originating_inspection_id=f"INSPECTION-{cycle}",
            origin_execution_id="original-090"
            if cycle == 1
            else f"rework-{cycle-1}-090",
            return_visit_id="060",
            rework_route_id="REWORK",
            rework_route_revision="route-r1",
            related_defect_id="DEFECT-1",
            related_incident_id="INCIDENT-1",
            current_rework_count=cycle - 1,
            approval_state="APPROVED",
            policy_state="RECORDED_BY_CORE",
        ),
    )


def test_rework_cycles_append_separate_segments_without_overwriting_history() -> None:
    original = history()
    original_json = original.model_dump_json()
    first = original.append_rework(rework())
    first_json = first.model_dump_json()
    second = first.append_rework(rework(2))

    assert original.model_dump_json() == original_json
    assert first.model_dump_json() == first_json
    assert second.original == original.original
    assert second.rework[0] == first.rework[0]
    assert len(second.rework) == 2
    assert second.rework[1].directive.origin_execution_id == "rework-1-090"
    assert (
        ComponentExecutionHistory.model_validate_json(second.model_dump_json())
        == second
    )
    executions = [r for s in (second.original, *second.rework) for r in s.executions]
    assert len({r.id for r in executions}) == 9
    assert {r.component_id for r in executions} == {"COMP-1"}
    # Re-entrant/repeated operations retain distinct execution records.
    assert [r.route_visit_id for r in executions].count("060") == 3


@pytest.mark.parametrize("directive", [None, {}])
def test_rework_requires_an_explicit_directive(directive: object) -> None:
    data = rework().model_dump()
    data["directive"] = directive
    with pytest.raises(ValidationError):
        ReworkExecutionSegment.model_validate(data)


def test_empty_rework_cannot_be_recorded_as_execution_history() -> None:
    data = rework().model_dump()
    data["executions"] = ()
    with pytest.raises(ValidationError):
        ReworkExecutionSegment.model_validate(data)


@pytest.mark.parametrize("field", ["rework_route_id", "rework_route_revision"])
def test_wrong_rework_route_or_revision_rejected(field: str) -> None:
    data = rework().model_dump()
    data["directive"][field] = "different"
    with pytest.raises(ValidationError, match="route does not match"):
        ReworkExecutionSegment.model_validate(data)


@pytest.mark.parametrize("field", ["component_id", "route_visit_id"])
def test_execution_with_wrong_component_or_unknown_visit_rejected(field: str) -> None:
    data = rework().model_dump()
    data["executions"][0][field] = "unknown"
    with pytest.raises(ValidationError):
        ReworkExecutionSegment.model_validate(data)


def test_append_rejects_cross_component_history_without_changing_original() -> None:
    source = history()
    data = rework().model_dump()
    data["directive"]["component_id"] = "COMP-2"
    for record in data["executions"]:
        record["component_id"] = "COMP-2"
    before = source.model_dump_json()
    with pytest.raises(ValidationError, match="different component"):
        source.append_rework(ReworkExecutionSegment.model_validate(data))
    assert source.model_dump_json() == before


@pytest.mark.parametrize("origin", ["unknown", "rework-1-090"])
def test_missing_or_self_referential_origin_rejected(origin: str) -> None:
    data = rework().model_dump()
    data["directive"]["origin_execution_id"] = origin
    with pytest.raises(ValidationError, match="prior execution"):
        history().append_rework(ReworkExecutionSegment.model_validate(data))


def test_return_must_reference_original_route() -> None:
    data = rework().model_dump()
    data["directive"]["return_visit_id"] = "unknown"
    with pytest.raises(ValidationError, match="return visit"):
        history().append_rework(ReworkExecutionSegment.model_validate(data))


def test_repeated_directive_cannot_create_another_history_segment() -> None:
    source = history().append_rework(rework())
    before = source.model_dump_json()
    with pytest.raises(ValidationError, match="duplicate rework directive"):
        source.append_rework(rework())
    assert source.model_dump_json() == before


def test_execution_identity_cannot_be_reused_across_segments() -> None:
    data = rework().model_dump()
    data["executions"][0]["id"] = "original-060"
    with pytest.raises(ValidationError, match="duplicate execution identity"):
        history().append_rework(ReworkExecutionSegment.model_validate(data))


def test_duplicate_execution_inside_segment_rejected() -> None:
    data = rework().model_dump()
    data["executions"] = (*data["executions"], deepcopy(data["executions"][0]))
    with pytest.raises(ValidationError, match="duplicate execution identity"):
        ReworkExecutionSegment.model_validate(data)


@pytest.mark.parametrize("invalid", [-1, True, "1"])
def test_count_is_a_nonnegative_strict_integer(invalid: object) -> None:
    data = rework().directive.model_dump()
    data["current_rework_count"] = invalid
    with pytest.raises(ValidationError):
        ReworkDirective.model_validate(data)


@pytest.mark.parametrize("field", ["started_at", "ended_at"])
def test_naive_execution_times_rejected(field: str) -> None:
    data = records("test")[0].model_dump()
    data[field] = "2026-10-24T10:00:00"
    with pytest.raises(ValidationError):
        ProcessExecutionRecord.model_validate(data)


def test_negative_execution_interval_rejected() -> None:
    data = records("test")[0].model_dump()
    data["ended_at"] = "2026-10-24T09:59:00Z"
    with pytest.raises(ValidationError, match="end precedes start"):
        ProcessExecutionRecord.model_validate(data)


def test_history_directive_and_nested_execution_are_immutable() -> None:
    source = history().append_rework(rework())
    for model, field in (
        (source, "component_id"),
        (source, "original"),
        (source, "rework"),
        (source.rework[0].directive, "id"),
        (source.original.executions[0], "component_id"),
        (source.original.route, "revision"),
    ):
        with pytest.raises(ValidationError, match="frozen"):
            setattr(model, field, "replacement")


def test_unknown_history_fields_do_not_smuggle_in_authority_or_oracle_state() -> None:
    data = rework().model_dump()
    data["oracle_state"] = "failed"
    with pytest.raises(ValidationError, match="Extra inputs"):
        ReworkExecutionSegment.model_validate(data)
