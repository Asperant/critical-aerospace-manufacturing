"""Decision request, dispatch intake and outcome messages (WP-SIM-006, FR-SIM-013).

Strict, value-free decoding: a document is exactly what the contract spells or it is
rejected with a closed reason code. Nothing here reads a clock, trims, case-folds or
coerces a value, and no error message repeats input.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from manufacturing_simulator.errors import SimulatorError
from manufacturing_simulator.isolation import find_evaluator_field

REQUEST_CONTRACT = "simulator.decision-request.v1"
INTAKE_CONTRACT = "simulator.dispatch-intake.v1"
PROVENANCE = "SIMULATION"
TIME_UNIT = "us"
MAX_SAFE = 9007199254740991
_IDENT = re.compile(r"\S+")


class RejectReason(StrEnum):
    """Closed set of reasons a dispatch is not accepted or not started."""

    MALFORMED = "MALFORMED"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    ORACLE_FIELD_REJECTED = "ORACLE_FIELD_REJECTED"
    WRONG_WORLD = "WRONG_WORLD"
    DUPLICATE_CONFLICT = "DUPLICATE_CONFLICT"
    STALE_REVISION = "STALE_REVISION"
    DECISION_TIME_MISMATCH = "DECISION_TIME_MISMATCH"
    UNKNOWN_LOT = "UNKNOWN_LOT"
    LOT_REVISION_MISMATCH = "LOT_REVISION_MISMATCH"
    LOT_HELD = "LOT_HELD"
    LOT_ALREADY_DISPATCHED = "LOT_ALREADY_DISPATCHED"
    WRONG_ROUTE_STEP = "WRONG_ROUTE_STEP"
    UNKNOWN_MACHINE = "UNKNOWN_MACHINE"
    MACHINE_INELIGIBLE = "MACHINE_INELIGIBLE"
    MACHINE_UNAVAILABLE = "MACHINE_UNAVAILABLE"
    CORE_AUTHORIZATION_MISSING = "CORE_AUTHORIZATION_MISSING"
    CORE_AUTHORIZATION_INVALID = "CORE_AUTHORIZATION_INVALID"


class IntakeSource(StrEnum):
    BASELINE = "BASELINE"
    EXTERNAL_DECIDER = "EXTERNAL_DECIDER"
    CORE_AUTHORIZED = "CORE_AUTHORIZED"


class OutcomeStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class DecisionContractError(SimulatorError):
    """A document does not satisfy the contract. Carries a code and a path, no values."""

    def __init__(self, code: RejectReason, path: str = "") -> None:
        super().__init__(f"{code.value} at {path or '/'}")
        self.code = code
        self.path = path


def _fail(
    path: str, code: RejectReason = RejectReason.MALFORMED
) -> DecisionContractError:
    return DecisionContractError(code, path)


def _obj(value: Any, path: str, keys: Collection[str]) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise _fail(path)
    fields: Mapping[Any, Any] = value
    if any(not isinstance(key, str) for key in fields) or set(fields) != set(keys):
        raise _fail(path)
    return fields


def _ident(value: Any, path: str) -> str:
    if not isinstance(value, str) or _IDENT.fullmatch(value) is None:
        raise _fail(path)
    return value


def _text(value: Any, path: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise _fail(path)
    return value


def _int(value: Any, path: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_SAFE:
        raise _fail(path)
    return value


def _const(value: Any, path: str, expected: str) -> str:
    if value != expected:
        raise _fail(path, RejectReason.UNSUPPORTED_VERSION)
    return expected


def _time(value: Any, path: str) -> int:
    fields = _obj(value, path, ("value", "unit"))
    if fields["unit"] != TIME_UNIT:
        raise _fail(f"{path}/unit")
    return _int(fields["value"], f"{path}/value")


def _idents(value: Any, path: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise _fail(path)
    items: list[Any] = value
    result = tuple(_ident(item, f"{path}/{index}") for index, item in enumerate(items))
    if len(set(result)) != len(result):
        raise _fail(path)
    return result


def _time_document(value: int) -> dict[str, Any]:
    return {"value": value, "unit": TIME_UNIT}


def _reject_duplicate(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def _reject_constant(_: str) -> Any:
    raise ValueError("non-finite JSON number")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("non-finite JSON number")
    return value


def loads_document(text: str) -> Any:
    """Decode JSON text, rejecting duplicate fields, NaN, Infinity and overflow."""
    try:
        return json.loads(
            text,
            object_pairs_hook=_reject_duplicate,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
    except ValueError:
        raise _fail("") from None


def _as_document(source: str | Mapping[str, Any]) -> Mapping[str, Any]:
    document: Any = loads_document(source) if isinstance(source, str) else source
    hit = find_evaluator_field(document)
    if hit is not None:
        raise _fail(hit, RejectReason.ORACLE_FIELD_REJECTED)
    return _obj_any(document)


def _obj_any(document: Any) -> Mapping[str, Any]:
    if not isinstance(document, Mapping):
        raise _fail("")
    result: Mapping[str, Any] = document
    return result


@dataclass(frozen=True)
class Candidate:
    """One lot offered to a decider at a decision point."""

    lot_id: str
    lot_revision: str
    route_step: str
    priority: int
    due_at: int
    ready_at: int
    eligible_machine_ids: tuple[str, ...]

    def to_document(self) -> dict[str, Any]:
        return {
            "lot_id": self.lot_id,
            "lot_revision": self.lot_revision,
            "route_step": self.route_step,
            "priority": self.priority,
            "due_at": self.due_at,
            "ready_at": self.ready_at,
            "eligible_machine_ids": list(self.eligible_machine_ids),
        }


_CANDIDATE_KEYS = (
    "lot_id",
    "lot_revision",
    "route_step",
    "priority",
    "due_at",
    "ready_at",
    "eligible_machine_ids",
)
_REQUEST_KEYS = (
    "contract_version",
    "world_id",
    "request_id",
    "state_revision",
    "simulation_time",
    "provenance",
    "decision_point",
    "candidates",
)


@dataclass(frozen=True)
class DecisionRequest:
    """The operational state a decider is shown when a machine becomes available."""

    world_id: str
    request_id: str
    state_revision: str
    simulation_time: int
    machine_id: str
    candidates: tuple[Candidate, ...]

    def to_document(self) -> dict[str, Any]:
        return {
            "contract_version": REQUEST_CONTRACT,
            "world_id": self.world_id,
            "request_id": self.request_id,
            "state_revision": self.state_revision,
            "simulation_time": _time_document(self.simulation_time),
            "provenance": PROVENANCE,
            "decision_point": {
                "kind": "MACHINE_AVAILABLE",
                "machine_id": self.machine_id,
            },
            "candidates": [c.to_document() for c in self.candidates],
        }


def decode_request(source: str | Mapping[str, Any]) -> DecisionRequest:
    """Decode a decision request; the inverse of :meth:`DecisionRequest.to_document`."""
    fields = _obj(_as_document(source), "", _REQUEST_KEYS)
    _const(fields["contract_version"], "/contract_version", REQUEST_CONTRACT)
    _const(fields["provenance"], "/provenance", PROVENANCE)
    point = _obj(fields["decision_point"], "/decision_point", ("kind", "machine_id"))
    if point["kind"] != "MACHINE_AVAILABLE":
        raise _fail("/decision_point/kind")
    raw = fields["candidates"]
    if not isinstance(raw, list):
        raise _fail("/candidates")
    items: list[Any] = raw
    candidates: list[Candidate] = []
    for index, item in enumerate(items):
        path = f"/candidates/{index}"
        data = _obj(item, path, _CANDIDATE_KEYS)
        candidates.append(
            Candidate(
                lot_id=_ident(data["lot_id"], f"{path}/lot_id"),
                lot_revision=_ident(data["lot_revision"], f"{path}/lot_revision"),
                route_step=_ident(data["route_step"], f"{path}/route_step"),
                priority=_int(data["priority"], f"{path}/priority"),
                due_at=_int(data["due_at"], f"{path}/due_at"),
                ready_at=_int(data["ready_at"], f"{path}/ready_at"),
                eligible_machine_ids=_idents(
                    data["eligible_machine_ids"], f"{path}/eligible_machine_ids"
                ),
            )
        )
    if len({c.lot_id for c in candidates}) != len(candidates):
        raise _fail("/candidates")
    return DecisionRequest(
        world_id=_ident(fields["world_id"], "/world_id"),
        request_id=_ident(fields["request_id"], "/request_id"),
        state_revision=_ident(fields["state_revision"], "/state_revision"),
        simulation_time=_time(fields["simulation_time"], "/simulation_time"),
        machine_id=_ident(point["machine_id"], "/decision_point/machine_id"),
        candidates=tuple(candidates),
    )


_INTAKE_KEYS = (
    "contract_version",
    "dispatch_id",
    "world_id",
    "request_id",
    "lot_id",
    "lot_revision",
    "route_step",
    "machine_id",
    "decision_time",
    "rule",
    "schedule_version",
    "base_state_revision",
    "source",
    "reason",
)


@dataclass(frozen=True)
class DispatchIntake:
    """A decision the Simulator is asked to execute. A proposal until revalidated."""

    dispatch_id: str
    world_id: str
    request_id: str | None
    lot_id: str
    lot_revision: str
    route_step: str
    machine_id: str
    decision_time: int
    rule_id: str
    rule_version: str
    schedule_version: str | None
    base_state_revision: str
    source: IntakeSource
    reason: str

    def to_document(self) -> dict[str, Any]:
        return {
            "contract_version": INTAKE_CONTRACT,
            "dispatch_id": self.dispatch_id,
            "world_id": self.world_id,
            "request_id": self.request_id,
            "lot_id": self.lot_id,
            "lot_revision": self.lot_revision,
            "route_step": self.route_step,
            "machine_id": self.machine_id,
            "decision_time": _time_document(self.decision_time),
            "rule": {"id": self.rule_id, "version": self.rule_version},
            "schedule_version": self.schedule_version,
            "base_state_revision": self.base_state_revision,
            "source": self.source.value,
            "reason": self.reason,
        }


def decode_intake(source: str | Mapping[str, Any]) -> DispatchIntake:
    """Decode a dispatch intake document strictly; raises :class:`DecisionContractError`."""
    fields = _obj(_as_document(source), "", _INTAKE_KEYS)
    _const(fields["contract_version"], "/contract_version", INTAKE_CONTRACT)
    rule = _obj(fields["rule"], "/rule", ("id", "version"))
    request_id = fields["request_id"]
    schedule_version = fields["schedule_version"]
    try:
        origin = IntakeSource(fields["source"])
    except ValueError:
        raise _fail("/source") from None
    return DispatchIntake(
        dispatch_id=_ident(fields["dispatch_id"], "/dispatch_id"),
        world_id=_ident(fields["world_id"], "/world_id"),
        request_id=None if request_id is None else _ident(request_id, "/request_id"),
        lot_id=_ident(fields["lot_id"], "/lot_id"),
        lot_revision=_ident(fields["lot_revision"], "/lot_revision"),
        route_step=_ident(fields["route_step"], "/route_step"),
        machine_id=_ident(fields["machine_id"], "/machine_id"),
        decision_time=_time(fields["decision_time"], "/decision_time"),
        rule_id=_ident(rule["id"], "/rule/id"),
        rule_version=_ident(rule["version"], "/rule/version"),
        schedule_version=(
            None
            if schedule_version is None
            else _ident(schedule_version, "/schedule_version")
        ),
        base_state_revision=_ident(
            fields["base_state_revision"], "/base_state_revision"
        ),
        source=origin,
        reason=_text(fields["reason"], "/reason"),
    )


@dataclass(frozen=True)
class DispatchOutcome:
    """The Simulator's answer to one intake. ACCEPTED means queued, not executed."""

    dispatch_id: str | None
    world_id: str
    status: OutcomeStatus
    reason_code: RejectReason | None
    simulation_time: int
    state_revision: str

    def to_document(self) -> dict[str, Any]:
        return {
            "contract_version": INTAKE_CONTRACT,
            "kind": "OUTCOME",
            "dispatch_id": self.dispatch_id,
            "world_id": self.world_id,
            "status": self.status.value,
            "reason_code": None if self.reason_code is None else self.reason_code.value,
            "simulation_time": _time_document(self.simulation_time),
            "state_revision": self.state_revision,
            "provenance": PROVENANCE,
        }
