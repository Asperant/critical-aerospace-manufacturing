"""Deterministic discrete-event kernel (ARCH-SIM-ENGINE).

The kernel owns one world: its future-event queue, clock, random streams and
local state. It has no Core client, database, broker, endpoint, wall clock or
Oracle export. Every record it exposes carries ``SIMULATION`` provenance.

Handler failure is fail-stop: the run becomes FAILED, the failure is recorded
with its event context, and the run cannot be resumed or extended. This includes
interruption by a ``BaseException`` (which is recorded and then re-raised). There is no
retry and no rollback claim for partial mutation made by a failed handler.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

import numpy as np

from manufacturing_simulator.errors import (
    DuplicateHandlerError,
    HandlerExecutionError,
    InvalidConfigurationError,
    InvalidTimeError,
    RunFailedError,
    SimulatorError,
    UnknownEventKindError,
)
from manufacturing_simulator.events import (
    EventSpec,
    Payload,
    PayloadValue,
    ScheduledEvent,
)
from manufacturing_simulator.rng import StreamName
from manufacturing_simulator.scenario import WorldState
from manufacturing_simulator.validation import require_int, require_text, require_time

PROVENANCE = "SIMULATION"
"""Every record and status view is simulator output, never real factory data."""


class StepOutcome(StrEnum):
    NO_EVENT = "NO_EVENT"
    EXECUTED = "EXECUTED"


class TerminationReason(StrEnum):
    """Why ``run`` stopped. Precedence: empty queue, then horizon, then budget."""

    QUEUE_EMPTY = "QUEUE_EMPTY"
    HORIZON_REACHED = "HORIZON_REACHED"
    EVENT_LIMIT_REACHED = "EVENT_LIMIT_REACHED"


class RunStatus(StrEnum):
    READY = "READY"
    RUNNING = "RUNNING"
    FAILED = "FAILED"


class RecordOutcome(StrEnum):
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class ExecutionRecord:
    """One consumed event, with scenario/run correlation and simulation provenance."""

    correlation_id: str
    provenance: str
    sequence: int
    time: int
    kind: str
    event_id: str | None
    payload: Payload
    outcome: RecordOutcome
    error: str | None = None


@dataclass(frozen=True)
class StepResult:
    outcome: StepOutcome
    record: ExecutionRecord | None = None


@dataclass(frozen=True)
class RunResult:
    termination: TerminationReason
    processed: int
    now: int
    queue_depth: int


@dataclass(frozen=True)
class KernelStatus:
    """Typed local status view; not an operational health or readiness claim."""

    correlation_id: str
    provenance: str
    status: RunStatus
    last_termination: TerminationReason | None
    processed_events: int
    queue_depth: int
    now: int


class ExecutionContext:
    """What a handler may touch: scheduling, local state and named random streams."""

    def __init__(self, kernel: Kernel) -> None:
        self._kernel = kernel

    @property
    def now(self) -> int:
        return self._kernel.world.clock.now

    @property
    def correlation_id(self) -> str:
        return self._kernel.world.correlation_id

    @property
    def state(self) -> dict[str, PayloadValue]:
        return self._kernel.world.state

    def stream(self, name: StreamName | str) -> np.random.Generator:
        return self._kernel.world.rng.stream(name)

    def schedule(self, spec: EventSpec) -> ScheduledEvent:
        return self._kernel.schedule(spec)


class EventHandler(Protocol):
    def __call__(self, event: ScheduledEvent, context: ExecutionContext, /) -> None: ...


class Kernel:
    """Single-threaded event loop over one :class:`WorldState`."""

    def __init__(
        self,
        world: WorldState,
        handlers: Mapping[str, EventHandler] | None = None,
    ) -> None:
        self._world = world
        self._handlers: dict[str, EventHandler] = {}
        self._records: list[ExecutionRecord] = []
        self._status = RunStatus.READY
        self._last_termination: TerminationReason | None = None
        self._processed = 0
        self._context = ExecutionContext(self)
        for kind, handler in (handlers or {}).items():
            self.register_handler(kind, handler)

    @property
    def world(self) -> WorldState:
        return self._world

    def register_handler(self, kind: str, handler: EventHandler) -> None:
        require_text(kind, "handler event kind")
        if not callable(handler):
            raise InvalidConfigurationError("handler must be callable")
        if kind in self._handlers:
            raise DuplicateHandlerError(f"handler already registered for {kind!r}")
        self._handlers[kind] = handler

    def schedule(self, spec: EventSpec) -> ScheduledEvent:
        """Enqueue ``spec``; rejected specs leave the world untouched."""
        self._require_not_failed()
        if spec.kind not in self._handlers:
            raise UnknownEventKindError(f"no handler registered for {spec.kind!r}")
        return self._world.queue.schedule(spec, now=self._world.clock.now)

    def step(self) -> StepResult:
        """Execute exactly one event, or report ``NO_EVENT`` on an empty queue."""
        self._require_not_failed()
        if self._status is RunStatus.RUNNING:
            raise SimulatorError("a handler cannot re-enter step() or run()")
        event = self._world.queue.peek()
        if event is None:
            return StepResult(StepOutcome.NO_EVENT)
        handler = self._handlers.get(event.kind)
        if handler is None:
            # Rejected before consuming: the event stays queued, the clock stays put.
            raise UnknownEventKindError(f"no handler registered for {event.kind!r}")
        self._world.queue.pop()
        self._world.clock.advance_to(event.time)
        self._status = RunStatus.RUNNING
        try:
            handler(event, self._context)
        except Exception as exc:
            self._fail(event, exc)
            raise HandlerExecutionError(
                f"handler for {event.kind!r} failed at sequence {event.sequence}, "
                f"time {event.time}: {exc!r}",
                sequence=event.sequence,
                time=event.time,
                kind=event.kind,
            ) from exc
        except BaseException as exc:
            # Interruption (KeyboardInterrupt, SystemExit, ...): the event is already
            # consumed, so record the terminal failure, then let it propagate.
            self._fail(event, exc)
            raise
        record = self._record(event, RecordOutcome.EXECUTED)
        self._records.append(record)
        self._processed += 1
        self._status = RunStatus.READY
        return StepResult(StepOutcome.EXECUTED, record)

    def run(self, until: int, max_events: int) -> RunResult:
        """Process events with ``time <= until``, at most ``max_events`` of them.

        Arguments are validated before any event is consumed. The clock only moves
        when an event is consumed, so it is never advanced to ``until`` itself, and
        events beyond the horizon stay queued.
        """
        self._require_not_failed()
        if self._status is RunStatus.RUNNING:
            raise SimulatorError("a handler cannot re-enter step() or run()")
        horizon = require_time(until, "until")
        if horizon < self._world.clock.now:
            raise InvalidTimeError(
                f"horizon {horizon} is before current time {self._world.clock.now}"
            )
        budget = require_int(
            max_events, "max_events", minimum=1, error=InvalidConfigurationError
        )
        processed = 0
        while True:
            next_event = self._world.queue.peek()
            if next_event is None:
                reason = TerminationReason.QUEUE_EMPTY
            elif next_event.time > horizon:
                reason = TerminationReason.HORIZON_REACHED
            elif processed >= budget:
                reason = TerminationReason.EVENT_LIMIT_REACHED
            else:
                self.step()
                processed += 1
                continue
            break
        self._last_termination = reason
        return RunResult(
            termination=reason,
            processed=processed,
            now=self._world.clock.now,
            queue_depth=len(self._world.queue),
        )

    def run_to_horizon(self, max_events: int) -> RunResult:
        """Run up to the scenario's configured horizon."""
        return self.run(self._world.config.horizon, max_events)

    def status(self) -> KernelStatus:
        return KernelStatus(
            correlation_id=self._world.correlation_id,
            provenance=PROVENANCE,
            status=self._status,
            last_termination=self._last_termination,
            processed_events=self._processed,
            queue_depth=len(self._world.queue),
            now=self._world.clock.now,
        )

    def records(self) -> tuple[ExecutionRecord, ...]:
        """Every consumed event, in execution order (a copy)."""
        return tuple(self._records)

    def _fail(self, event: ScheduledEvent, exc: BaseException) -> None:
        """Record the failed event and make the run terminal."""
        self._records.append(self._record(event, RecordOutcome.FAILED, error=repr(exc)))
        self._status = RunStatus.FAILED

    def _require_not_failed(self) -> None:
        if self._status is RunStatus.FAILED:
            raise RunFailedError("the run failed and cannot be resumed or extended")

    def _record(
        self, event: ScheduledEvent, outcome: RecordOutcome, error: str | None = None
    ) -> ExecutionRecord:
        return ExecutionRecord(
            correlation_id=self._world.correlation_id,
            provenance=PROVENANCE,
            sequence=event.sequence,
            time=event.time,
            kind=event.kind,
            event_id=event.event_id,
            payload=event.payload,
            outcome=outcome,
            error=error,
        )
