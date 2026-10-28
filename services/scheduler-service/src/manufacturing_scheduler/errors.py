"""Explicit failure types of the offline dispatch baselines.

Every rejected input raises one of these before any decision is produced.
"""

from __future__ import annotations


class SchedulerError(Exception):
    """Base class of every failure defined by this package."""


class InvalidTickError(SchedulerError):
    """A tick or duration is not an ``int`` (``bool`` included) in its range."""


class InvalidJobError(SchedulerError):
    """A dispatch job is malformed or internally inconsistent."""


class InvalidContextError(SchedulerError):
    """A dispatch context is malformed."""


class DuplicateJobIdError(InvalidContextError):
    """Two candidates of one context share a job ID."""


class IncompatibleTimeUnitError(SchedulerError):
    """A job and its context declare different tick units."""


class UnsupportedPolicyError(SchedulerError):
    """A policy or baseline ID is not one of the five registered rules."""


class InvalidInstanceConfigError(SchedulerError):
    """An offline instance configuration value is malformed or out of bounds."""


class InvalidSeedError(SchedulerError):
    """A generator seed is not an acceptable non-negative integer."""


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
