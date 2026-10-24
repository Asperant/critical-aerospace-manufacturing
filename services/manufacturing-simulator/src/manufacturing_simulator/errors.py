"""Explicit failure types of the simulation kernel.

Every rejected input or illegal state transition raises one of these. Validation
failures are raised before any world state is mutated.
"""

from __future__ import annotations


class SimulatorError(Exception):
    """Base class of every kernel-defined failure."""


class InvalidConfigurationError(SimulatorError):
    """A scenario or kernel configuration value is malformed."""


class InvalidTimeError(SimulatorError):
    """A simulation time, horizon or delay is malformed or moves backwards."""


class PastSchedulingError(InvalidTimeError):
    """An event was scheduled before the current simulation time."""


class InvalidSeedError(SimulatorError):
    """A master seed is not an acceptable non-negative integer."""


class UnknownStreamError(SimulatorError):
    """A random stream name is not in the fixed stream registry."""


class UnknownEventKindError(SimulatorError):
    """An event kind has no registered handler."""


class DuplicateHandlerError(SimulatorError):
    """A second handler was registered for an already handled event kind."""


class RunFailedError(SimulatorError):
    """The run already failed; a failed run cannot be resumed or extended."""


class HandlerExecutionError(SimulatorError):
    """An event handler raised; the run is now FAILED and cannot be resumed."""

    def __init__(self, message: str, *, sequence: int, time: int, kind: str) -> None:
        super().__init__(message)
        self.sequence = sequence
        self.time = time
        self.kind = kind
