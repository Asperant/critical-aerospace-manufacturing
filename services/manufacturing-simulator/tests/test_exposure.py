"""Operational exposure: allow-list only, no evaluator-only truth (TEST-SIM-ISOLATION)."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from dispatch_fixtures import FixtureFacility, lot
from manufacturing_simulator import (
    ExposureError,
    OperationalSnapshot,
    build_request,
    find_evaluator_field,
    is_evaluator_field,
    make_event,
    operational_snapshot,
)
from manufacturing_simulator.exposure import ALLOWED_ATTRIBUTES, EVENT_KINDS


@pytest.mark.parametrize(
    "name",
    [
        "oracle",
        "Oracle_label",
        "ORACLE-state",
        "ground_truth",
        "groundTruth".lower(),
        "true_root_cause",
        "x_oracle_y",
        "true-root-cause",
    ],
)
def test_evaluator_field_names_are_recognised(name: str) -> None:
    assert is_evaluator_field(name)


@pytest.mark.parametrize("name", ["lot_id", "machine_id", "hold", "truthful", 5, None])
def test_operational_field_names_are_not_flagged(name: object) -> None:
    assert not is_evaluator_field(name)


def test_detection_is_recursive_and_does_not_exhaust_the_stack() -> None:
    assert find_evaluator_field({"a": [{"b": {"oracle_x": 1}}]}) == "/a/0/b/oracle_x"
    clean: dict[str, Any] = {"leaf": 1}
    for _ in range(5000):
        clean = {"n": clean}
    assert find_evaluator_field(clean) is None
    flagged: dict[str, Any] = {"ground_truth": 1}
    for _ in range(5000):
        flagged = {"n": flagged}
    assert find_evaluator_field(flagged) is not None


def test_events_accept_only_allow_listed_kinds_and_attributes() -> None:
    event = make_event(
        "DISPATCH_ACCEPTED", 7, "w", "c", {"lot_id": "L1", "rule_id": None}
    )
    assert event.provenance == "SIMULATION" and event.attributes == (("lot_id", "L1"),)
    assert set(event.to_document()) == {
        "kind",
        "time",
        "world_id",
        "correlation_id",
        "provenance",
        "attributes",
    }
    with pytest.raises(ExposureError):
        make_event("QUALITY_EXCURSION_DETECTED", 0, "w", "c", {})
    for bad in ("oracle_state", "free_text", "ground_truth", "reason"):
        with pytest.raises(ExposureError):
            make_event("DISPATCH_REJECTED", 0, "w", "c", {bad: "x"})
    not_text: dict[str, Any] = {"lot_id": 5}
    with pytest.raises(ExposureError):
        make_event("DISPATCH_REJECTED", 0, "w", "c", not_text)
    assert "oracle" not in " ".join(sorted(EVENT_KINDS | ALLOWED_ATTRIBUTES)).lower()


def test_the_snapshot_exposes_exactly_the_allow_listed_fields() -> None:
    facility = FixtureFacility([lot("L2"), lot("L1", held=True)])
    snapshot = operational_snapshot("w", facility, 12)
    assert isinstance(snapshot, OperationalSnapshot)
    assert [item.lot_id for item in snapshot.lots] == ["L1", "L2"]
    assert snapshot.provenance == "SIMULATION" and snapshot.simulation_time == 12
    names = {f.name for item in snapshot.lots for f in dataclasses.fields(item)}
    assert names == {
        "lot_id",
        "revision",
        "route_step",
        "held",
        "priority",
        "due_at",
        "ready_at",
    }
    assert {f.name for f in dataclasses.fields(snapshot.machines[0])} == {
        "machine_id",
        "available",
    }
    assert not any(is_evaluator_field(n) for n in names)


def test_a_request_offers_only_ready_unheld_eligible_lots_in_a_stable_order() -> None:
    facility = FixtureFacility(
        [
            lot("L3"),
            lot("L1"),
            lot("HELD", held=True),
            lot("LATE", ready=99),
            lot("OTHER", machines=("M2",)),
        ]
    )
    request = build_request("w", "REQ-1", facility, 10, "M1")
    assert [c.lot_id for c in request.candidates] == ["L1", "L3"]
    assert request.state_revision == facility.state_revision
    assert find_evaluator_field(request.to_document()) is None
    with pytest.raises(ExposureError):
        build_request("w", "REQ-2", facility, 10, "NOPE")
