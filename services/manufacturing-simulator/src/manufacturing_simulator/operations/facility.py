"""The operational model: reentrant routing, queues, failures, maintenance, rework.

``OperationalFacility`` is the real implementation of :class:`FacilityPort`. All change
happens inside kernel events, so a run is ordered, recorded and replayable, and every
random draw uses a named stream. Lot execution states and lot lifecycle follow the
vocabulary and edges Core publishes; the Simulator never invents legality, and an
equipment failure never moves material to another machine (docs/02).

Modelling constants (duration and defect uplift by health) are simulation assumptions
for causal structure, not claims about real machining physics.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from manufacturing_simulator.decision import DispatchIntake
from manufacturing_simulator.dispatch import DispatchGate
from manufacturing_simulator.events import EventSpec, ScheduledEvent, make_payload
from manufacturing_simulator.exposure import make_event
from manufacturing_simulator.kernel import EventHandler, ExecutionContext
from manufacturing_simulator.operations.config import (
    FacilityConfig,
    ReworkDirectiveSpec,
    RouteSpec,
    VisitSpec,
)
from manufacturing_simulator.operations.states import (
    EQUIPMENT_EDGES,
    EXECUTION_EDGES,
    LOT_EDGES,
    EquipmentState,
    ExecutionState,
    Health,
    LotLifecycle,
    check,
)
from manufacturing_simulator.ports import (
    DecisionProvider,
    LotView,
    OperationalPublisher,
)
from manufacturing_simulator.scenario import InitialEventSpec, KernelScenarioConfig

# Duration factor and extra defect probability (per mille) by health.
_FACTOR = {Health.HEALTHY: 1000, Health.DEGRADED: 1250, Health.CRITICAL: 1500}
_UPLIFT = {Health.HEALTHY: 0, Health.DEGRADED: 50, Health.CRITICAL: 150}

KINDS = (
    "lot.release",
    "equipment.idle",
    "equipment.arm",
    "equipment.fail",
    "equipment.repair_done",
    "equipment.qualified",
    "process.complete",
    "maintenance.start",
    "maintenance.done",
    "hold.place",
    "hold.release",
    "rework.inject",
    "lot.scrap",
    "dispatch.start",
)


@dataclass
class StepExecution:
    """One execution of one route visit; append-only history."""

    execution_id: str
    visit_id: str
    equipment_id: str
    started_at: int
    ended_at: int | None = None
    interruptions: int = 0


@dataclass
class _Lot:
    spec_id: str
    order_id: str
    priority: int
    due_at: int
    plan: list[tuple[str, VisitSpec]]
    index: int = 0
    lifecycle: LotLifecycle = LotLifecycle.CREATED
    execution: ExecutionState = ExecutionState.READY
    held: bool = False
    queued_at: int = 0
    rev: int = 1
    rework_count: int = 0
    executions: list[StepExecution] = field(default_factory=lambda: [])
    directives: list[str] = field(default_factory=lambda: [])


@dataclass
class _Equipment:
    equipment_id: str
    classes: tuple[str, ...]
    mtbf: int | None
    mttr: int
    qualification: int
    degrade_after: int | None
    critical_after: int | None
    state: EquipmentState = EquipmentState.AVAILABLE
    health: Health = Health.HEALTHY
    usage: int = 0
    token: int = 0
    arm_gen: int = 0
    svc: int = 0
    lot_id: str | None = None
    ends_at: int = 0
    remaining: int = 0
    pending_maintenance: int = 0


@dataclass(frozen=True)
class LotReport:
    lot_id: str
    order_id: str
    revision: str
    lifecycle: str
    execution_state: str
    held: bool
    current_visit: str | None
    rework_count: int
    directives: tuple[str, ...]
    executions: tuple[StepExecution, ...]


@dataclass(frozen=True)
class EquipmentReport:
    equipment_id: str
    state: str
    health: str
    usage: int
    lot_id: str | None


def _payload(event: ScheduledEvent) -> dict[str, str | int | float | bool | None]:
    return dict(event.payload)


def _text(values: Mapping[str, str | int | float | bool | None], key: str) -> str:
    value = values[key]
    assert isinstance(value, str)
    return value


def _number(values: Mapping[str, str | int | float | bool | None], key: str) -> int:
    value = values[key]
    assert isinstance(value, int) and not isinstance(value, bool)
    return value


class OperationalFacility:
    """Mutable facility state; implements :class:`FacilityPort`."""

    def __init__(
        self,
        config: FacilityConfig,
        *,
        provider: DecisionProvider | None = None,
        publisher: OperationalPublisher | None = None,
    ) -> None:
        self._config = config
        self._provider = provider
        self._publisher = publisher
        self._revision = 1
        self._routes: dict[str, RouteSpec] = {
            r.route_id: r for r in (*config.routes, *config.rework_routes)
        }
        self._equipment: dict[str, _Equipment] = {
            e.equipment_id: _Equipment(
                e.equipment_id,
                e.operation_classes,
                e.mtbf,
                e.mttr,
                e.qualification,
                e.degrade_after,
                e.critical_after,
            )
            for e in config.equipment
        }
        self._lots: dict[str, _Lot] = {}
        for lot in config.lots:
            route = self._routes[lot.route_id]
            self._lots[lot.lot_id] = _Lot(
                lot.lot_id,
                lot.order_id,
                lot.priority,
                lot.due_at,
                [(route.route_id, v) for v in route.visits],
            )
        self.gate = DispatchGate(config.world_id, self, publisher)

    # ------------------------------------------------------------------ FacilityPort

    @property
    def state_revision(self) -> str:
        return f"rev-{self._revision}"

    def lots(self) -> Sequence[LotView]:
        """Dispatchable waiting work: lots in production that are QUEUED for a visit."""
        views: list[LotView] = []
        for name in sorted(self._lots):
            lot = self._lots[name]
            if lot.lifecycle is not LotLifecycle.IN_PRODUCTION:
                continue
            if lot.execution is not ExecutionState.QUEUED:
                continue
            visit = lot.plan[lot.index][1]
            views.append(
                LotView(
                    lot_id=name,
                    revision=f"{name}-r{lot.rev}",
                    route_step=visit.visit_id,
                    held=lot.held,
                    priority=lot.priority,
                    due_at=lot.due_at,
                    ready_at=lot.queued_at,
                    eligible_machine_ids=tuple(sorted(visit.eligible_equipment)),
                )
            )
        return views

    def machine_ids(self) -> Sequence[str]:
        return tuple(sorted(self._equipment))

    def machine_available(self, machine_id: str) -> bool | None:
        equipment = self._equipment.get(machine_id)
        if equipment is None:
            return None
        return equipment.state is EquipmentState.AVAILABLE

    def start(self, intake: DispatchIntake, context: ExecutionContext) -> None:
        """QUEUED -> DISPATCHED -> PROCESSING on the chosen machine, inside a kernel event."""
        lot = self._lots[intake.lot_id]
        equipment = self._equipment[intake.machine_id]
        visit = lot.plan[lot.index][1]
        self._set_execution(lot, ExecutionState.DISPATCHED)
        self._set_execution(lot, ExecutionState.PROCESSING)
        self._set_equipment(equipment, EquipmentState.BUSY)
        equipment.lot_id = lot.spec_id
        number = len(lot.executions) + 1
        lot.executions.append(
            StepExecution(
                f"EXEC-{lot.spec_id}-{number}",
                visit.visit_id,
                equipment.equipment_id,
                context.now,
            )
        )
        duration = self._duration(context, visit.mean_duration, equipment.health)
        self._run_for(equipment, context, duration)

    # ------------------------------------------------------------------ construction

    def handlers(self) -> dict[str, EventHandler]:
        """Every event handler of the facility, including the dispatch gate's."""
        return {
            "lot.release": self._on_release,
            "equipment.idle": self._on_idle,
            "equipment.arm": self._on_arm,
            "equipment.fail": self._on_fail,
            "equipment.repair_done": self._on_repair_done,
            "equipment.qualified": self._on_qualified,
            "process.complete": self._on_complete,
            "maintenance.start": self._on_maintenance_start,
            "maintenance.done": self._on_maintenance_done,
            "hold.place": self._on_hold_place,
            "hold.release": self._on_hold_release,
            "rework.inject": self._on_rework,
            "lot.scrap": self._on_scrap,
            **self.gate.handlers(),
        }

    def lot_reports(self) -> tuple[LotReport, ...]:
        reports: list[LotReport] = []
        for name in sorted(self._lots):
            lot = self._lots[name]
            current = (
                lot.plan[lot.index][1].visit_id
                if lot.lifecycle is LotLifecycle.IN_PRODUCTION
                else None
            )
            reports.append(
                LotReport(
                    name,
                    lot.order_id,
                    f"{name}-r{lot.rev}",
                    lot.lifecycle.value,
                    lot.execution.value,
                    lot.held,
                    current,
                    lot.rework_count,
                    tuple(lot.directives),
                    tuple(lot.executions),
                )
            )
        return tuple(reports)

    def equipment_reports(self) -> tuple[EquipmentReport, ...]:
        return tuple(
            EquipmentReport(
                e.equipment_id, e.state.value, e.health.value, e.usage, e.lot_id
            )
            for _, e in sorted(self._equipment.items())
        )

    # ------------------------------------------------------------------ state changes

    def _touch(self, lot: _Lot | None = None) -> None:
        self._revision += 1
        if lot is not None:
            lot.rev += 1

    def _set_execution(self, lot: _Lot, target: ExecutionState) -> None:
        check(EXECUTION_EDGES, "EXECUTION", lot.execution, target)
        lot.execution = target
        self._touch(lot)

    def _set_lifecycle(self, lot: _Lot, target: LotLifecycle) -> None:
        check(LOT_EDGES, "LOT", lot.lifecycle, target)
        lot.lifecycle = target
        self._touch(lot)

    def _set_equipment(self, equipment: _Equipment, target: EquipmentState) -> None:
        check(EQUIPMENT_EDGES, "EQUIPMENT", equipment.state, target)
        equipment.state = target
        self._touch()

    def _emit(
        self,
        kind: str,
        context: ExecutionContext,
        correlation: str,
        **attributes: str | None,
    ) -> None:
        if self._publisher is None:
            return
        self._publisher.publish(
            make_event(
                kind, context.now, self._config.world_id, correlation, attributes
            )
        )

    # ------------------------------------------------------------------ queues

    def _enqueue(self, lot: _Lot, context: ExecutionContext) -> None:
        """READY -> QUEUED at the lot's current visit, then wake idle eligible machines."""
        self._set_execution(lot, ExecutionState.QUEUED)
        lot.queued_at = context.now
        visit = lot.plan[lot.index][1]
        self._emit(
            "LOT_QUEUED",
            context,
            lot.spec_id,
            lot_id=lot.spec_id,
            route_step=visit.visit_id,
        )
        for name in sorted(visit.eligible_equipment):
            self._wake(name, context)

    def _wake(self, equipment_id: str, context: ExecutionContext) -> None:
        if self._equipment[equipment_id].state is EquipmentState.AVAILABLE:
            context.schedule(
                EventSpec(
                    context.now,
                    "equipment.idle",
                    make_payload({"equipment": equipment_id}),
                )
            )

    def _on_idle(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        name = _text(_payload(event), "equipment")
        equipment = self._equipment[name]
        if (
            self._provider is None
            or equipment.state is not EquipmentState.AVAILABLE
            or name in self.gate.pending_machines
        ):
            return
        request = self.gate.request(f"REQ-{event.sequence}", name, context)
        decision = self._provider.decide(request)
        if decision is not None:
            self.gate.submit(decision.to_document(), context)

    # ------------------------------------------------------------------ lots

    def _on_release(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        lot = self._lots[_text(_payload(event), "lot")]
        self._set_lifecycle(lot, LotLifecycle.RELEASED)
        self._set_lifecycle(lot, LotLifecycle.IN_PRODUCTION)
        self._emit("LOT_RELEASED", context, lot.spec_id, lot_id=lot.spec_id)
        self._enqueue(lot, context)

    def _on_complete(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        values = _payload(event)
        lot = self._lots[_text(values, "lot")]
        equipment = self._equipment[_text(values, "equipment")]
        if (
            _number(values, "token") != equipment.token
            or equipment.state is not EquipmentState.BUSY
            or equipment.lot_id != lot.spec_id
        ):
            return  # a completion invalidated by a failure; the lot is paused elsewhere
        visit = lot.plan[lot.index][1]
        self._set_execution(lot, ExecutionState.STEP_COMPLETED)
        lot.executions[-1].ended_at = context.now
        self._set_equipment(equipment, EquipmentState.AVAILABLE)
        equipment.lot_id = None
        equipment.usage += 1
        self._update_health(equipment, context)
        self._emit(
            "PROCESS_COMPLETED",
            context,
            lot.spec_id,
            lot_id=lot.spec_id,
            machine_id=equipment.equipment_id,
            route_step=visit.visit_id,
        )
        if visit.inspect and self._defect(context, visit, equipment.health):
            self._emit(
                "INSPECTION_FAILED",
                context,
                lot.spec_id,
                lot_id=lot.spec_id,
                route_step=visit.visit_id,
            )
            self._emit(
                "REWORK_REQUESTED",
                context,
                lot.spec_id,
                lot_id=lot.spec_id,
                route_step=visit.visit_id,
            )
        lot.index += 1
        if lot.index < len(lot.plan):
            self._set_execution(lot, ExecutionState.READY)
            self._enqueue(lot, context)
        else:
            lot.index = len(lot.plan) - 1
            self._set_lifecycle(lot, LotLifecycle.COMPLETED)
            self._emit("LOT_COMPLETED", context, lot.spec_id, lot_id=lot.spec_id)
        self._after_free(equipment, context)

    def _defect(
        self, context: ExecutionContext, visit: VisitSpec, health: Health
    ) -> bool:
        threshold = visit.defect_per_mille + _UPLIFT.get(health, 0)
        return int(context.stream("quality").integers(0, 1000)) < threshold

    def _on_scrap(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        lot = self._lots[_text(_payload(event), "lot")]
        busy = lot.execution in {ExecutionState.DISPATCHED, ExecutionState.PROCESSING}
        if (
            lot.lifecycle not in {LotLifecycle.RELEASED, LotLifecycle.IN_PRODUCTION}
            or busy
        ):
            reason = "LOT_BUSY" if busy else "LOT_NOT_SCRAPPABLE"
            self._emit(
                "LOT_SCRAP_REJECTED",
                context,
                lot.spec_id,
                lot_id=lot.spec_id,
                reason_code=reason,
            )
            return
        self._set_lifecycle(lot, LotLifecycle.SCRAPPED)
        self._emit("LOT_SCRAPPED", context, lot.spec_id, lot_id=lot.spec_id)

    def _on_hold_place(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        lot = self._lots[_text(_payload(event), "lot")]
        lot.held = True
        self._touch(lot)
        self._emit("HOLD_PLACED", context, lot.spec_id, lot_id=lot.spec_id)

    def _on_hold_release(
        self, event: ScheduledEvent, context: ExecutionContext
    ) -> None:
        lot = self._lots[_text(_payload(event), "lot")]
        lot.held = False
        self._touch(lot)
        self._emit("HOLD_RELEASED", context, lot.spec_id, lot_id=lot.spec_id)
        if (
            lot.lifecycle is LotLifecycle.IN_PRODUCTION
            and lot.execution is ExecutionState.QUEUED
        ):
            for name in sorted(lot.plan[lot.index][1].eligible_equipment):
                self._wake(name, context)

    # ------------------------------------------------------------------ rework

    def _on_rework(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        wanted = _text(_payload(event), "directive")
        directive = next(d for d in self._config.reworks if d.directive_id == wanted)
        self.apply_rework(directive, context)

    def apply_rework(
        self, directive: ReworkDirectiveSpec, context: ExecutionContext
    ) -> str | None:
        """Execute an injected directive; returns the rejection code or ``None``.

        The Simulator never creates a directive: it only executes one that arrives the
        way Core would issue it. Scrapped or completed material is never reworked.
        """
        lot = self._lots[directive.lot_id]
        reason = self._rework_refusal(lot, directive)
        if reason is not None:
            self._emit(
                "REWORK_REJECTED",
                context,
                lot.spec_id,
                lot_id=lot.spec_id,
                directive_id=directive.directive_id,
                reason_code=reason,
            )
            return reason
        original = self._original_route(lot)
        ids = [v.visit_id for v in original.visits]
        rework = self._routes[directive.rework_route_id]
        tail = [
            (original.route_id, v)
            for v in original.visits[ids.index(directive.return_visit_id) :]
        ]
        lot.plan = [(rework.route_id, v) for v in rework.visits] + tail
        lot.index = 0
        lot.rework_count += 1
        lot.directives.append(directive.directive_id)
        self._touch(lot)
        self._emit(
            "REWORK_STARTED",
            context,
            lot.spec_id,
            lot_id=lot.spec_id,
            directive_id=directive.directive_id,
            route_step=lot.plan[0][1].visit_id,
        )
        for name in sorted(lot.plan[0][1].eligible_equipment):
            self._wake(name, context)
        return None

    def _original_route(self, lot: _Lot) -> RouteSpec:
        spec = next(item for item in self._config.lots if item.lot_id == lot.spec_id)
        return self._routes[spec.route_id]

    def _rework_refusal(self, lot: _Lot, directive: ReworkDirectiveSpec) -> str | None:
        if lot.lifecycle is LotLifecycle.SCRAPPED:
            return "LOT_SCRAPPED"
        if lot.lifecycle is LotLifecycle.COMPLETED:
            return "LOT_COMPLETED"
        if lot.lifecycle is not LotLifecycle.IN_PRODUCTION:
            return "LOT_NOT_IN_PRODUCTION"
        if directive.approval != "APPROVED":
            return "NOT_APPROVED"
        if lot.execution is not ExecutionState.QUEUED:
            return "NOT_BETWEEN_STEPS"
        if not any(e.visit_id == directive.origin_visit_id for e in lot.executions):
            return "NO_ORIGIN_EXECUTION"
        original = self._original_route(lot)
        if directive.return_visit_id not in {v.visit_id for v in original.visits}:
            return "BAD_RETURN_VISIT"
        if lot.rework_count >= self._config.max_rework:
            return "REWORK_LIMIT"
        return None

    # ------------------------------------------------------------------ equipment

    def _duration(self, context: ExecutionContext, mean: int, health: Health) -> int:
        low = max(1, mean * 3 // 4)
        high = max(low + 1, mean * 5 // 4 + 1)
        base = int(context.stream("processing").integers(low, high))
        return max(1, base * _FACTOR.get(health, 1500) // 1000)

    def _run_for(
        self, equipment: _Equipment, context: ExecutionContext, duration: int
    ) -> None:
        equipment.token += 1
        equipment.ends_at = context.now + duration
        assert equipment.lot_id is not None
        context.schedule(
            EventSpec(
                equipment.ends_at,
                "process.complete",
                make_payload(
                    {
                        "lot": equipment.lot_id,
                        "equipment": equipment.equipment_id,
                        "token": equipment.token,
                    }
                ),
            )
        )

    def _update_health(self, equipment: _Equipment, context: ExecutionContext) -> None:
        before = equipment.health
        if (
            equipment.critical_after is not None
            and equipment.usage >= equipment.critical_after
        ):
            equipment.health = Health.CRITICAL
        elif (
            equipment.degrade_after is not None
            and equipment.usage >= equipment.degrade_after
        ):
            equipment.health = Health.DEGRADED
        if equipment.health is not before:
            self._touch()
            self._emit(
                "EQUIPMENT_DEGRADED",
                context,
                equipment.equipment_id,
                machine_id=equipment.equipment_id,
                from_state=before.value,
                to_state=equipment.health.value,
            )

    def _on_arm(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        equipment = self._equipment[_text(_payload(event), "equipment")]
        if equipment.mtbf is None:
            return
        equipment.arm_gen += 1
        gap = 1 + int(context.stream("failure").exponential(equipment.mtbf))
        context.schedule(
            EventSpec(
                context.now + gap,
                "equipment.fail",
                make_payload(
                    {"equipment": equipment.equipment_id, "gen": equipment.arm_gen}
                ),
            )
        )

    def _on_fail(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        values = _payload(event)
        equipment = self._equipment[_text(values, "equipment")]
        generation = _number(values, "gen")
        if generation != -1 and generation != equipment.arm_gen:
            return  # a stale stochastic failure from before a repair
        if equipment.state in {EquipmentState.DOWN, EquipmentState.MAINTENANCE}:
            return
        if equipment.state is EquipmentState.BUSY:
            # Pause, never transfer: the lot stays PROCESSING on this machine.
            equipment.remaining = max(1, equipment.ends_at - context.now)
            equipment.token += 1
            lot = self._lots[equipment.lot_id or ""]
            lot.executions[-1].interruptions += 1
        self._set_equipment(equipment, EquipmentState.DOWN)
        equipment.health = Health.FAILED
        equipment.arm_gen += 1
        self._emit(
            "EQUIPMENT_FAILED",
            context,
            equipment.equipment_id,
            machine_id=equipment.equipment_id,
        )
        self._set_equipment(equipment, EquipmentState.MAINTENANCE)
        low = max(1, equipment.mttr * 3 // 4)
        high = max(low + 1, equipment.mttr * 5 // 4 + 1)
        duration = int(context.stream("repair").integers(low, high))
        self._schedule_service(equipment, context, "equipment.repair_done", duration)

    def _schedule_service(
        self,
        equipment: _Equipment,
        context: ExecutionContext,
        kind: str,
        duration: int,
    ) -> None:
        """Schedule a repair, qualification or maintenance completion for this epoch."""
        equipment.svc += 1
        context.schedule(
            EventSpec(
                context.now + duration,
                kind,
                make_payload(
                    {"equipment": equipment.equipment_id, "svc": equipment.svc}
                ),
            )
        )

    def _current(self, equipment: _Equipment, event: ScheduledEvent) -> bool:
        return _number(_payload(event), "svc") == equipment.svc

    def _on_repair_done(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        equipment = self._equipment[_text(_payload(event), "equipment")]
        if (
            equipment.state is not EquipmentState.MAINTENANCE
            or equipment.health is not Health.FAILED
            or not self._current(equipment, event)
        ):
            return
        equipment.health = Health.HEALTHY
        equipment.usage = 0
        if equipment.qualification > 0:
            self._set_equipment(equipment, EquipmentState.QUALIFICATION)
            self._schedule_service(
                equipment, context, "equipment.qualified", equipment.qualification
            )
            return
        self._back_in_service(equipment, context, "EQUIPMENT_REPAIRED")

    def _on_qualified(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        equipment = self._equipment[_text(_payload(event), "equipment")]
        if equipment.state is EquipmentState.QUALIFICATION and self._current(
            equipment, event
        ):
            self._back_in_service(equipment, context, "EQUIPMENT_REPAIRED")

    def _back_in_service(
        self, equipment: _Equipment, context: ExecutionContext, kind: str
    ) -> None:
        self._set_equipment(equipment, EquipmentState.AVAILABLE)
        self._emit(
            kind, context, equipment.equipment_id, machine_id=equipment.equipment_id
        )
        if equipment.mtbf is not None:
            context.schedule(
                EventSpec(
                    context.now,
                    "equipment.arm",
                    make_payload({"equipment": equipment.equipment_id}),
                )
            )
        if equipment.lot_id is not None:  # resume the paused lot on the same machine
            self._set_equipment(equipment, EquipmentState.BUSY)
            self._run_for(equipment, context, equipment.remaining)
        else:
            self._after_free(equipment, context)

    def _after_free(self, equipment: _Equipment, context: ExecutionContext) -> None:
        """An idle machine starts a deferred maintenance window or asks for work."""
        if equipment.state is not EquipmentState.AVAILABLE:
            return
        if equipment.pending_maintenance:
            duration, equipment.pending_maintenance = equipment.pending_maintenance, 0
            self._begin_maintenance(equipment, context, duration)
        else:
            self._wake(equipment.equipment_id, context)

    # ------------------------------------------------------------------ maintenance

    def _on_maintenance_start(
        self, event: ScheduledEvent, context: ExecutionContext
    ) -> None:
        values = _payload(event)
        equipment = self._equipment[_text(values, "equipment")]
        duration = _number(values, "duration")
        if equipment.state is EquipmentState.BUSY:
            equipment.pending_maintenance = duration
        elif equipment.state is EquipmentState.AVAILABLE:
            self._begin_maintenance(equipment, context, duration)
        else:
            self._emit(
                "MAINTENANCE_SKIPPED",
                context,
                equipment.equipment_id,
                machine_id=equipment.equipment_id,
                reason_code="EQUIPMENT_NOT_IDLE",
            )

    def _begin_maintenance(
        self, equipment: _Equipment, context: ExecutionContext, duration: int
    ) -> None:
        self._set_equipment(equipment, EquipmentState.MAINTENANCE)
        self._emit(
            "MAINTENANCE_STARTED",
            context,
            equipment.equipment_id,
            machine_id=equipment.equipment_id,
        )
        self._schedule_service(equipment, context, "maintenance.done", duration)

    def _on_maintenance_done(
        self, event: ScheduledEvent, context: ExecutionContext
    ) -> None:
        equipment = self._equipment[_text(_payload(event), "equipment")]
        if (
            equipment.state is not EquipmentState.MAINTENANCE
            or equipment.health is Health.FAILED
            or not self._current(equipment, event)
        ):
            return  # a repair, not a planned window, is running
        equipment.health = Health.HEALTHY
        equipment.usage = 0
        self._back_in_service(equipment, context, "MAINTENANCE_COMPLETED")


def scenario_config(
    config: FacilityConfig,
    *,
    seed: int,
    horizon: int,
    simulator_version: str = "opsem-1",
    scenario_id: str = "facility",
) -> KernelScenarioConfig:
    """The kernel scenario that releases the lots and injects every configured disruption."""
    events: list[InitialEventSpec] = []
    for lot in config.lots:
        events.append(
            InitialEventSpec(
                f"release-{lot.lot_id}",
                lot.release_at,
                "lot.release",
                make_payload({"lot": lot.lot_id}),
            )
        )
    for index, failure in enumerate(config.failures):
        events.append(
            InitialEventSpec(
                f"fail-{index}",
                failure.at,
                "equipment.fail",
                make_payload({"equipment": failure.equipment_id, "gen": -1}),
            )
        )
    for index, window in enumerate(config.maintenance):
        events.append(
            InitialEventSpec(
                f"maint-{index}",
                window.start_at,
                "maintenance.start",
                make_payload(
                    {"equipment": window.equipment_id, "duration": window.duration}
                ),
            )
        )
    for index, hold in enumerate(config.holds):
        events.append(
            InitialEventSpec(
                f"hold-{index}",
                hold.placed_at,
                "hold.place",
                make_payload({"lot": hold.lot_id}),
            )
        )
        if hold.released_at is not None:
            events.append(
                InitialEventSpec(
                    f"unhold-{index}",
                    hold.released_at,
                    "hold.release",
                    make_payload({"lot": hold.lot_id}),
                )
            )
    for directive in config.reworks:
        events.append(
            InitialEventSpec(
                f"rework-{directive.directive_id}",
                directive.at,
                "rework.inject",
                make_payload({"directive": directive.directive_id}),
            )
        )
    for index, scrap in enumerate(config.scraps):
        events.append(
            InitialEventSpec(
                f"scrap-{index}",
                scrap.at,
                "lot.scrap",
                make_payload({"lot": scrap.lot_id}),
            )
        )
    for equipment in config.equipment:
        if equipment.mtbf is not None:
            events.append(
                InitialEventSpec(
                    f"arm-{equipment.equipment_id}",
                    0,
                    "equipment.arm",
                    make_payload({"equipment": equipment.equipment_id}),
                )
            )
    return KernelScenarioConfig(
        scenario_id=scenario_id,
        scenario_version="1",
        seed=seed,
        simulator_version=simulator_version,
        horizon=horizon,
        initial_events=tuple(events),
    )
