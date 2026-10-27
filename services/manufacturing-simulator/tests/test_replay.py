"""Public replay API (FR-SIM-008, NFR-REP-001 H0): equality, isolation, identity,
completeness, failure paths and fresh-process replays.

Structural validation of results and the negative matrices are in
``test_replay_validation``. Toy scenario only: these tests bound kernel mechanics for
the supplied handlers. They are not BENCH-SIMVAL-001, REPRO-NONOWNER-001 or a proof
for arbitrary handlers.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
from collections.abc import Callable
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from manufacturing_simulator import (
    MAX_SEED,
    CanonicalizationError,
    ComparisonOutcome,
    HandlerExecutionError,
    IncompatibleRuntimeError,
    InvalidConfigurationError,
    InvalidTimeError,
    ReplayExecutionError,
    ReplayIdentity,
    ReplayResult,
    TerminationReason,
    check_determinism,
    compare,
    replay,
)
from replay_fixtures import (
    IDENTITY,
    SEED,
    fresh_handlers,
    hash_dependent_handlers,
    make_spec,
    reversed_handlers,
    run_replay,
    shared_state_handlers,
    variant_handlers,
    worker,
)

MATCH = ComparisonOutcome.MATCH
PARTIAL = ComparisonOutcome.PARTIAL_MATCH


def not_a_mapping() -> Any:
    return ["not", "a", "mapping"]


def test_the_same_scenario_state_and_seed_match_with_equal_digests() -> None:
    first, second = run_replay(), run_replay()
    comparison = compare(first, second)
    assert comparison.outcome is MATCH and comparison.accepted, comparison.detail
    assert first.event_digest == second.event_digest
    assert first.state_digest == second.state_digest
    state = dict(first.final_state.local_state)
    # Each arrival yields exactly one arrive, one start and one finish event.
    arrivals = state["arrivals"]
    assert isinstance(arrivals, int) and len(first.events) == 3 * arrivals > 0
    assert first.termination is TerminationReason.QUEUE_EMPTY
    assert dict(first.final_state.local_state)["scale"] == 1.5  # initial state kept


@settings(max_examples=25)
@given(st.integers(0, MAX_SEED))
def test_every_supported_seed_matches_its_own_replay(seed: int) -> None:
    assert check_determinism(make_spec(seed), fresh_handlers).outcome is MATCH


def test_handler_construction_order_does_not_change_the_result() -> None:
    assert (
        compare(run_replay(), replay(make_spec(), reversed_handlers)).outcome is MATCH
    )


def test_replays_are_isolated_from_each_other_and_from_caller_inputs() -> None:
    state: dict[str, Any] = {"scale": 1.5, "note": "initial"}
    spec = make_spec(initial_state=state)
    first = replay(spec, fresh_handlers)
    run_replay(seed=7)  # an unrelated run in between
    state["scale"] = 99.0  # the caller mutates its own mapping afterwards
    assert compare(first, replay(spec, fresh_handlers)).outcome is MATCH
    assert dict(spec.initial_state)["scale"] == 1.5
    assert dict(first.final_state.local_state)["scale"] == 1.5


@pytest.mark.parametrize(
    "factory", [hash_dependent_handlers, shared_state_handlers], ids=["hash", "shared"]
)
def test_in_process_state_shared_between_replays_is_detected_only_when_it_leaks(
    factory: Callable[[], dict[str, Any]],
) -> None:
    outcome = check_determinism(make_spec(), factory).outcome
    # A hash-dependent handler is stable inside one process; a shared counter is not.
    leaks = factory is shared_state_handlers
    assert outcome is (ComparisonOutcome.EVENT_MISMATCH if leaks else MATCH)


@pytest.mark.parametrize(
    "change",
    [
        {"seed": SEED + 1},
        {"initial_state": {"scale": 2.5, "note": "initial"}},
        {"initial_state": {"scale": 1.5}},
        {"max_events": 9_999},
        {"until": 4_999},
        {"horizon": 6_000},
        {"identity": dataclasses.replace(IDENTITY, source_id="test-source-1")},
        {"identity": dataclasses.replace(IDENTITY, handler_bundle_id="toy-handlers/2")},
    ],
)
def test_different_input_or_declared_labels_are_incompatible_not_a_mismatch(
    change: dict[str, Any],
) -> None:
    seed = change.pop("seed", SEED)
    other = replay(make_spec(seed, **change), fresh_handlers)
    assert compare(run_replay(), other).outcome is ComparisonOutcome.INCOMPATIBLE_INPUT


@pytest.mark.parametrize(
    ("field", "value"), [("numpy_version", "0.0.0"), ("rng_algorithm", "other")]
)
def test_results_from_another_runtime_are_compared_as_incompatible(
    field: str, value: str
) -> None:
    # Historical results may carry another runtime's real identity; compare them as
    # result fixtures. A new execution can never be labelled with one (next test).
    here = run_replay()
    other = dataclasses.replace(
        here, identity=dataclasses.replace(here.identity, **{field: value})
    )
    assert compare(here, other).outcome is ComparisonOutcome.INCOMPATIBLE_INPUT


@pytest.mark.parametrize("limit", ["until", "max_events"])
def test_results_that_declare_different_limits_are_incompatible(limit: str) -> None:
    here = run_replay()
    forged = dataclasses.replace(here, **{limit: getattr(here, limit) + 1})
    assert compare(here, forged).outcome is ComparisonOutcome.INCOMPATIBLE_INPUT


@pytest.mark.parametrize(
    "change", [{"numpy_version": "not-the-runtime"}, {"rng_algorithm": "fake"}]
)
def test_a_false_runtime_identity_runs_nothing(change: dict[str, str]) -> None:
    calls: list[int] = []

    def counting() -> dict[str, Any]:
        calls.append(1)
        return fresh_handlers()

    spec = make_spec(identity=dataclasses.replace(IDENTITY, **change))
    with pytest.raises(IncompatibleRuntimeError):
        replay(spec, counting)
    with pytest.raises(IncompatibleRuntimeError):
        check_determinism(spec, counting)
    assert calls == []


def test_an_input_that_cannot_be_canonicalized_runs_nothing() -> None:
    calls: list[int] = []

    def counting() -> dict[str, Any]:
        calls.append(1)
        return fresh_handlers()

    bad_config = dataclasses.replace(make_spec().config, scenario_id="bad\ud800")
    bad_state = make_spec(initial_state={"note": "bad\ud800"})
    for spec in (dataclasses.replace(make_spec(), config=bad_config), bad_state):
        with pytest.raises(CanonicalizationError):
            replay(spec, counting)
    assert calls == []


def test_equal_incomplete_runs_are_a_partial_match_and_never_accepted() -> None:
    for budget in (1, 25):
        spec = make_spec(max_events=budget)
        first, second = replay(spec, fresh_handlers), replay(spec, fresh_handlers)
        assert first.termination is TerminationReason.EVENT_LIMIT_REACHED
        assert len(first.events) == budget and first.final_state.pending
        comparison = compare(first, second)
        assert comparison.outcome is PARTIAL and not comparison.accepted
        assert "not accepted determinism" in comparison.detail
        assert not check_determinism(spec, fresh_handlers).accepted


def test_a_real_difference_in_an_incomplete_run_keeps_its_typed_mismatch() -> None:
    spec = make_spec(max_events=25)
    base = replay(spec, lambda: variant_handlers())
    other = replay(spec, lambda: variant_handlers(order="yx"))
    assert compare(base, other).outcome is ComparisonOutcome.EVENT_MISMATCH


def test_complete_horizon_bounded_and_empty_runs_are_accepted() -> None:
    complete = check_determinism(make_spec(), fresh_handlers)
    assert complete.outcome is MATCH and complete.accepted
    horizon = run_replay(until=40)
    assert horizon.termination is TerminationReason.HORIZON_REACHED
    assert check_determinism(make_spec(until=40), fresh_handlers).accepted
    spec = dataclasses.replace(
        make_spec(), config=dataclasses.replace(make_spec().config, initial_events=())
    )
    empty = replay(spec, fresh_handlers)
    assert empty.events == () and empty.termination is TerminationReason.QUEUE_EMPTY
    assert empty.event_digest == (
        "6c20ab2c9fc484e19932ce7bbe6928f7b40d16003f5431f4824e451f1d375c4d"
    )
    assert check_determinism(spec, fresh_handlers).accepted


def test_a_missing_run_is_an_error_not_a_match() -> None:
    missing: Any = None
    with pytest.raises(InvalidConfigurationError):
        compare(run_replay(), missing)


def test_a_failing_handler_raises_and_never_yields_a_result() -> None:
    def failing() -> dict[str, Any]:
        handlers = fresh_handlers()

        def finish(event: Any, ctx: Any) -> None:
            raise RuntimeError("boom 0x7f")

        handlers["finish"] = finish
        return handlers

    with pytest.raises(ReplayExecutionError) as caught:
        replay(make_spec(), failing)
    assert caught.value.kind == "finish"
    cause = caught.value.__cause__
    assert isinstance(cause, HandlerExecutionError)
    assert isinstance(cause.__cause__, RuntimeError)
    with pytest.raises(ReplayExecutionError):  # no retry: a second call fails again
        replay(make_spec(), failing)


@pytest.mark.parametrize(
    ("build", "error"),
    [
        (lambda: make_spec(max_events=0), InvalidConfigurationError),
        (lambda: make_spec(max_events=True), InvalidConfigurationError),
        (lambda: make_spec(until=5001), InvalidTimeError),
        (lambda: make_spec(until=True), InvalidTimeError),
        (lambda: make_spec(until=-1), InvalidTimeError),
        (
            lambda: make_spec(initial_state={"k": float("nan")}),
            InvalidConfigurationError,
        ),
        (lambda: make_spec(initial_state={"k": [1]}), InvalidConfigurationError),
        (
            lambda: make_spec(initial_state=(("k", 1), ("k", 2))),
            InvalidConfigurationError,
        ),
        (
            lambda: make_spec(identity=ReplayIdentity("", "b", "n", "r")),
            InvalidConfigurationError,
        ),
        (lambda: replay(make_spec(), not_a_mapping), InvalidConfigurationError),
    ],
)
def test_invalid_specs_fail_before_any_kernel_runs(
    build: Callable[[], Any], error: type[Exception]
) -> None:
    with pytest.raises(error):
        build()


def test_json_round_trip_is_exact_for_complete_and_incomplete_runs() -> None:
    for result in (run_replay(), run_replay(max_events=25), run_replay(until=40)):
        again = ReplayResult.from_json(result.to_json())
        assert again == result
        assert compare(result, again).outcome is (
            PARTIAL
            if result.termination is TerminationReason.EVENT_LIMIT_REACHED
            else MATCH
        )


def test_malformed_json_is_rejected_never_repaired() -> None:
    text = run_replay(max_events=25).to_json()
    data = json.loads(text)

    def tampered(**change: Any) -> str:
        return json.dumps({**data, **change})

    for bad in [
        text[: len(text) // 2],
        "",
        "[]",
        text.replace('"format"', '"formats"', 1),
        tampered(event_digest="0" * 64),
        tampered(state_digest="0" * 64),
        tampered(termination="NOT_A_REASON"),
        tampered(input_digest=7),
        tampered(identity={"source_id": "only"}),
        tampered(extra=1),
        text.replace("0x1.8000000000000p+0", "NaN", 1),
        text.replace('["i",', '["i",true,', 1),
    ]:
        with pytest.raises(CanonicalizationError):
            ReplayResult.from_json(bad)


FRESH_MATRIX = [
    (SEED, "plain", "0"),
    (SEED, "plain", "1"),
    (SEED, "plain", "424242"),
    (SEED, "plain", "random"),
    (SEED, "shuffled", "1"),
    (SEED, "shuffled", "random"),
    (7, "plain", "424242"),
    (7, "shuffled", "0"),
]


@pytest.mark.parametrize(("seed", "variant", "hash_seed"), FRESH_MATRIX)
def test_fresh_processes_replay_to_a_semantic_match(
    seed: int, variant: str, hash_seed: str
) -> None:
    remote = ReplayResult.from_json(worker(seed, variant, hash_seed))
    comparison = compare(replay(make_spec(seed), fresh_handlers), remote)
    assert comparison.outcome is MATCH and comparison.accepted, comparison.detail


def test_a_fresh_process_that_hit_its_event_budget_is_partial_not_accepted() -> None:
    remote = ReplayResult.from_json(worker(SEED, "partial", "1"))
    local = replay(make_spec(max_events=25), fresh_handlers)
    comparison = compare(local, remote)
    assert comparison.outcome is PARTIAL and not comparison.accepted


def test_injected_hash_dependence_is_detected_across_processes() -> None:
    zero = ReplayResult.from_json(worker(SEED, "hashdep", "0"))
    one = ReplayResult.from_json(worker(SEED, "hashdep", "1"))
    again = ReplayResult.from_json(worker(SEED, "hashdep", "1"))
    assert compare(zero, one).outcome is ComparisonOutcome.EVENT_MISMATCH
    assert compare(one, again).outcome is MATCH  # same hash seed: no false alarm


def test_worker_failures_are_explicit_never_a_match() -> None:
    with pytest.raises(AssertionError, match="worker exit 3"):
        worker(SEED, "crash", "0")
    with pytest.raises(subprocess.TimeoutExpired):
        worker(SEED, "hang", "0", timeout=3)
    with pytest.raises(CanonicalizationError):
        ReplayResult.from_json(worker(SEED, "truncated", "0"))
