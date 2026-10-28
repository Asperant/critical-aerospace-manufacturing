"""Explicit, value-free failure types of the snapshot consumer and plan contract.

Messages carry a stable ``code`` and a JSON-Pointer-like ``path``, never a payload
value, so a rejected snapshot or plan cannot leak its content through an exception.
"""

from __future__ import annotations


class SchedulerError(Exception):
    """Base class of every failure defined by this package."""


class ContractError(SchedulerError):
    """A payload violates a consumed or produced contract."""

    def __init__(self, code: str, path: str = "") -> None:
        self.code = code
        self.path = path
        super().__init__(f"{code} at {path or '<root>'}")


class SnapshotError(ContractError):
    """A ``core.scheduling-snapshot.v1`` payload cannot be consumed."""


class PlanError(ContractError):
    """A ``scheduler.recovery-plan.v1`` payload or binding is invalid."""


class IncompleteInputError(SchedulerError):
    """The snapshot lacks inputs a full optimizer instance would need."""

    def __init__(self, missing: tuple[str, ...]) -> None:
        self.missing = missing
        super().__init__("snapshot is not a complete optimizer instance")
