"""Test-only facility for the dispatch interface (kernel mechanics, not OPSEM).

The facility is a stand-in for the operational model of WP-SIM-003: a handful of lots
on a single route step and two machines. It carries no manufacturing semantics. Tests
that pass on it prove the dispatch interface, not the operational model.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from typing import Any

from manufacturing_simulator import (
    DecisionProvider,
    DispatchGate,
    DispatchIntake,
    EventSpec,
    ExecutionContext,
    InitialEventSpec,
    Kernel,
    KernelScenarioConfig,
    ListPublisher,
    LotView,
    ScenarioEngine,
    ScheduledEvent,
    make_payload,
)

STEP = "ROUGH-MILL"
WORLD = "world-1"
KINDS = ("machine_free", "finish", "dispatch.start")


def lot(
    lot_id: str,
    *,
    ready: int = 0,
    due: int = 100,
    priority: int = 1,
    machines: tuple[str, ...] = ("M1", "M2"),
    held: bool = False,
    revision: str | None = None,
    step: str = STEP,
) -> LotView:
    return LotView(
        lot_id=lot_id,
        revision=revision or f"{lot_id}-r1",
        route_step=step,
        held=held,
        priority=priority,
        due_at=due,
        ready_at=ready,
        eligible_machine_ids=machines,
    )


class FixtureFacility:
    """Mutable lots and machines with a revision counter."""

    def __init__(
        self, lots: Sequence[LotView], machines: Sequence[str] = ("M1", "M2")
    ) -> None:
        self._lots: dict[str, LotView] = {item.lot_id: item for item in lots}
        self._busy: dict[str, str | None] = {name: None for name in machines}
        self._revision = 1
        self.started: list[tuple[int, str, str]] = []
        self.finished: list[str] = []

    @property
    def state_revision(self) -> str:
        return f"rev-{self._revision}"

    def lots(self) -> Sequence[LotView]:
        return tuple(self._lots.values())

    def machine_ids(self) -> Sequence[str]:
        return tuple(self._busy)

    def machine_available(self, machine_id: str) -> bool | None:
        if machine_id not in self._busy:
            return None
        return self._busy[machine_id] is None

    def update_lot(self, lot_id: str, **changes: Any) -> None:
        self._lots[lot_id] = replace(self._lots[lot_id], **changes)
        self._revision += 1

    def start(self, intake: DispatchIntake, context: ExecutionContext) -> None:
        self._busy[intake.machine_id] = intake.lot_id
        self.started.append((context.now, intake.lot_id, intake.machine_id))
        del self._lots[intake.lot_id]
        self._revision += 1
        duration = int(context.stream("processing").integers(1, 20))
        context.schedule(
            EventSpec(
                context.now + duration,
                "finish",
                make_payload({"lot": intake.lot_id, "machine": intake.machine_id}),
            )
        )

    def finish(self, machine_id: str, lot_id: str) -> None:
        self._busy[machine_id] = None
        self.finished.append(lot_id)
        self._revision += 1


@dataclass
class Rig:
    """Handlers and objects of one decision-driven toy run."""

    facility: FixtureFacility
    gate: DispatchGate
    publisher: ListPublisher
    handlers: dict[str, Callable[[ScheduledEvent, ExecutionContext], None]]


def rig(lots: Sequence[LotView], provider: DecisionProvider | None) -> Rig:
    facility = FixtureFacility(lots)
    publisher = ListPublisher()
    gate = DispatchGate(WORLD, facility, publisher)

    def machine_free(event: ScheduledEvent, ctx: ExecutionContext) -> None:
        machine = dict(event.payload)["machine"]
        assert isinstance(machine, str)
        if provider is None or not facility.machine_available(machine):
            return
        request = gate.request(f"REQ-{event.sequence}", machine, ctx)
        decision = provider.decide(request)
        if decision is not None:
            gate.submit(decision.to_document(), ctx)

    def finish(event: ScheduledEvent, ctx: ExecutionContext) -> None:
        payload = dict(event.payload)
        machine, finished = payload["machine"], payload["lot"]
        assert isinstance(machine, str) and isinstance(finished, str)
        facility.finish(machine, finished)
        ctx.schedule(
            EventSpec(ctx.now, "machine_free", make_payload({"machine": machine}))
        )

    handlers = {"machine_free": machine_free, "finish": finish, **gate.handlers()}
    return Rig(facility, gate, publisher, handlers)


def run_config(
    seed: int, *, horizon: int = 500, free_machines: bool = True
) -> KernelScenarioConfig:
    return KernelScenarioConfig(
        scenario_id="dispatch-toy",
        scenario_version="1",
        seed=seed,
        simulator_version="dispatch-test-0",
        horizon=horizon,
        initial_events=tuple(
            InitialEventSpec(
                f"free-{name}", 0, "machine_free", make_payload({"machine": name})
            )
            for name in ("M1", "M2")
            if free_machines
        ),
    )


def intake_document(**overrides: Any) -> dict[str, Any]:
    """A valid BASELINE-style intake for ``lot("L1")`` on ``M1`` at time 0, revision 1."""
    document: dict[str, Any] = {
        "contract_version": "simulator.dispatch-intake.v1",
        "dispatch_id": "DSP-1",
        "world_id": WORLD,
        "request_id": "REQ-1",
        "lot_id": "L1",
        "lot_revision": "L1-r1",
        "route_step": STEP,
        "machine_id": "M1",
        "decision_time": {"value": 0, "unit": "us"},
        "rule": {"id": "EXT-RULE", "version": "1"},
        "schedule_version": None,
        "base_state_revision": "rev-1",
        "source": "EXTERNAL_DECIDER",
        "reason": "L1 is the earliest due lot",
    }
    document.update(overrides)
    return document


def build(rigged: Rig, seed: int = 1) -> Kernel:
    """A kernel over the rig's handlers; its initial events are not run by default."""
    world = ScenarioEngine(KINDS).initialize(run_config(seed, free_machines=False))
    return Kernel(world, rigged.handlers)
