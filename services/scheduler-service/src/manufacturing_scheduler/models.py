"""Immutable offline dispatch inputs and decisions.

These are package-internal types, not a canonical transport contract. Time is a
local integer count of a declared ``tick_unit``; nothing reads a wall clock.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction

from manufacturing_scheduler.errors import (
    DuplicateJobIdError,
    IncompatibleTimeUnitError,
    InvalidContextError,
    InvalidJobError,
    InvalidTickError,
)
from manufacturing_scheduler.validation import require_int, require_text

# (policy primary key, queue-entry tick, job ID): the last two are the tie break.
RankingKey = tuple[int | Fraction, int, str]


class JobState(Enum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    COMPLETED = "COMPLETED"


class DecisionStatus(Enum):
    SELECTED = "SELECTED"
    NO_CANDIDATES = "NO_CANDIDATES"


@dataclass(frozen=True, slots=True)
class DispatchJob:
    """One job waiting for the next operation.

    ``queue_entry_tick`` is the tick at which the job was released into the queue.
    ``operation_ticks`` is the processing time of the next operation;
    ``remaining_route_ticks`` is the processing time of the whole remaining route,
    that operation included. ``state`` is supplied by the caller: eligibility is a
    fixture input here, not a production constraint check. A ``COMPLETED`` job has
    nothing remaining (``remaining_route_ticks == 0``) and is never dispatched.
    """

    job_id: str
    queue_entry_tick: int
    due_tick: int
    operation_ticks: int
    remaining_route_ticks: int
    tick_unit: str
    state: JobState = JobState.ELIGIBLE

    def __post_init__(self) -> None:
        require_text(self.job_id, "job_id", error=InvalidJobError)
        require_text(self.tick_unit, "tick_unit", error=InvalidJobError)
        require_int(
            self.queue_entry_tick,
            "queue_entry_tick",
            minimum=0,
            error=InvalidTickError,
        )
        require_int(self.due_tick, "due_tick", minimum=0, error=InvalidTickError)
        require_int(
            self.operation_ticks, "operation_ticks", minimum=1, error=InvalidTickError
        )
        if not isinstance(self.state, JobState):
            raise InvalidJobError(f"state must be a JobState, got {self.state!r}")
        if self.state is JobState.COMPLETED:
            require_int(
                self.remaining_route_ticks,
                "remaining_route_ticks",
                minimum=0,
                error=InvalidTickError,
            )
            if self.remaining_route_ticks != 0:
                raise InvalidJobError(
                    f"{self.job_id}: a COMPLETED job has no remaining route ticks"
                )
            return
        require_int(
            self.remaining_route_ticks,
            "remaining_route_ticks",
            minimum=1,
            error=InvalidTickError,
        )
        if self.remaining_route_ticks < self.operation_ticks:
            raise InvalidJobError(
                f"{self.job_id}: remaining_route_ticks {self.remaining_route_ticks} "
                f"is below operation_ticks {self.operation_ticks}"
            )

    def is_dispatchable(self, now: int) -> bool:
        """Released (not in the future) and explicitly eligible."""
        return self.state is JobState.ELIGIBLE and self.queue_entry_tick <= now


@dataclass(frozen=True, slots=True)
class DispatchContext:
    """The decision epoch ``now`` and the immutable candidate collection."""

    now: int
    tick_unit: str
    candidates: tuple[DispatchJob, ...]

    def __post_init__(self) -> None:
        require_int(self.now, "now", minimum=0, error=InvalidTickError)
        require_text(self.tick_unit, "tick_unit", error=InvalidContextError)
        if not isinstance(self.candidates, tuple):
            raise InvalidContextError(
                f"candidates must be a tuple, got {type(self.candidates).__name__}"
            )
        seen: set[str] = set()
        for job in self.candidates:
            if not isinstance(job, DispatchJob):
                raise InvalidContextError(
                    f"candidates must hold DispatchJob, got {type(job).__name__}"
                )
            if job.job_id in seen:
                raise DuplicateJobIdError(f"duplicate job_id {job.job_id!r}")
            seen.add(job.job_id)
            if job.tick_unit != self.tick_unit:
                raise IncompatibleTimeUnitError(
                    f"{job.job_id}: tick_unit {job.tick_unit!r} differs from "
                    f"the context's {self.tick_unit!r}"
                )


@dataclass(frozen=True, slots=True)
class RankedJob:
    job_id: str
    key: RankingKey


@dataclass(frozen=True, slots=True)
class DispatchDecision:
    """A ranking at one decision epoch. It selects; it never executes or mutates.

    ``ranking`` lists every dispatchable job, best first. ``NO_CANDIDATES`` is a
    normal outcome for an empty dispatchable queue.
    """

    status: DecisionStatus
    policy_id: str
    policy_name: str
    policy_version: str
    decision_tick: int
    selected_job_id: str | None
    ranking: tuple[RankedJob, ...]
