"""TEST-SIM-KERNEL: dispatch, termination, failure and validation semantics."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from manufacturing_simulator import (
    PROVENANCE,
    DuplicateHandlerError,
    EventSpec,
    ExecutionContext,
    HandlerExecutionError,
    InitialEventSpec,
    InvalidConfigurationError,
    InvalidTimeError,
    Kernel,
    KernelScenarioConfig,
    PastSchedulingError,
    RandomnessManager,
    RecordOutcome,
    RunFailedError,
    RunStatus,
    ScenarioEngine,
    ScheduledEvent,
    SimulatorError,
    StepOutcome,
    TerminationReason,
    UnknownEventKindError,
)

Seen = list[tuple[int, str]]


def make_kernel(
    events: list[tuple[int, str]],
    handlers: dict[str, Any] | None = None,
    kinds: tuple[str, ...] = ("a", "b", "c"),
    horizon: int = 1000,
) -> tuple[Kernel, Seen]:
    seen: Seen = []

    def record(event: ScheduledEvent, context: ExecutionContext) -> None:
        seen.append((context.now, event.kind))

    config = KernelScenarioConfig(
        scenario_id="k",
        scenario_version="1",
        seed=1,
        simulator_version="sim-0",
        horizon=horizon,
        initial_events=tuple(
            InitialEventSpec(f"e{i}", time, kind)
            for i, (time, kind) in enumerate(events)
        ),
    )
    world = ScenarioEngine(kinds).initialize(config)
    return Kernel(world, handlers or {kind: record for kind in kinds}), seen


def untouched(kernel: Kernel) -> tuple[Any, ...]:
    world = kernel.world
    return (
        world.clock.now,
        world.queue.pending(),
        world.queue.scheduled_total,
        dict(world.state),
        kernel.records(),
        kernel.status(),
    )


def test_step_on_empty_queue_reports_no_event() -> None:
    kernel, _ = make_kernel([])
    result = kernel.step()
    assert result.outcome is StepOutcome.NO_EVENT and result.record is None
    assert kernel.world.clock.now == 0


def test_step_executes_one_event_and_advances_the_clock() -> None:
    kernel, seen = make_kernel([(7, "a"), (9, "b")])
    result = kernel.step()
    assert result.outcome is StepOutcome.EXECUTED
    assert seen == [(7, "a")] and kernel.world.clock.now == 7
    assert len(kernel.world.queue) == 1


def test_records_carry_simulation_provenance_and_correlation() -> None:
    kernel, _ = make_kernel([(2, "a")])
    kernel.run_to_horizon(10)
    (record,) = kernel.records()
    assert record.provenance == PROVENANCE == "SIMULATION"
    assert record.correlation_id == "k/1/seed-1"
    assert (record.sequence, record.time, record.kind) == (0, 2, "a")
    assert record.event_id == "e0" and record.outcome is RecordOutcome.EXECUTED
    with pytest.raises(dataclasses.FrozenInstanceError):
        record.time = 3  # pyright: ignore[reportAttributeAccessIssue]


def test_records_expose_no_oracle_fields() -> None:
    names = {f.name for f in dataclasses.fields(make_kernel([(0, "a")])[0].status())}
    names |= {f.name for f in dataclasses.fields(ScheduledEvent)}
    forbidden = {"oracle", "label", "truth", "hidden"}
    assert not any(token in name for name in names for token in forbidden)


def test_status_view() -> None:
    kernel, _ = make_kernel([(1, "a"), (50, "b")])
    status = kernel.status()
    assert status.status is RunStatus.READY and status.provenance == "SIMULATION"
    assert (status.processed_events, status.queue_depth, status.now) == (0, 2, 0)
    assert status.last_termination is None
    kernel.run(10, 10)
    status = kernel.status()
    assert status.last_termination is TerminationReason.HORIZON_REACHED
    assert (status.processed_events, status.queue_depth, status.now) == (1, 1, 1)


times = st.integers(min_value=0, max_value=30)


@given(st.lists(st.tuples(times, st.sampled_from(["a", "b", "c"])), max_size=40))
def test_run_executes_in_reference_order_with_a_monotonic_clock(
    events: list[tuple[int, str]],
) -> None:
    kernel, seen = make_kernel(events)
    result = kernel.run(1000, 1000)
    reference = sorted(range(len(events)), key=lambda i: (events[i][0], i))
    assert [kind for _, kind in seen] == [events[i][1] for i in reference]
    clock_values = [time for time, _ in seen]
    assert clock_values == sorted(clock_values)
    assert result.termination is TerminationReason.QUEUE_EMPTY
    assert result.processed == len(events)
    assert len(kernel.records()) + len(kernel.world.queue) == len(events)
    assert kernel.world.queue.scheduled_total == len(events)


@given(
    st.lists(st.tuples(times, st.just("a")), max_size=30),
    st.integers(0, 40),
    st.integers(1, 10),
)
def test_horizon_and_budget_never_drop_events(
    events: list[tuple[int, str]], horizon: int, budget: int
) -> None:
    kernel, seen = make_kernel(events)
    kernel.run(horizon, budget)
    eligible = sum(1 for time, _ in events if time <= horizon)
    assert len(seen) == min(eligible, budget)
    assert len(seen) + len(kernel.world.queue) == len(events)
    assert all(time <= horizon for time, _ in seen)


def test_handler_inserted_equal_time_event_runs_after_existing_ones() -> None:
    order: list[str] = []

    def a(event: ScheduledEvent, context: ExecutionContext) -> None:
        order.append("a")
        context.schedule(EventSpec(context.now, "c"))

    def b(event: ScheduledEvent, context: ExecutionContext) -> None:
        order.append("b")

    def c(event: ScheduledEvent, context: ExecutionContext) -> None:
        order.append("c")

    kernel, _ = make_kernel([(5, "a"), (5, "b")], {"a": a, "b": b, "c": c})
    kernel.run(10, 10)
    assert order == ["a", "b", "c"]


def test_event_exactly_at_the_horizon_executes() -> None:
    kernel, seen = make_kernel([(10, "a"), (11, "b")])
    result = kernel.run(10, 10)
    assert seen == [(10, "a")]
    assert result.termination is TerminationReason.HORIZON_REACHED
    assert len(kernel.world.queue) == 1


def test_clock_is_not_advanced_to_the_horizon_and_the_run_can_continue() -> None:
    kernel, seen = make_kernel([(3, "a"), (20, "b")])
    first = kernel.run(10, 10)
    assert first.now == 3 and kernel.world.clock.now == 3
    second = kernel.run(25, 10)
    assert seen == [(3, "a"), (20, "b")]
    assert second.termination is TerminationReason.QUEUE_EMPTY and second.now == 20


def test_event_budget_stops_the_run_and_keeps_the_rest_queued() -> None:
    kernel, seen = make_kernel([(i, "a") for i in range(5)])
    result = kernel.run(100, 2)
    assert result.termination is TerminationReason.EVENT_LIMIT_REACHED
    assert result.processed == 2 and result.queue_depth == 3 and len(seen) == 2


def test_termination_precedence_is_empty_then_horizon_then_budget() -> None:
    kernel, _ = make_kernel([(1, "a"), (2, "a")])
    assert kernel.run(100, 2).termination is TerminationReason.QUEUE_EMPTY
    kernel, _ = make_kernel([(1, "a"), (50, "a")])
    assert kernel.run(10, 1).termination is TerminationReason.HORIZON_REACHED
    kernel, _ = make_kernel([(1, "a"), (2, "a")])
    assert kernel.run(100, 1).termination is TerminationReason.EVENT_LIMIT_REACHED


def test_run_to_horizon_uses_the_scenario_horizon() -> None:
    kernel, seen = make_kernel([(5, "a")], horizon=100)
    kernel.schedule(EventSpec(500, "b"))  # beyond the configured horizon
    result = kernel.run_to_horizon(10)
    assert seen == [(5, "a")]
    assert result.termination is TerminationReason.HORIZON_REACHED
    assert result.queue_depth == 1


def test_zero_time_rescheduling_is_bounded_by_the_event_budget() -> None:
    count = 0

    def forever(event: ScheduledEvent, context: ExecutionContext) -> None:
        nonlocal count
        count += 1
        context.schedule(EventSpec(context.now, "a"))

    kernel, _ = make_kernel([(4, "a")], {"a": forever}, kinds=("a",))
    result = kernel.run(100, 50)
    assert result.termination is TerminationReason.EVENT_LIMIT_REACHED
    assert count == 50 and result.queue_depth == 1 and kernel.world.clock.now == 4


@pytest.mark.parametrize("bad", [-1, True, 1.5, "5", None])
def test_invalid_horizons_are_rejected_before_any_event_runs(bad: Any) -> None:
    kernel, _ = make_kernel([(1, "a")])
    before = untouched(kernel)
    with pytest.raises(InvalidTimeError):
        kernel.run(bad, 10)
    assert untouched(kernel) == before


def test_backwards_horizon_is_rejected_before_any_event_runs() -> None:
    kernel, _ = make_kernel([(5, "a"), (9, "a")])
    kernel.run(5, 10)
    before = untouched(kernel)
    with pytest.raises(InvalidTimeError):
        kernel.run(4, 10)
    assert untouched(kernel) == before


@pytest.mark.parametrize("bad", [0, -1, True, 1.5, "5", None])
def test_invalid_budgets_are_rejected_before_any_event_runs(bad: Any) -> None:
    kernel, _ = make_kernel([(1, "a")])
    before = untouched(kernel)
    with pytest.raises(InvalidConfigurationError):
        kernel.run(10, bad)
    assert untouched(kernel) == before


def test_scheduling_an_unknown_kind_is_rejected_without_mutation() -> None:
    kernel, _ = make_kernel([(1, "a")])
    before = untouched(kernel)
    with pytest.raises(UnknownEventKindError):
        kernel.schedule(EventSpec(5, "nope"))
    assert untouched(kernel) == before


def test_scheduling_in_the_past_is_rejected_without_mutation() -> None:
    kernel, _ = make_kernel([(5, "a")])
    kernel.step()
    before = untouched(kernel)
    with pytest.raises(PastSchedulingError):
        kernel.schedule(EventSpec(4, "a"))
    assert untouched(kernel) == before
    assert kernel.schedule(EventSpec(5, "a")).sequence == 1


def test_event_without_a_handler_is_rejected_before_consumption() -> None:
    kernel, _ = make_kernel([(3, "a"), (4, "b")], {"b": lambda e, c: None})
    before = untouched(kernel)
    with pytest.raises(UnknownEventKindError):
        kernel.step()
    with pytest.raises(UnknownEventKindError):
        kernel.run(10, 10)
    assert untouched(kernel) == before
    assert kernel.status().status is RunStatus.READY


def test_duplicate_and_invalid_handler_registration() -> None:
    kernel, _ = make_kernel([])
    with pytest.raises(DuplicateHandlerError):
        kernel.register_handler("a", lambda e, c: None)
    with pytest.raises(InvalidConfigurationError):
        kernel.register_handler("", lambda e, c: None)
    with pytest.raises(InvalidConfigurationError):
        kernel.register_handler("fresh", "not-callable")  # pyright: ignore[reportArgumentType]
    kernel.register_handler("fresh", lambda e, c: None)
    assert kernel.schedule(EventSpec(0, "fresh")).kind == "fresh"


def failing_kernel() -> tuple[Kernel, list[str]]:
    calls: list[str] = []

    def ok(event: ScheduledEvent, context: ExecutionContext) -> None:
        calls.append("ok")
        context.state["touched"] = 1

    def boom(event: ScheduledEvent, context: ExecutionContext) -> None:
        calls.append("boom")
        context.state["partial"] = 1
        raise ValueError("synthetic handler failure")

    kernel, _ = make_kernel(
        [(1, "a"), (2, "b"), (3, "a"), (4, "a")],
        {"a": ok, "b": boom},
        kinds=("a", "b"),
    )
    return kernel, calls


def test_handler_failure_fails_the_run_with_event_context() -> None:
    kernel, calls = failing_kernel()
    with pytest.raises(HandlerExecutionError) as caught:
        kernel.run(100, 100)
    error = caught.value
    assert (error.sequence, error.time, error.kind) == (1, 2, "b")
    assert isinstance(error.__cause__, ValueError)
    assert calls == ["ok", "boom"]
    assert kernel.status().status is RunStatus.FAILED
    failed = kernel.records()[-1]
    assert failed.outcome is RecordOutcome.FAILED and failed.kind == "b"
    assert failed.error is not None and "synthetic handler failure" in failed.error
    assert kernel.status().processed_events == 1
    # Partial mutation by the failed handler is kept, never rolled back.
    assert kernel.world.state == {"touched": 1, "partial": 1}


def test_a_failed_run_cannot_be_resumed_extended_or_retried() -> None:
    kernel, calls = failing_kernel()
    with pytest.raises(HandlerExecutionError):
        kernel.run(100, 100)
    before = untouched(kernel)
    with pytest.raises(RunFailedError):
        kernel.step()
    with pytest.raises(RunFailedError):
        kernel.run(100, 100)
    with pytest.raises(RunFailedError):
        kernel.schedule(EventSpec(10, "a"))
    assert untouched(kernel) == before
    assert calls == ["ok", "boom"]
    assert len(kernel.world.queue) == 2


def test_a_handler_scheduling_into_the_past_fails_the_run() -> None:
    def bad(event: ScheduledEvent, context: ExecutionContext) -> None:
        context.schedule(EventSpec(context.now - 1, "a"))

    kernel, _ = make_kernel([(5, "a")], {"a": bad}, kinds=("a",))
    with pytest.raises(HandlerExecutionError) as caught:
        kernel.step()
    assert isinstance(caught.value.__cause__, PastSchedulingError)
    assert kernel.status().status is RunStatus.FAILED


def test_a_handler_scheduling_an_unknown_kind_fails_the_run() -> None:
    def bad(event: ScheduledEvent, context: ExecutionContext) -> None:
        context.schedule(EventSpec(context.now, "ghost"))

    kernel, _ = make_kernel([(5, "a")], {"a": bad}, kinds=("a",))
    with pytest.raises(HandlerExecutionError) as caught:
        kernel.step()
    assert isinstance(caught.value.__cause__, UnknownEventKindError)


def test_a_handler_cannot_reenter_the_kernel() -> None:
    holder: list[Kernel] = []

    def reenter(event: ScheduledEvent, context: ExecutionContext) -> None:
        holder[0].step()

    kernel, _ = make_kernel([(1, "a")], {"a": reenter}, kinds=("a",))
    holder.append(kernel)
    with pytest.raises(HandlerExecutionError) as caught:
        kernel.step()
    assert isinstance(caught.value.__cause__, SimulatorError)
    assert kernel.status().status is RunStatus.FAILED


def test_handlers_reach_streams_only_through_the_context() -> None:
    def draw(event: ScheduledEvent, context: ExecutionContext) -> None:
        context.state["draw"] = int(context.stream("arrival").integers(0, 10**6))

    kernel, _ = make_kernel([(1, "a")], {"a": draw}, kinds=("a",))
    kernel.step()
    reference = RandomnessManager(1).stream("arrival").integers(0, 10**6)
    assert kernel.world.state["draw"] == int(reference)


def test_kernels_built_from_one_config_are_independent() -> None:
    first, first_seen = make_kernel([(1, "a"), (2, "a")])
    second, second_seen = make_kernel([(1, "a"), (2, "a")])
    first.run(10, 10)
    assert first_seen and not second_seen
    assert len(second.world.queue) == 2 and second.world.clock.now == 0


class Halt(BaseException):
    """A custom control-flow exception outside the ``Exception`` hierarchy."""


def interrupted_kernel(exc: type[BaseException]) -> tuple[Kernel, list[str]]:
    calls: list[str] = []

    def ok(event: ScheduledEvent, context: ExecutionContext) -> None:
        calls.append("ok")
        context.state["touched"] = 1

    def interrupt(event: ScheduledEvent, context: ExecutionContext) -> None:
        calls.append("interrupt")
        context.state["partial"] = 1
        raise exc()

    kernel, _ = make_kernel(
        [(1, "a"), (2, "b"), (3, "a"), (4, "a")],
        {"a": ok, "b": interrupt},
        kinds=("a", "b"),
    )
    return kernel, calls


@pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit, Halt])
def test_interruption_is_recorded_fails_the_run_and_propagates(
    exc: type[BaseException],
) -> None:
    kernel, calls = interrupted_kernel(exc)
    with pytest.raises(exc):
        kernel.run(100, 100)
    assert calls == ["ok", "interrupt"]
    status = kernel.status()
    assert status.status is RunStatus.FAILED and status.processed_events == 1
    records = kernel.records()
    assert [r.outcome for r in records] == [
        RecordOutcome.EXECUTED,
        RecordOutcome.FAILED,
    ]
    failed = records[-1]
    assert (failed.sequence, failed.time, failed.kind) == (1, 2, "b")
    assert failed.error is not None and exc.__name__ in failed.error
    # Partial mutation is retained (no rollback claim); unprocessed events stay queued.
    assert kernel.world.state == {"touched": 1, "partial": 1}
    assert [(e.time, e.kind) for e in kernel.world.queue.pending()] == [
        (3, "a"),
        (4, "a"),
    ]
    assert kernel.world.clock.now == 2


@pytest.mark.parametrize("exc", [KeyboardInterrupt, SystemExit, Halt])
def test_an_interrupted_run_cannot_be_resumed_or_extended(
    exc: type[BaseException],
) -> None:
    kernel, calls = interrupted_kernel(exc)
    with pytest.raises(exc):
        kernel.step()
        kernel.step()
    before = untouched(kernel)
    with pytest.raises(RunFailedError):
        kernel.step()
    with pytest.raises(RunFailedError):
        kernel.run(100, 100)
    with pytest.raises(RunFailedError):
        kernel.schedule(EventSpec(10, "a"))
    assert untouched(kernel) == before
    assert calls == ["ok", "interrupt"]


def test_interruption_is_not_wrapped_as_a_handler_error() -> None:
    kernel, _ = interrupted_kernel(KeyboardInterrupt)
    with pytest.raises(KeyboardInterrupt) as caught:
        kernel.run(100, 100)
    assert not isinstance(caught.value, HandlerExecutionError)
