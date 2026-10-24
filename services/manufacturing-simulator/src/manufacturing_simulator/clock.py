"""Simulation-relative clock (ARCH-SIM-CLOCK).

Time is a local integer count of the declared unit since the run start. It is
not a wall-clock time and not a cross-service unit. Only the kernel advances it,
and only when an event is consumed.
"""

from __future__ import annotations

from enum import StrEnum

from manufacturing_simulator.errors import InvalidTimeError
from manufacturing_simulator.validation import require_time


class TimeUnit(StrEnum):
    """Declared unit of simulation time. Local to this kernel."""

    MICROSECOND = "us"


class SimulationClock:
    """Monotonic integer clock starting at zero."""

    def __init__(self, unit: TimeUnit = TimeUnit.MICROSECOND) -> None:
        self._unit = unit
        self._now = 0

    @property
    def now(self) -> int:
        return self._now

    @property
    def unit(self) -> TimeUnit:
        return self._unit

    def advance_to(self, time: int) -> None:
        """Move forward to ``time``; kernel use only. Never moves backwards."""
        require_time(time, "advance time")
        if time < self._now:
            raise InvalidTimeError(
                f"clock cannot move backwards from {self._now} to {time}"
            )
        self._now = time
