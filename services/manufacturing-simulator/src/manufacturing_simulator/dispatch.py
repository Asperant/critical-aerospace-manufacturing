"""Dispatch gate: accept, revalidate and execute external decisions (FR-SIM-013).

A decision is a proposal. The gate re-checks it against the current simulated state
(SCH-INV-02) when it arrives and again when it executes, and it executes only by
scheduling a kernel event, so every dispatch is ordered, recorded and replayable.
The gate holds no Core client, database or network handle and mutates no canonical
state: it can only ask the :class:`FacilityPort` to start work inside the simulation.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from manufacturing_simulator.decision import (
    DecisionContractError,
    DecisionRequest,
    DispatchIntake,
    DispatchOutcome,
    IntakeSource,
    OutcomeStatus,
    RejectReason,
    decode_intake,
)
from manufacturing_simulator.events import EventSpec, ScheduledEvent, make_payload
from manufacturing_simulator.exposure import build_request, make_event
from manufacturing_simulator.kernel import EventHandler, ExecutionContext
from manufacturing_simulator.ports import FacilityPort, LotView, OperationalPublisher

START_KIND = "dispatch.start"
_CORE_EVENT_TYPE = "production.lot-dispatch-authorized"
_CORE_KEYS = frozenset(
    {
        "event_type",
        "schema_version",
        "aggregate_type",
        "aggregate_id",
        "aggregate_version",
        "lot_id",
        "lot_revision",
        "dispatch_id",
    }
)


def _core_text(value: object) -> str:
    if not isinstance(value, str) or not value or any(c.isspace() for c in value):
        raise DecisionContractError(RejectReason.CORE_AUTHORIZATION_INVALID)
    return value


class DispatchGate:
    """Single entry point for dispatch decisions of one simulated world."""

    def __init__(
        self,
        world_id: str,
        facility: FacilityPort,
        publisher: OperationalPublisher | None = None,
    ) -> None:
        self._world_id = world_id
        self._facility = facility
        self._publisher = publisher
        self._seen: dict[str, tuple[DispatchIntake, DispatchOutcome]] = {}
        self._pending_lots: set[str] = set()
        self._pending_machines: set[str] = set()
        self._authorized: dict[str, tuple[str, str]] = {}
        self._executions: list[tuple[str, RejectReason | None]] = []

    def handlers(self) -> dict[str, EventHandler]:
        """Event handlers to merge into the kernel's handler bundle."""
        return {START_KIND: self._on_start}

    @property
    def executions(self) -> tuple[tuple[str, RejectReason | None], ...]:
        """``(dispatch_id, None)`` for a started dispatch, else its rejection reason."""
        return tuple(self._executions)

    def authorize(self, core_event: Mapping[str, Any]) -> None:
        """Record a Core ``LotDispatchAuthorized`` fact for a later CORE_AUTHORIZED intake."""
        if not isinstance(core_event, Mapping) or set(core_event) != _CORE_KEYS:
            raise DecisionContractError(RejectReason.CORE_AUTHORIZATION_INVALID)
        version = core_event["aggregate_version"]
        if (
            core_event["event_type"] != _CORE_EVENT_TYPE
            or core_event["aggregate_type"] != "Lot"
            or type(core_event["schema_version"]) is not int
            or core_event["schema_version"] != 1
            or type(version) is not int
            or version < 1
        ):
            raise DecisionContractError(RejectReason.CORE_AUTHORIZATION_INVALID)
        _core_text(core_event["aggregate_id"])
        entry = (
            _core_text(core_event["lot_id"]),
            _core_text(core_event["lot_revision"]),
        )
        dispatch_id = _core_text(core_event["dispatch_id"])
        if self._authorized.setdefault(dispatch_id, entry) != entry:
            raise DecisionContractError(RejectReason.CORE_AUTHORIZATION_INVALID)

    def request(
        self, request_id: str, machine_id: str, context: ExecutionContext
    ) -> DecisionRequest:
        """The decision request for ``machine_id`` now, without lots already pending."""
        return build_request(
            self._world_id,
            request_id,
            self._facility,
            context.now,
            machine_id,
            exclude=self._pending_lots,
        )

    def submit(
        self, source: str | Mapping[str, Any], context: ExecutionContext
    ) -> DispatchOutcome:
        """Decide one intake at the context's simulation time.

        Never raises for a bad document; it answers REJECTED.
        """
        now = context.now
        try:
            intake = decode_intake(source)
        except DecisionContractError as error:
            return self._reject(None, error.code, None, now)
        known = self._seen.get(intake.dispatch_id)
        if known is not None:
            if known[0] == intake:
                return known[1]
            return self._reject(intake, RejectReason.DUPLICATE_CONFLICT, None, now)
        reason = self._admission_failure(intake, now)
        if reason is not None:
            outcome = self._reject(intake, reason, intake.dispatch_id, now)
            self._seen[intake.dispatch_id] = (intake, outcome)
            return outcome
        context.schedule(
            EventSpec(
                time=now,
                kind=START_KIND,
                payload=make_payload({"dispatch_id": intake.dispatch_id}),
                event_id=intake.dispatch_id,
            )
        )
        outcome = self._outcome(intake.dispatch_id, OutcomeStatus.ACCEPTED, None, now)
        self._seen[intake.dispatch_id] = (intake, outcome)
        self._pending_lots.add(intake.lot_id)
        self._pending_machines.add(intake.machine_id)
        self._emit("DISPATCH_ACCEPTED", intake, None, now)
        return outcome

    def _admission_failure(
        self, intake: DispatchIntake, now: int
    ) -> RejectReason | None:
        if intake.world_id != self._world_id:
            return RejectReason.WRONG_WORLD
        if intake.base_state_revision != self._facility.state_revision:
            return RejectReason.STALE_REVISION
        if intake.decision_time != now:
            return RejectReason.DECISION_TIME_MISMATCH
        if intake.lot_id in self._pending_lots:
            return RejectReason.LOT_ALREADY_DISPATCHED
        if intake.machine_id in self._pending_machines:
            return RejectReason.MACHINE_UNAVAILABLE
        reason = self._state_failure(intake)
        if reason is not None:
            return reason
        if intake.source is IntakeSource.CORE_AUTHORIZED:
            granted = self._authorized.get(intake.dispatch_id)
            if granted is None:
                return RejectReason.CORE_AUTHORIZATION_MISSING
            if granted != (intake.lot_id, intake.lot_revision):
                return RejectReason.CORE_AUTHORIZATION_INVALID
        return None

    def _state_failure(self, intake: DispatchIntake) -> RejectReason | None:
        lot: LotView | None = next(
            (item for item in self._facility.lots() if item.lot_id == intake.lot_id),
            None,
        )
        if lot is None:
            return RejectReason.UNKNOWN_LOT
        if lot.revision != intake.lot_revision:
            return RejectReason.LOT_REVISION_MISMATCH
        if lot.held:
            return RejectReason.LOT_HELD
        if lot.route_step != intake.route_step:
            return RejectReason.WRONG_ROUTE_STEP
        available = self._facility.machine_available(intake.machine_id)
        if available is None:
            return RejectReason.UNKNOWN_MACHINE
        if intake.machine_id not in lot.eligible_machine_ids:
            return RejectReason.MACHINE_INELIGIBLE
        if not available:
            return RejectReason.MACHINE_UNAVAILABLE
        return None

    def _on_start(self, event: ScheduledEvent, context: ExecutionContext) -> None:
        now = context.now
        payload = dict(event.payload)
        dispatch_id = payload.get("dispatch_id")
        known = self._seen.get(dispatch_id) if isinstance(dispatch_id, str) else None
        if known is None or known[1].status is not OutcomeStatus.ACCEPTED:
            raise DecisionContractError(RejectReason.UNKNOWN_LOT)
        intake = known[0]
        self._pending_lots.discard(intake.lot_id)
        self._pending_machines.discard(intake.machine_id)
        reason = self._state_failure(intake)
        if reason is not None:
            self._executions.append((intake.dispatch_id, reason))
            self._emit("DISPATCH_START_REJECTED", intake, reason, now)
            return
        self._facility.start(intake, context)
        self._executions.append((intake.dispatch_id, None))
        self._emit("DISPATCH_STARTED", intake, None, now)

    def _outcome(
        self,
        dispatch_id: str | None,
        status: OutcomeStatus,
        reason: RejectReason | None,
        now: int,
    ) -> DispatchOutcome:
        return DispatchOutcome(
            dispatch_id=dispatch_id,
            world_id=self._world_id,
            status=status,
            reason_code=reason,
            simulation_time=now,
            state_revision=self._facility.state_revision,
        )

    def _reject(
        self,
        intake: DispatchIntake | None,
        reason: RejectReason,
        dispatch_id: str | None,
        now: int,
    ) -> DispatchOutcome:
        outcome = self._outcome(dispatch_id, OutcomeStatus.REJECTED, reason, now)
        if intake is not None:
            self._emit("DISPATCH_REJECTED", intake, reason, now)
        else:
            self._publish(
                "DISPATCH_REJECTED", "unparsed", {"reason_code": reason.value}, now
            )
        return outcome

    def _emit(
        self,
        kind: str,
        intake: DispatchIntake,
        reason: RejectReason | None,
        now: int,
    ) -> None:
        self._publish(
            kind,
            intake.dispatch_id,
            {
                "dispatch_id": intake.dispatch_id,
                "request_id": intake.request_id,
                "lot_id": intake.lot_id,
                "machine_id": intake.machine_id,
                "route_step": intake.route_step,
                "rule_id": intake.rule_id,
                "reason_code": None if reason is None else reason.value,
            },
            now,
        )

    def _publish(
        self,
        kind: str,
        correlation_id: str,
        attributes: Mapping[str, str | None],
        now: int,
    ) -> None:
        if self._publisher is None:
            return
        self._publisher.publish(
            make_event(kind, now, self._world_id, correlation_id, attributes)
        )
