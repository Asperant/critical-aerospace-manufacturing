"""Canonical bytes and digests of replay (FR-SIM-008): golden vectors, type and order
sensitivity, excluded provenance, and rejection of malformed records.

Golden bytes and SHA-256 values are literals written out by hand and hashed with
``hashlib`` on the literal, not produced by the code under test.
"""

from __future__ import annotations

import dataclasses
import math
from typing import Any

import pytest
from manufacturing_simulator import (
    CanonicalizationError,
    EventSpec,
    ExecutionRecord,
    InitialEventSpec,
    KernelScenarioConfig,
    RecordOutcome,
    ScenarioEngine,
    event_sequence_digest,
    final_state_digest,
    input_digest,
)
from manufacturing_simulator.serialization import (
    canonical_bytes,
    decode_events_document,
    decode_state_document,
    encode_value,
    events_document,
    project_records,
    project_world,
    state_document,
)

EMPTY_EVENTS = '["sim-replay-hash/1","events",[]]'
EMPTY_EVENTS_SHA = "6c20ab2c9fc484e19932ce7bbe6928f7b40d16003f5431f4824e451f1d375c4d"
ONE_EVENT = (
    '["sim-replay-hash/1","events",[[0,5,"arrive","e-1",[["a",["s","é"]],'
    '["b",["f","0x1.8000000000000p+0"]],["c",["n"]],["d",["b",true]],'
    '["z",["f","-0x0.0p+0"]]],"EXECUTED"]]]'
)
ONE_EVENT_SHA = "f5dcb8372a6dabbc29d7a68c27b8d5ed644f4845159b6d817b42efadefdbc0f8"
STATE = '["sim-replay-hash/1","state",7,[["k",["i",2]]],3,[[2,9,"x",null,[]]]]'
STATE_SHA = "fb752235bb9055812f9f870cccc35d7e1c05ff205e88edd63b69a06f3943f70e"
INPUT = (
    '["sim-replay-hash/1","input",["s","1",1,"v","us",10,[["i0",0,"arrive",[]]]],'
    "[],10,100]"
)
INPUT_SHA = "6c455052cbf64d17fd43bcaad71abcb4bc3a2d1f6890e59b519d35980d82b395"


def record(**changes: Any) -> ExecutionRecord:
    fields: dict[str, Any] = {
        "correlation_id": "c/1/seed-1",
        "provenance": "SIMULATION",
        "sequence": 0,
        "time": 5,
        "kind": "arrive",
        "event_id": "e-1",
        "payload": (("a", "é"), ("b", 1.5), ("c", None), ("d", True), ("z", -0.0)),
        "outcome": RecordOutcome.EXECUTED,
        "error": None,
    }
    return ExecutionRecord(**{**fields, **changes})


def world(*, local: dict[str, Any] | None = None, pending_kind: str = "x"):
    """now=7, three sequences issued, one event pending at sequence 2 (time 9)."""
    config = KernelScenarioConfig("s", "1", 1, "v", 10)
    built = ScenarioEngine(["x", "y"]).initialize(config)
    for spec in (EventSpec(1, "y"), EventSpec(2, "y"), EventSpec(9, pending_kind)):
        built.queue.schedule(spec, now=0)
    built.queue.pop()
    built.queue.pop()
    built.clock.advance_to(7)
    built.state.update({"k": 2} if local is None else local)
    return built


def test_golden_vectors_match_hand_written_bytes_and_hashes() -> None:
    assert (
        canonical_bytes(events_document(project_records([]))) == EMPTY_EVENTS.encode()
    )
    assert event_sequence_digest([]) == EMPTY_EVENTS_SHA
    one = project_records([record()])
    assert canonical_bytes(events_document(one)) == ONE_EVENT.encode("utf-8")
    assert event_sequence_digest([record()]) == ONE_EVENT_SHA
    assert canonical_bytes(state_document(project_world(world()))) == STATE.encode()
    assert final_state_digest(world()) == STATE_SHA
    config = KernelScenarioConfig(
        "s", "1", 1, "v", 10, initial_events=(InitialEventSpec("i0", 0, "arrive"),)
    )
    assert input_digest(config, (), 10, 100) == INPUT_SHA


def test_the_documents_decode_back_to_the_same_semantics() -> None:
    events = project_records([record()])
    assert decode_events_document(events_document(events)) == events
    state = project_world(world())
    assert decode_state_document(state_document(state)) == state


@pytest.mark.parametrize(
    ("value", "document"),
    [
        (None, ["n"]),
        (True, ["b", True]),
        (1, ["i", 1]),
        (2**70, ["i", 2**70]),
        (0.1, ["f", "0x1.999999999999ap-4"]),
        (5e-324, ["f", "0x0.0000000000001p-1022"]),
        (-0.0, ["f", "-0x0.0p+0"]),
        ("1", ["s", "1"]),
    ],
)
def test_values_have_exact_tagged_documents(value: Any, document: list[Any]) -> None:
    assert encode_value(value) == document


@pytest.mark.parametrize(
    ("a", "b"),
    [(1, True), (1, 1.0), (1, "1"), (0.0, -0.0), (None, "n"), ("é", "é")],
)
def test_distinct_values_never_share_a_digest(a: Any, b: Any) -> None:
    assert event_sequence_digest([record(payload=(("v", a),))]) != (
        event_sequence_digest([record(payload=(("v", b),))])
    )


def test_payload_construction_order_never_changes_the_digest() -> None:
    forward = record(payload=(("a", 1), ("b", 2)))
    backward = record(payload=(("b", 2), ("a", 1)))
    assert event_sequence_digest([forward]) == event_sequence_digest([backward])
    state_a, state_b = {"x": 1, "y": 2}, {"y": 2, "x": 1}
    assert final_state_digest(world(local=state_a)) == final_state_digest(
        world(local=state_b)
    )


def test_excluded_provenance_cannot_change_a_digest_but_everything_else_does() -> None:
    base = event_sequence_digest([record()])
    assert event_sequence_digest([record(correlation_id="other/9/seed-9")]) == base
    assert event_sequence_digest([record(error="repr of an exception")]) == base
    for change in (
        {"sequence": 1},
        {"time": 6},
        {"kind": "start"},
        {"event_id": "e-2"},
        {"event_id": None},
        {"payload": ()},
        {"payload": (("a", "é"), ("b", 1.5), ("c", None), ("d", False), ("z", -0.0))},
    ):
        assert event_sequence_digest([record(**change)]) != base, change


def test_event_order_and_content_are_part_of_the_hash() -> None:
    first = record(sequence=0, time=1, kind="a")
    second = record(sequence=1, time=1, kind="b")
    swapped = (
        record(sequence=0, time=1, kind="b"),
        record(sequence=1, time=1, kind="a"),
    )
    assert event_sequence_digest([first, second]) != event_sequence_digest(swapped)
    assert event_sequence_digest([first, second]) != event_sequence_digest([first])
    with pytest.raises(CanonicalizationError):
        event_sequence_digest([second, first])


def test_equal_queue_depth_with_different_pending_events_has_a_different_digest() -> (
    None
):
    base = world()
    other = world(pending_kind="y")
    assert len(base.queue) == len(other.queue) == 1
    assert final_state_digest(base) != final_state_digest(other)


@pytest.mark.parametrize("change", ["local", "clock", "next_sequence"])
def test_every_final_state_component_is_covered(change: str) -> None:
    base, other = world(), world()
    if change == "local":
        other.state["k"] = 3
    elif change == "clock":
        other.clock.advance_to(8)
    else:
        other.queue.schedule(EventSpec(9, "x"), now=7)
        other.queue.pop()
        other.queue.pop()
    assert final_state_digest(base) != final_state_digest(other)


@pytest.mark.parametrize(
    "bad",
    [
        record(payload=(("v", math.nan),)),
        record(payload=(("v", math.inf),)),
        record(payload=(("v", [1]),)),
        record(payload=(("v", b"x"),)),
        record(payload=(("v", "\ud800"),)),
        record(payload=(("a", 1), ("a", 2))),
        record(payload=((1, 1),)),
        record(sequence=True),
        record(time=True),
        record(time=-1),
        record(kind=""),
        record(event_id=7),
        record(outcome=RecordOutcome.FAILED, error="boom"),
        record(provenance="REAL"),
        record(correlation_id=None),
    ],
)
def test_malformed_records_are_rejected_at_the_hashing_boundary(
    bad: ExecutionRecord,
) -> None:
    with pytest.raises(CanonicalizationError):
        event_sequence_digest([bad])


def test_repeated_or_non_record_entries_are_rejected() -> None:
    with pytest.raises(CanonicalizationError):
        event_sequence_digest([record(), record()])
    not_a_record: Any = dataclasses.asdict(record())
    with pytest.raises(CanonicalizationError):
        event_sequence_digest([not_a_record])


def test_a_sequence_repeated_at_a_later_time_is_rejected() -> None:
    first = record(sequence=0, time=1)
    with pytest.raises(CanonicalizationError):
        event_sequence_digest([first, record(sequence=0, time=2)])


def test_decoding_checks_order_and_uniqueness_itself() -> None:
    def event(sequence: int, time: int) -> list[Any]:
        return [sequence, time, "k", None, [], "EXECUTED"]

    for records in ([event(1, 5), event(0, 5)], [event(0, 1), event(0, 2)]):
        with pytest.raises(CanonicalizationError):
            decode_events_document(["sim-replay-hash/1", "events", records])
    pending = [[3, 9, "x", None, []], [2, 9, "x", None, []]]  # (9, 3) before (9, 2)
    with pytest.raises(CanonicalizationError):
        decode_state_document(["sim-replay-hash/1", "state", 7, [], 4, pending])


def test_unsupported_local_state_is_rejected() -> None:
    for bad in ({"k": math.nan}, {"k": (1, 2)}, {"k": {"n": 1}}):
        with pytest.raises(CanonicalizationError):
            final_state_digest(world(local=bad))


@pytest.mark.parametrize(
    "document",
    [
        "not a list",
        ["sim-replay-hash/1", "events"],
        ["sim-replay-hash/0", "events", []],
        [
            "sim-replay-hash/1",
            "events",
            [[0, 5, "k", None, [["b", ["i", True]]], "EXECUTED"]],
        ],
        [
            "sim-replay-hash/1",
            "events",
            [[0, 5, "k", None, [["b", ["f", "1.5"]]], "EXECUTED"]],
        ],
        [
            "sim-replay-hash/1",
            "events",
            [[0, 5, "k", None, [["b", ["i", 1]], ["a", ["i", 1]]], "EXECUTED"]],
        ],
        ["sim-replay-hash/1", "events", [[0, 5, "k", None, [], "FAILED"]]],
    ],
)
def test_non_canonical_or_malformed_documents_are_not_decoded(document: Any) -> None:
    with pytest.raises(CanonicalizationError):
        decode_events_document(document)
