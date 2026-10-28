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
