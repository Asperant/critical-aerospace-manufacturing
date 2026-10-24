"""Immutable events and the future-event queue (ARCH-SIM-CLOCK).

Ordering is ``(scheduled_time, insertion_sequence)``: equal-time events run in
FIFO insertion order, including events inserted by handlers at the current
time. Payloads are never compared.
"""

from __future__ import annotations

import heapq
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, cast

from manufacturing_simulator.errors import (
    InvalidConfigurationError,
    PastSchedulingError,
)
from manufacturing_simulator.validation import require_text, require_time

PayloadValue = str | int | float | bool | None
"""Scalar values a fixture payload may carry."""

Payload = tuple[tuple[str, PayloadValue], ...]
"""Immutable payload: ``(key, value)`` pairs sorted by key, keys unique."""


def make_payload(values: Mapping[str, PayloadValue] | None = None) -> Payload:
    """Validate and freeze a payload mapping into its canonical sorted form."""
    if values is None:
        return ()
    if not isinstance(values, Mapping):
        raise InvalidConfigurationError("payload must be a mapping")
    items: list[tuple[str, PayloadValue]] = []
    for key, value in values.items():
        require_text(key, "payload key")
        if isinstance(value, float) and not math.isfinite(value):
            raise InvalidConfigurationError(f"payload value for {key!r} is not finite")
        if value is not None and not isinstance(value, str | int | float | bool):
            raise InvalidConfigurationError(
                f"payload value for {key!r} has unsupported type "
                f"{type(value).__name__}"
            )
        items.append((key, value))
    return tuple(sorted(items, key=lambda item: item[0]))


def freeze_payload(payload: Payload | Mapping[str, PayloadValue]) -> Payload:
    """Canonicalise a payload given as a mapping or as ``(key, value)`` pairs."""
    raw: object = payload
    if isinstance(raw, Mapping):
        return make_payload(cast(Mapping[str, PayloadValue], raw))
    if not isinstance(raw, tuple | list):
        raise InvalidConfigurationError(
            "payload must be a mapping or a sequence of (key, value) pairs"
        )
    pairs: dict[str, PayloadValue] = {}
    for pair in cast(Sequence[object], raw):
        if not isinstance(pair, tuple | list) or len(cast(Sequence[object], pair)) != 2:
            raise InvalidConfigurationError("payload pairs must be (key, value)")
        key, value = cast(Sequence[Any], pair)
        if not isinstance(key, str):
            raise InvalidConfigurationError("payload keys must be str")
        if key in pairs:
            raise InvalidConfigurationError("payload keys must be unique")
        pairs[key] = value
    return make_payload(pairs)


@dataclass(frozen=True)
class EventSpec:
    """A request to schedule an event at an absolute simulation time."""

    time: int
    kind: str
    payload: Payload = ()
    event_id: str | None = None

    def __post_init__(self) -> None:
        require_time(self.time, "event time")
        require_text(self.kind, "event kind")
        if self.event_id is not None:
            require_text(self.event_id, "event_id")
        object.__setattr__(self, "payload", freeze_payload(self.payload))


@dataclass(frozen=True)
class ScheduledEvent:
    """An accepted event with its queue-assigned insertion sequence."""

    time: int
    sequence: int
    kind: str
    payload: Payload = ()
    event_id: str | None = None


class FutureEventQueue:
    """Binary-heap future-event list ordered by ``(time, sequence)``."""

    def __init__(self) -> None:
        self._heap: list[tuple[int, int, ScheduledEvent]] = []
        self._next_sequence = 0

    def __len__(self) -> int:
        return len(self._heap)

    @property
    def empty(self) -> bool:
        return not self._heap

    @property
    def scheduled_total(self) -> int:
        """Number of events ever accepted (the next insertion sequence)."""
        return self._next_sequence

    def schedule(self, spec: EventSpec, *, now: int) -> ScheduledEvent:
        """Accept ``spec``; events before ``now`` are rejected without mutation."""
        require_time(now, "now")
        if spec.time < now:
            raise PastSchedulingError(
                f"event time {spec.time} is before current time {now}"
            )
        event = ScheduledEvent(
            time=spec.time,
            sequence=self._next_sequence,
            kind=spec.kind,
            payload=spec.payload,
            event_id=spec.event_id,
        )
        self._next_sequence += 1
        heapq.heappush(self._heap, (event.time, event.sequence, event))
        return event

    def peek(self) -> ScheduledEvent | None:
        """Next event without removing it, or ``None`` when empty."""
        return self._heap[0][2] if self._heap else None

    def pop(self) -> ScheduledEvent | None:
        """Remove and return the next event, or ``None`` when empty."""
        return heapq.heappop(self._heap)[2] if self._heap else None

    def pending(self) -> tuple[ScheduledEvent, ...]:
        """All queued events in execution order (a copy; the queue is unchanged)."""
        return tuple(entry[2] for entry in sorted(self._heap))
