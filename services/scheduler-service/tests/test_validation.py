"""Negative paths: every malformed input fails with a named error before any
decision is produced."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from manufacturing_scheduler import (
    DispatchContext,
    DispatchJob,
    DuplicateJobIdError,
    IncompatibleTimeUnitError,
    InvalidContextError,
    InvalidInstanceConfigError,
    InvalidJobError,
    InvalidSeedError,
    InvalidTickError,
    JobState,
    OfflineInstanceConfig,
    SchedulerError,
    generate,
)
from sch_fixtures import job

GOOD: dict[str, Any] = {
    "job_id": "J1",
    "queue_entry_tick": 0,
    "due_tick": 10,
    "operation_ticks": 2,
    "remaining_route_ticks": 5,
    "tick_unit": "tick",
}


def make_job(**changes: Any) -> DispatchJob:
    return DispatchJob(**{**GOOD, **changes})


@pytest.mark.parametrize(
    ("changes", "error"),
    [
        ({"job_id": ""}, InvalidJobError),
        ({"job_id": " J1"}, InvalidJobError),
        ({"job_id": 7}, InvalidJobError),
        ({"tick_unit": ""}, InvalidJobError),
        ({"state": "ELIGIBLE"}, InvalidJobError),
        ({"queue_entry_tick": True}, InvalidTickError),
        ({"due_tick": 1.5}, InvalidTickError),
        ({"due_tick": "10"}, InvalidTickError),
        ({"queue_entry_tick": -1}, InvalidTickError),
        ({"due_tick": -1}, InvalidTickError),
        ({"operation_ticks": 0}, InvalidTickError),
        ({"operation_ticks": True}, InvalidTickError),
        ({"remaining_route_ticks": 0}, InvalidTickError),
        ({"remaining_route_ticks": -3}, InvalidTickError),
        ({"remaining_route_ticks": 1}, InvalidJobError),  # below operation_ticks 2
        ({"state": JobState.COMPLETED}, InvalidJobError),  # remaining 5, not 0
        ({"state": JobState.COMPLETED, "remaining_route_ticks": -1}, InvalidTickError),
    ],
)
def test_malformed_jobs_are_rejected(
    changes: dict[str, Any], error: type[Exception]
) -> None:
    with pytest.raises(error):
        make_job(**changes)


def test_an_overdue_job_is_valid() -> None:
    assert make_job(due_tick=0, queue_entry_tick=9).due_tick == 0


def test_a_completed_job_is_representable_with_nothing_remaining() -> None:
    done = make_job(state=JobState.COMPLETED, remaining_route_ticks=0)
    assert not done.is_dispatchable(99)


def ctx(now: Any = 0, unit: Any = "tick", candidates: Any = ()) -> DispatchContext:
    return DispatchContext(now, unit, candidates)


CONTEXT_CASES: list[tuple[Callable[[], object], type[SchedulerError]]] = [
    (lambda: ctx(now=-1), InvalidTickError),
    (lambda: ctx(now=True), InvalidTickError),
    (lambda: ctx(unit=""), InvalidContextError),
    (lambda: ctx(candidates=[job("A", 0, 1, 1, 1)]), InvalidContextError),
    (lambda: ctx(candidates=("A",)), InvalidContextError),
    (
        lambda: ctx(candidates=(job("A", 0, 1, 1, 1), job("A", 1, 2, 1, 1))),
        DuplicateJobIdError,
    ),
    (
        lambda: ctx(unit="second", candidates=(job("A", 0, 1, 1, 1),)),
        IncompatibleTimeUnitError,
    ),
]


@pytest.mark.parametrize(("build", "error"), CONTEXT_CASES)
def test_malformed_contexts_are_rejected(
    build: Callable[[], object], error: type[SchedulerError]
) -> None:
    with pytest.raises(error):
        build()


@pytest.mark.parametrize(
    "changes",
    [
        {"job_count": 0},
        {"job_count": 501},
        {"job_count": True},
        {"job_count": 2.0},
        {"horizon_ticks": -1},
        {"horizon_ticks": 100_001},
        {"min_operation_ticks": 0},
        {"min_operation_ticks": 5, "max_operation_ticks": 4},
        {"max_operation_ticks": 10_001},
        {"max_extra_route_ticks": -1},
        {"min_due_offset_ticks": -1},
        {"min_due_offset_ticks": 9, "max_due_offset_ticks": 8},
        {"tick_unit": ""},
    ],
)
def test_invalid_generator_configuration_is_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(InvalidInstanceConfigError):
        OfflineInstanceConfig(**{"job_count": 5, "horizon_ticks": 10, **changes})


@pytest.mark.parametrize("seed", [-1, 2**63, True, 1.0, "1", None])
def test_invalid_seed_is_rejected(seed: Any) -> None:
    with pytest.raises(InvalidSeedError):
        generate(OfflineInstanceConfig(3, 10), seed)


def test_generate_rejects_a_non_config() -> None:
    not_a_config: Any = {"job_count": 3}
    with pytest.raises(InvalidInstanceConfigError):
        generate(not_a_config, 1)
