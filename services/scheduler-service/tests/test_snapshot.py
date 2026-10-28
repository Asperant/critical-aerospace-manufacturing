"""Snapshot consumer: the published v1 shape, freshness and completeness limits."""

from __future__ import annotations

import dataclasses
from collections.abc import Callable
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from manufacturing_scheduler.errors import IncompleteInputError, SnapshotError
from manufacturing_scheduler.snapshot import (
    FreshnessMode,
    FreshnessPolicy,
    InputGap,
    MaintenanceState,
    Usability,
    parse_snapshot,
    parse_snapshot_json,
    read_planning_input,
    to_planning_input,
)
from plan_helpers import NOW, Doc, mutated, parsed_snapshot, policy, snapshot_doc

Change = Callable[[Doc], None]


def _set(path: str, value: Any) -> Change:
    def apply(doc: Doc) -> None:
        keys = path.split("/")
        node: Any = doc
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        last = keys[-1]
        if isinstance(node, list):
            node[int(last)] = value
        else:
            node[last] = value

    return apply


def _drop(path: str) -> Change:
    def apply(doc: Doc) -> None:
        keys = path.split("/")
        node: Any = doc
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        del node[keys[-1]]

    return apply


def test_valid_fixture_keeps_every_published_fact_exactly() -> None:
    snap = parsed_snapshot()
    assert (snap.world_id, snap.snapshot_revision) == ("PRIMARY", "twin-rev-184202")
    assert snap.generated_at == datetime(2026, 10, 27, 8, 0, tzinfo=UTC)
    assert snap.valid_until == datetime(2026, 10, 27, 8, 5, tzinfo=UTC)
    assert snap.usability is Usability.NORMAL and snap.diagnostics == ()
    assert snap.current_schedule_version == "schedule-v19"
    first, second = snap.lots
    assert (first.lot_id, first.revision, first.priority) == (
        "LOT-001",
        "lot-rev-11",
        90,
    )
    assert first.visit.route_id == "ROUTE-A" and first.visit.visit_id == "VISIT-A-03"
    assert first.visit.position == 2 and first.visit.operation_class_id == "FINISH-CNC"
    assert second.eligible_equipment_ids == ("CNC-5AX-07", "CNC-5AX-08")
    assert [e.maintenance_state for e in snap.equipment] == [
        MaintenanceState.AVAILABLE,
        MaintenanceState.PLANNED_MAINTENANCE,
    ]
    assert snap.equipment[1].revision == "equipment-rev-3"


def test_json_text_and_mapping_give_the_same_snapshot() -> None:
    text = (
        '{"contract_version":"core.scheduling-snapshot.v1","world_id":"W",'
        '"snapshot_revision":"r","generated_at":"2026-10-27T08:00:00+00:00",'
        '"freshness":{"status":"FRESH","valid_until":"2026-10-27T08:05:00Z"},'
        '"lots":[],"equipment":[],"current_schedule_version":null}'
    )
    snap = parse_snapshot_json(text, expected_world_id="W", policy=policy())
    assert snap.lots == () and snap.current_schedule_version is None


REJECTED: list[tuple[str, Change, str]] = [
    (
        "version",
        _set("contract_version", "core.scheduling-snapshot.v2"),
        "VERSION_UNSUPPORTED",
    ),
    ("world", _set("world_id", "OTHER"), "WORLD_MISMATCH"),
    ("world-case", _set("world_id", "primary"), "WORLD_MISMATCH"),
    ("unknown-top", _set("extra", 1), "FIELD_UNKNOWN"),
    ("unknown-lot", _set("lots/0/extra", 1), "FIELD_UNKNOWN"),
    ("missing-top", _drop("freshness"), "FIELD_MISSING"),
    ("missing-visit", _drop("lots/0/route_position/visit_id"), "FIELD_MISSING"),
    ("oracle-top", _set("oracle_state", {}), "ORACLE_FIELD_REJECTED"),
    (
        "oracle-nested",
        _set("lots/1/route_position/Hidden_Oracle", 1),
        "ORACLE_FIELD_REJECTED",
    ),
    ("blank-id", _set("lots/0/id", ""), "IDENTIFIER_INVALID"),
    ("padded-id", _set("lots/0/id", " LOT-001"), "IDENTIFIER_INVALID"),
    ("inner-space", _set("equipment/0/id", "CNC 07"), "IDENTIFIER_INVALID"),
    ("trailing-newline", _set("snapshot_revision", "rev\n"), "IDENTIFIER_INVALID"),
    ("non-string-id", _set("lots/0/revision", 11), "IDENTIFIER_INVALID"),
    ("huge-priority", _set("lots/0/priority", 10**400), "INTEGER_INVALID"),
    (
        "huge-position",
        _set("lots/0/route_position/position", -(10**400)),
        "INTEGER_INVALID",
    ),
    ("bool-priority", _set("lots/0/priority", True), "INTEGER_INVALID"),
    ("float-priority", _set("lots/0/priority", 90.0), "INTEGER_INVALID"),
    ("negative-priority", _set("lots/0/priority", -1), "INTEGER_INVALID"),
    ("bool-position", _set("lots/0/route_position/position", False), "INTEGER_INVALID"),
    ("string-position", _set("lots/0/route_position/position", "2"), "INTEGER_INVALID"),
    ("naive-time", _set("generated_at", "2026-10-27T08:00:00"), "TIMESTAMP_INVALID"),
    (
        "offset-time",
        _set("generated_at", "2026-10-27T11:00:00+03:00"),
        "TIMESTAMP_INVALID",
    ),
    ("date-only", _set("lots/0/due_at", "2026-10-28"), "TIMESTAMP_INVALID"),
    (
        "impossible-date",
        _set("lots/0/due_at", "2026-02-30T00:00:00Z"),
        "TIMESTAMP_INVALID",
    ),
    ("lowercase-t", _set("lots/0/due_at", "2026-10-28t12:00:00Z"), "TIMESTAMP_INVALID"),
    (
        "long-fraction",
        _set("lots/0/due_at", "2026-10-28T12:00:00.1234567Z"),
        "TIMESTAMP_INVALID",
    ),
    ("leap-second", _set("lots/0/due_at", "2026-10-28T23:59:60Z"), "TIMESTAMP_INVALID"),
    ("duplicate-lot", _set("lots/1/id", "LOT-001"), "DUPLICATE_ID"),
    ("duplicate-equipment", _set("equipment/1/id", "CNC-5AX-07"), "DUPLICATE_ID"),
    (
        "duplicate-eligible",
        _set("lots/1/eligible_equipment_ids", ["CNC-5AX-07", "CNC-5AX-07"]),
        "DUPLICATE_ID",
    ),
    (
        "unknown-eligible",
        _set("lots/0/eligible_equipment_ids", ["CNC-GHOST"]),
        "UNKNOWN_REFERENCE",
    ),
    ("status", _set("freshness/status", "fresh"), "ENUM_INVALID"),
    ("maintenance", _set("equipment/0/maintenance_state", "RUNNING"), "ENUM_INVALID"),
    (
        "empty-window",
        _set("freshness/valid_until", "2026-10-27T08:00:00Z"),
        "WINDOW_INCONSISTENT",
    ),
    (
        "reversed-window",
        _set("freshness/valid_until", "2026-10-27T07:00:00Z"),
        "WINDOW_INCONSISTENT",
    ),
    ("lots-not-array", _set("lots", {"0": {}}), "ARRAY_REQUIRED"),
    ("lots-tuple", _set("lots", ()), "ARRAY_REQUIRED"),
    (
        "blank-schedule-version",
        _set("current_schedule_version", ""),
        "IDENTIFIER_INVALID",
    ),
]


@pytest.mark.parametrize(
    ("change", "code"),
    [(c, k) for _, c, k in REJECTED],
    ids=[n for n, _, _ in REJECTED],
)
def test_malformed_snapshot_is_rejected_with_a_stable_code(
    change: Change, code: str
) -> None:
    with pytest.raises(SnapshotError) as caught:
        parse_snapshot(
            mutated(snapshot_doc(), change),
            expected_world_id="PRIMARY",
            policy=policy(),
        )
    assert caught.value.code == code


@pytest.mark.parametrize("world", [None, "", " PRIMARY", 7])
def test_expected_world_must_be_explicit(world: Any) -> None:
    with pytest.raises(SnapshotError) as caught:
        parse_snapshot(snapshot_doc(), expected_world_id=world, policy=policy())
    assert caught.value.path == "expected_world_id"


@pytest.mark.parametrize(
    "text",
    [
        '{"a": 1, "a": 2}',
        '{"contract_version": NaN}',
        '{"contract_version": Infinity}',
        '{"contract_version": -Infinity}',
        '{"contract_version": 1e999}',
        "[1,",
        "",
    ],
)
def test_strict_json_decoding(text: str) -> None:
    with pytest.raises(SnapshotError) as caught:
        parse_snapshot_json(text, expected_world_id="PRIMARY", policy=policy())
    assert caught.value.code == "JSON_INVALID"


def test_duplicate_field_nested_in_a_lot_is_rejected() -> None:
    text = '{"lots":[{"id":"A","id":"B"}]}'
    with pytest.raises(SnapshotError) as caught:
        parse_snapshot_json(text, expected_world_id="PRIMARY", policy=policy())
    assert caught.value.code == "JSON_INVALID"


def test_errors_never_echo_payload_values() -> None:
    doc = mutated(snapshot_doc(), _set("world_id", "SECRET-WORLD-VALUE"))
    with pytest.raises(SnapshotError) as caught:
        parse_snapshot(doc, expected_world_id="PRIMARY", policy=policy())
    assert "SECRET" not in str(caught.value) and "PRIMARY" not in str(caught.value)


def _at(delta: timedelta, base: str = "generated_at") -> datetime:
    start = datetime(2026, 10, 27, 8, 0, tzinfo=UTC)
    end = datetime(2026, 10, 27, 8, 5, tzinfo=UTC)
    return (start if base == "generated_at" else end) + delta


def test_expiry_end_is_exclusive_and_generation_instant_is_inclusive() -> None:
    doc = snapshot_doc()
    micro = timedelta(microseconds=1)
    parse_snapshot(doc, expected_world_id="PRIMARY", policy=policy(_at(timedelta(0))))
    parse_snapshot(
        doc, expected_world_id="PRIMARY", policy=policy(_at(-micro, "valid_until"))
    )
    with pytest.raises(SnapshotError) as future:
        parse_snapshot(doc, expected_world_id="PRIMARY", policy=policy(_at(-micro)))
    assert future.value.code == "SNAPSHOT_FROM_FUTURE"
    with pytest.raises(SnapshotError) as expired:
        parse_snapshot(
            doc,
            expected_world_id="PRIMARY",
            policy=policy(_at(timedelta(0), "valid_until")),
        )
    assert expired.value.code == "SNAPSHOT_NOT_USABLE"


@pytest.mark.parametrize(
    ("status", "now", "reasons"),
    [
        ("DEGRADED", NOW, ("STATUS_DEGRADED",)),
        ("STALE", NOW, ("STATUS_STALE",)),
        ("FRESH", datetime(2026, 10, 27, 8, 5, tzinfo=UTC), ("EXPIRED",)),
        (
            "STALE",
            datetime(2026, 10, 27, 9, 0, tzinfo=UTC),
            ("STATUS_STALE", "EXPIRED"),
        ),
    ],
)
def test_unsafe_snapshot_is_rejected_or_an_explicit_diagnostic(
    status: str, now: datetime, reasons: tuple[str, ...]
) -> None:
    doc = mutated(snapshot_doc(), _set("freshness/status", status))
    with pytest.raises(SnapshotError):
        parse_snapshot(doc, expected_world_id="PRIMARY", policy=policy(now))
    diagnostic = parse_snapshot(
        doc, expected_world_id="PRIMARY", policy=policy(now, FreshnessMode.DIAGNOSTIC)
    )
    assert diagnostic.usability is Usability.DIAGNOSTIC_ONLY
    assert diagnostic.diagnostics == reasons
    assert diagnostic.freshness_status.value == status  # never promoted to FRESH


def test_future_snapshot_is_never_accepted_even_as_a_diagnostic() -> None:
    early = datetime(2026, 10, 27, 7, 59, tzinfo=UTC)
    with pytest.raises(SnapshotError) as caught:
        parse_snapshot(
            snapshot_doc(),
            expected_world_id="PRIMARY",
            policy=policy(early, FreshnessMode.DIAGNOSTIC),
        )
    assert caught.value.code == "SNAPSHOT_FROM_FUTURE"


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 10, 27, 8, 1),
        datetime(2026, 10, 27, 11, 1, tzinfo=timezone(timedelta(hours=3))),
    ],
)
def test_caller_clock_must_be_aware_utc(now: datetime) -> None:
    with pytest.raises(SnapshotError) as caught:
        FreshnessPolicy(now)
    assert caught.value.code == "NOW_NOT_AWARE_UTC"


def test_reentrant_visits_stay_distinct_and_in_order() -> None:
    def add_reentrant_lot(doc: Doc) -> None:
        lot = dict(doc["lots"][0])
        lot.update(
            id="LOT-003",
            route_position=dict(
                lot["route_position"], visit_id="VISIT-A-01", position=0
            ),
        )
        lot["route_position"]["operation_class_id"] = "FINISH-CNC"
        doc["lots"].append(lot)

    snap = parsed_snapshot(mutated(snapshot_doc(), add_reentrant_lot))
    a, _, c = snap.lots
    assert a.visit.operation_class_id == c.visit.operation_class_id
    assert (a.visit.route_id, c.visit.route_id) == ("ROUTE-A", "ROUTE-A")
    assert (a.visit.visit_id, c.visit.visit_id) == ("VISIT-A-03", "VISIT-A-01")
    assert (a.visit.position, c.visit.position) == (2, 0)


def test_snapshot_is_immutable_and_detached_from_the_caller_payload() -> None:
    doc = snapshot_doc()
    snap = parsed_snapshot(doc)
    doc["lots"][0]["revision"] = "tampered"
    doc["world_id"] = "tampered"
    assert snap.lots[0].revision == "lot-rev-11" and snap.world_id == "PRIMARY"
    with pytest.raises(dataclasses.FrozenInstanceError):
        snap.world_id = "OTHER"  # type: ignore[misc]
    assert isinstance(snap.lots, tuple) and isinstance(
        snap.lots[0].eligible_equipment_ids, tuple
    )


def test_v1_snapshot_is_an_explicitly_incomplete_optimizer_input() -> None:
    planning_input = to_planning_input(parsed_snapshot())
    assert not planning_input.complete
    assert set(planning_input.gaps) == set(InputGap)
    with pytest.raises(IncompleteInputError) as caught:
        planning_input.require_full_instance()
    assert set(caught.value.missing) == {
        "PROCESSING_DURATIONS",
        "REMAINING_ROUTE",
        "MATERIAL_HOLDS",
        "QUEUES",
        "MAINTENANCE_WINDOWS",
        "SIMULATION_TIME",
    }


def test_reader_is_called_once_for_the_requested_world_only() -> None:
    calls: list[str] = []

    class Reader:
        def read_scheduling_snapshot(self, world_id: str) -> dict[str, Any]:
            calls.append(world_id)
            return snapshot_doc()

    result = read_planning_input(Reader(), world_id="PRIMARY", policy=policy())
    assert calls == ["PRIMARY"] and result.snapshot.world_id == "PRIMARY"
    with pytest.raises(SnapshotError):
        read_planning_input(Reader(), world_id="", policy=policy())
    assert calls == ["PRIMARY"]  # an invalid request never reaches the reader
    with pytest.raises(SnapshotError) as caught:
        read_planning_input(Reader(), world_id="COUNTERFACTUAL-1", policy=policy())
    assert caught.value.code == "WORLD_MISMATCH" and calls[-1] == "COUNTERFACTUAL-1"
