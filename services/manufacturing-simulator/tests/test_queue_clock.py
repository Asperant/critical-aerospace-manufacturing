"""TEST-SIM-KERNEL: future-event queue ordering and the simulation clock."""

from __future__ import annotations

import math
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from manufacturing_simulator import (
    EventSpec,
    FutureEventQueue,
    InvalidConfigurationError,
    InvalidTimeError,
    PastSchedulingError,
    SimulationClock,
    TimeUnit,
    make_payload,
)

times = st.integers(min_value=0, max_value=50)


@given(st.lists(times, max_size=60))
def test_pops_match_independent_sorted_reference(schedule: list[int]) -> None:
    queue = FutureEventQueue()
    for index, time in enumerate(schedule):
        queue.schedule(EventSpec(time, "k", make_payload({"i": index})), now=0)
    reference = sorted(range(len(schedule)), key=lambda i: (schedule[i], i))
    popped = []
    while (event := queue.pop()) is not None:
        popped.append(event)
    assert [dict(e.payload)["i"] for e in popped] == reference
    assert [e.time for e in popped] == sorted(schedule)
    assert [e.sequence for e in popped] == reference
    assert queue.empty and queue.pop() is None and queue.peek() is None


@given(
    st.lists(
        st.one_of(st.tuples(st.just("push"), st.integers(0, 20)), st.just("pop")),
        max_size=80,
    )
)
def test_interleaved_operations_match_model_and_time_is_monotonic(
    ops: list[Any],
) -> None:
    queue = FutureEventQueue()
    model: list[tuple[int, int]] = []
    now = 0
    sequence = 0
    last_popped = 0
    for op in ops:
        if op == "pop":
            event = queue.pop()
            if not model:
                assert event is None
                continue
            expected = min(model)
            model.remove(expected)
            assert event is not None
            assert (event.time, event.sequence) == expected
            assert event.time >= last_popped
            last_popped = now = event.time
        else:
            _, delta = op
            queue.schedule(EventSpec(now + delta, "k"), now=now)
            model.append((now + delta, sequence))
            sequence += 1
        assert len(queue) == len(model)
        assert queue.scheduled_total == sequence
    assert [(e.time, e.sequence) for e in queue.pending()] == sorted(model)


@given(st.lists(times, max_size=40))
def test_events_are_conserved(schedule: list[int]) -> None:
    queue = FutureEventQueue()
    for time in schedule:
        queue.schedule(EventSpec(time, "k"), now=0)
    popped = 0
    while queue.pop() is not None:
        popped += 1
    assert popped == len(schedule) == queue.scheduled_total


def test_equal_time_events_are_fifo() -> None:
    queue = FutureEventQueue()
    for name in ("a", "b", "c"):
        queue.schedule(EventSpec(7, name), now=0)
    assert [e.kind for e in queue.pending()] == ["a", "b", "c"]
    drained = []
    while (event := queue.pop()) is not None:
        drained.append(event.kind)
    assert drained == ["a", "b", "c"]


def test_payloads_are_never_compared() -> None:
    queue = FutureEventQueue()
    queue.schedule(EventSpec(1, "k", make_payload({"v": "text"})), now=0)
    queue.schedule(EventSpec(1, "k", make_payload({"v": 3})), now=0)
    queue.schedule(EventSpec(1, "k", make_payload({"v": None})), now=0)
    assert [dict(e.payload)["v"] for e in queue.pending()] == ["text", 3, None]


def test_past_scheduling_is_rejected_without_mutation() -> None:
    queue = FutureEventQueue()
    queue.schedule(EventSpec(10, "k"), now=0)
    before = (len(queue), queue.scheduled_total, queue.pending())
    with pytest.raises(PastSchedulingError):
        queue.schedule(EventSpec(4, "k"), now=5)
    assert (len(queue), queue.scheduled_total, queue.pending()) == before
    assert queue.schedule(EventSpec(5, "k"), now=5).time == 5


def test_empty_queue_has_explicit_outcomes() -> None:
    queue = FutureEventQueue()
    assert queue.empty and len(queue) == 0
    assert queue.peek() is None and queue.pop() is None
    assert queue.pending() == ()


def test_peek_does_not_consume() -> None:
    queue = FutureEventQueue()
    queue.schedule(EventSpec(3, "k"), now=0)
    assert queue.peek() is queue.peek()
    assert len(queue) == 1


def test_large_times_are_exact() -> None:
    big = 2**62
    queue = FutureEventQueue()
    queue.schedule(EventSpec(big + 1, "late"), now=0)
    queue.schedule(EventSpec(big, "early"), now=0)
    assert [e.kind for e in queue.pending()] == ["early", "late"]


@pytest.mark.parametrize("bad", [-1, True, False, 1.0, 2.5, "3", None, math.nan])
def test_invalid_event_times_are_rejected(bad: Any) -> None:
    with pytest.raises(InvalidTimeError):
        EventSpec(bad, "k")


@pytest.mark.parametrize("bad", ["", " k", "k ", None, 3])
def test_invalid_event_kinds_are_rejected(bad: Any) -> None:
    with pytest.raises(InvalidConfigurationError):
        EventSpec(1, bad)


def test_invalid_now_is_rejected() -> None:
    with pytest.raises(InvalidTimeError):
        FutureEventQueue().schedule(EventSpec(1, "k"), now=-1)


def test_payload_is_canonical_and_immutable() -> None:
    spec = EventSpec(1, "k", make_payload({"b": 2, "a": 1}))
    assert spec.payload == (("a", 1), ("b", 2))
    assert EventSpec(1, "k", (("b", 2), ("a", 1))).payload == spec.payload
    with pytest.raises(AttributeError):
        spec.time = 2  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    "payload",
    [
        {"x": [1, 2]},
        {"x": {"nested": 1}},
        {"x": math.nan},
        {"x": math.inf},
        {"": 1},
        {3: 1},
    ],
)
def test_malformed_payloads_are_rejected(payload: Any) -> None:
    with pytest.raises(InvalidConfigurationError):
        make_payload(payload)


def test_duplicate_payload_keys_are_rejected() -> None:
    with pytest.raises(InvalidConfigurationError):
        EventSpec(1, "k", (("a", 1), ("a", 2)))


def test_clock_starts_at_zero_and_only_moves_forward() -> None:
    clock = SimulationClock()
    assert clock.now == 0 and clock.unit is TimeUnit.MICROSECOND
    clock.advance_to(5)
    clock.advance_to(5)
    assert clock.now == 5
    with pytest.raises(InvalidTimeError):
        clock.advance_to(4)
    assert clock.now == 5


@pytest.mark.parametrize("bad", [-1, True, 1.5, "1", None])
def test_clock_rejects_invalid_times(bad: Any) -> None:
    clock = SimulationClock()
    with pytest.raises(InvalidTimeError):
        clock.advance_to(bad)
    assert clock.now == 0


def test_clock_exposes_no_setter() -> None:
    clock = SimulationClock()
    with pytest.raises(AttributeError):
        clock.now = 3  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize(
    "payload",
    [
        5,
        "ab",
        None,
        (1,),
        ("ab",),
        (("a",),),
        (("a", 1, 2),),
        ((1, 2),),
        ((["k"], 2),),
        (("a", [1]),),
        (("a", {"n": 1}),),
    ],
)
def test_malformed_typed_payloads_raise_the_configuration_error(payload: Any) -> None:
    with pytest.raises(InvalidConfigurationError):
        EventSpec(1, "k", payload)
