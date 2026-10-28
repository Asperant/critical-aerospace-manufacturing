"""Ports of the dispatch interface (WP-SIM-006).

The Simulator does not know how the facility is modelled: lots, machines, holds and
queues belong to the operational semantics (WP-SIM-003). The gate reads and starts
work only through :class:`FacilityPort`, so that model plugs in later without a
change here. Nothing in this module touches Core, a database or a network.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from manufacturing_simulator.decision import DecisionRequest, DispatchIntake
    from manufacturing_simulator.exposure import OperationalEvent
    from manufacturing_simulator.kernel import ExecutionContext


@dataclass(frozen=True)
class LotView:
    """What the interface may read about one lot. Operational facts only."""

    lot_id: str
    revision: str
    route_step: str
    held: bool
    priority: int
    due_at: int
    ready_at: int
    eligible_machine_ids: tuple[str, ...]


class FacilityPort(Protocol):
    """Read operational state and start an accepted dispatch."""

    @property
    def state_revision(self) -> str: ...

    def lots(self) -> Sequence[LotView]: ...

    def machine_ids(self) -> Sequence[str]: ...

    def machine_available(self, machine_id: str) -> bool | None:
        """``None`` for an unknown machine, otherwise whether it can start work now."""
        ...

    def start(self, intake: DispatchIntake, context: ExecutionContext) -> None:
        """Begin the dispatched operation. Called only from a kernel event.

        The context lets the facility schedule its own completion events.
        """
        ...


class DecisionProvider(Protocol):
    """A baseline or an external decider: one request in, at most one decision out."""

    @property
    def rule_id(self) -> str: ...

    @property
    def rule_version(self) -> str: ...

    def decide(self, request: DecisionRequest) -> DispatchIntake | None: ...


class OperationalPublisher(Protocol):
    """A typed local sink for operational events. Not the event spine."""

    def publish(self, event: OperationalEvent) -> None: ...
