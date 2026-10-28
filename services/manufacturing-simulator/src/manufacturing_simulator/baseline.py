"""Standalone baseline dispatch policies (WP-SIM-006).

Deterministic, total-order rules for running the Simulator without an external
Scheduler (docs/02, Scheduler Boundary). Integrated mode never falls back to them.
The research baselines SCH-B1..SCH-B5 stay in scheduler-service; these are only the
minimal rules a standalone world needs. No clock, no randomness, no I/O.
"""

from __future__ import annotations

from collections.abc import Callable

from manufacturing_simulator.decision import (
    Candidate,
    DecisionRequest,
    DispatchIntake,
    IntakeSource,
)

Key = Callable[[Candidate], tuple[int | str, ...]]


class BaselinePolicy:
    """Pick the best candidate for the machine by a fixed key; ties end at lot id."""

    def __init__(self, rule_id: str, rule_version: str, key: Key, reason: str) -> None:
        self._rule_id = rule_id
        self._rule_version = rule_version
        self._key = key
        self._reason = reason

    @property
    def rule_id(self) -> str:
        return self._rule_id

    @property
    def rule_version(self) -> str:
        return self._rule_version

    def decide(self, request: DecisionRequest) -> DispatchIntake | None:
        usable = [
            c
            for c in request.candidates
            if request.machine_id in c.eligible_machine_ids
        ]
        if not usable:
            return None
        best = min(usable, key=self._key)
        return DispatchIntake(
            dispatch_id=f"DSP-{request.request_id}",
            world_id=request.world_id,
            request_id=request.request_id,
            lot_id=best.lot_id,
            lot_revision=best.lot_revision,
            route_step=best.route_step,
            machine_id=request.machine_id,
            decision_time=request.simulation_time,
            rule_id=self._rule_id,
            rule_version=self._rule_version,
            schedule_version=None,
            base_state_revision=request.state_revision,
            source=IntakeSource.BASELINE,
            reason=f"{self._reason}; {len(usable)} eligible candidate(s)",
        )


def fifo() -> BaselinePolicy:
    """Earliest ready time first; ties by lot id."""
    return BaselinePolicy(
        "SIM-FIFO",
        "1",
        lambda c: (c.ready_at, c.lot_id),
        "FIFO: earliest ready_at, ties by lot_id",
    )


def edd() -> BaselinePolicy:
    """Earliest due date first; ties by ready time, then lot id."""
    return BaselinePolicy(
        "SIM-EDD",
        "1",
        lambda c: (c.due_at, c.ready_at, c.lot_id),
        "EDD: earliest due_at, ties by ready_at then lot_id",
    )


def static_priority() -> BaselinePolicy:
    """Highest priority value first; ties by ready time, then lot id."""
    return BaselinePolicy(
        "SIM-PRIORITY",
        "1",
        lambda c: (-c.priority, c.ready_at, c.lot_id),
        "PRIORITY: highest priority, ties by ready_at then lot_id",
    )
