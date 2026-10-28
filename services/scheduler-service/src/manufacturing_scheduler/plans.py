"""Typed, strict ``scheduler.recovery-plan.v1`` (IC-SCH-004) proposal contract.

A RecoveryPlan is a PLAN: a proposal bound to one world and one source snapshot. This
module decodes, validates and serializes it; it never decides that a plan is feasible,
approved or executable. ``validation_result`` is the producer's *report*, unattested:
an independent, world/revision/candidate-bound validation result (DN-SCH-VALID) is
required at the future execution boundary, and no API here activates, approves or
executes anything. ``content_digest`` binds a proposal's exact content (it is not a
signature or a validator certificate).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from manufacturing_scheduler.errors import PlanError
from manufacturing_scheduler.snapshot import (
    FreshnessStatus,
    PlanningInput,
    PlanningSnapshot,
    Usability,
)
from manufacturing_scheduler.wire import (
    Reader,
    format_timestamp,
    loads_strict,
    reject_oracle_fields,
    sha256_digest,
)

PLAN_CONTRACT = "scheduler.recovery-plan.v1"


class GenerationKind(StrEnum):
    #: Hand-written example for contract tests; never operational output.
    DEVELOPMENT_FIXTURE = "DEVELOPMENT_FIXTURE"
    #: Reserved for the dynamic generator (DEP-083); nothing in this package emits it.
    GENERATOR_OUTPUT = "GENERATOR_OUTPUT"


class Direction(StrEnum):
    MINIMIZE = "MINIMIZE"
    MAXIMIZE = "MAXIMIZE"


class SolveStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    OPTIMAL = "OPTIMAL"
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


class Computed(StrEnum):
    COMPUTED = "COMPUTED"
    NOT_COMPUTED = "NOT_COMPUTED"


class CounterfactualStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    AVAILABLE = "AVAILABLE"


class ValidationStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    REPORTED_VALID = "REPORTED_VALID"
    REPORTED_INVALID = "REPORTED_INVALID"


class RationaleStatus(StrEnum):
    NOT_AVAILABLE = "NOT_AVAILABLE"
    TRACE_DERIVED = "TRACE_DERIVED"


def _values(enum: type[StrEnum]) -> tuple[str, ...]:
    return tuple(member.value for member in enum)


@dataclass(frozen=True, slots=True)
class Generation:
    kind: GenerationKind
    generator_id: str
    generator_version: str


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    snapshot_revision: str
    generated_at: datetime


@dataclass(frozen=True, slots=True)
class AffectedMaterial:
    lot_id: str
    lot_revision: str
    route_id: str
    visit_id: str
    position: int


@dataclass(frozen=True, slots=True)
class AffectedEquipment:
    equipment_id: str
    equipment_revision: str


@dataclass(frozen=True, slots=True)
class Assumption:
    assumption_id: str
    statement: str


@dataclass(frozen=True, slots=True)
class ObjectiveTerm:
    metric: str
    unit: str
    direction: Direction
    weight: float


@dataclass(frozen=True, slots=True)
class ObjectiveProfile:
    profile_id: str
    profile_version: str
    method: str
    terms: tuple[ObjectiveTerm, ...]


@dataclass(frozen=True, slots=True)
class Horizon:
    start_at: datetime
    end_at: datetime


@dataclass(frozen=True, slots=True)
class Assignment:
    """A PLANNED placement of one route visit; never an ACTUAL execution fact."""

    assignment_id: str
    lot_id: str
    lot_revision: str
    route_id: str
    visit_id: str
    equipment_id: str
    equipment_revision: str
    start_at: datetime
    end_at: datetime
    batch_id: str | None = None


@dataclass(frozen=True, slots=True)
class Solve:
    status: SolveStatus = SolveStatus.NOT_RUN
    wall_time_ms: float | None = None


@dataclass(frozen=True, slots=True)
class PredictedObjective:
    metric: str
    unit: str
    status: Computed = Computed.NOT_COMPUTED
    value: float | None = None


@dataclass(frozen=True, slots=True)
class Stability:
    status: Computed = Computed.NOT_COMPUTED
    moved_assignment_count: int | None = None


@dataclass(frozen=True, slots=True)
class Counterfactual:
    status: CounterfactualStatus = CounterfactualStatus.NOT_RUN
    result_ref: str | None = None
    counterfactual_world_id: str | None = None


@dataclass(frozen=True, slots=True)
class Validator:
    validator_id: str
    validator_version: str


@dataclass(frozen=True, slots=True)
class ValidationBinding:
    world_id: str
    snapshot_revision: str
    candidate_id: str


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """The producer's relayed report; ``NOT_RUN`` is the only value this package makes."""

    status: ValidationStatus = ValidationStatus.NOT_RUN
    validator: Validator | None = None
    result_ref: str | None = None
    violation_refs: tuple[str, ...] = ()
    bound_to: ValidationBinding | None = None


@dataclass(frozen=True, slots=True)
class Candidate:
    candidate_id: str
    algorithm_id: str
    algorithm_version: str
    horizon: Horizon
    assignments: tuple[Assignment, ...]
    predicted_objectives: tuple[PredictedObjective, ...]
    solve: Solve = field(default_factory=Solve)
    stability: Stability = field(default_factory=Stability)
    counterfactual: Counterfactual = field(default_factory=Counterfactual)
    validation_result: ValidationResult = field(default_factory=ValidationResult)


@dataclass(frozen=True, slots=True)
class Comparison:
    status: Computed = Computed.NOT_COMPUTED
    ranking: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Rationale:
    status: RationaleStatus = RationaleStatus.NOT_AVAILABLE
    summary: str | None = None
    trace_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    recovery_plan_id: str
    incident_id: str
    world_id: str
    source_snapshot: SourceSnapshot
    base_schedule_version: str | None
    generated_at: datetime
    valid_until: datetime
    generation: Generation
    affected_material: tuple[AffectedMaterial, ...]
    affected_equipment: tuple[AffectedEquipment, ...]
    assumptions: tuple[Assumption, ...]
    objective_profile: ObjectiveProfile
    candidate_schedules: tuple[Candidate, ...]
    recommended_candidate_id: str
    comparison: Comparison
    rationale: Rationale

    @property
    def content_digest(self) -> str:
        """Digest of the canonical wire form without the ``content_digest`` field.

        ``sha256:`` over sorted-key, compact, ASCII JSON of the decoded document;
        integers and floats keep their Python JSON spelling (``1`` is not ``1.0``).
        Any material change to the plan changes it. It binds content only: it is no
        approval, signature or validation certificate.
        """

        return sha256_digest(_wire(self))

    def to_wire(self) -> dict[str, Any]:
        return {**_wire(self), "content_digest": self.content_digest}

    @classmethod
    def from_wire(cls, payload: Mapping[str, Any]) -> RecoveryPlan:
        return _decode(payload)

    @classmethod
    def from_json(cls, text: str) -> RecoveryPlan:
        """Strict JSON decoding (duplicate fields, NaN, Infinity rejected) first."""

        return _decode(loads_strict(text, PlanError))

    @property
    def recommended(self) -> Candidate:
        return next(
            item
            for item in self.candidate_schedules
            if item.candidate_id == self.recommended_candidate_id
        )


@dataclass(frozen=True, slots=True)
class PlanHeader:
    """Everything a producer states about a plan except its candidates and binding."""

    recovery_plan_id: str
    incident_id: str
    generated_at: datetime
    valid_until: datetime
    generation: Generation
    affected_material: tuple[AffectedMaterial, ...]
    affected_equipment: tuple[AffectedEquipment, ...]
    assumptions: tuple[Assumption, ...]
    objective_profile: ObjectiveProfile
    recommended_candidate_id: str
    comparison: Comparison = field(default_factory=Comparison)
    rationale: Rationale = field(default_factory=Rationale)


@dataclass(frozen=True, slots=True)
class BindingResult:
    """A plan matches a snapshot's identity; nothing about feasibility is implied."""

    plan_digest: str
    world_id: str
    snapshot_revision: str
    feasibility_assessed: bool = False


# --- serialization ---------------------------------------------------------------


def _ts(value: datetime) -> str:
    return format_timestamp(value)


def _wire_candidate(item: Candidate) -> dict[str, Any]:
    result = item.validation_result
    return {
        "candidate_id": item.candidate_id,
        "algorithm": {
            "algorithm_id": item.algorithm_id,
            "algorithm_version": item.algorithm_version,
        },
        "horizon": {
            "start_at": _ts(item.horizon.start_at),
            "end_at": _ts(item.horizon.end_at),
        },
        "assignments": [
            {
                "assignment_id": a.assignment_id,
                "lot_id": a.lot_id,
                "lot_revision": a.lot_revision,
                "route_id": a.route_id,
                "visit_id": a.visit_id,
                "equipment_id": a.equipment_id,
                "equipment_revision": a.equipment_revision,
                "start_at": _ts(a.start_at),
                "end_at": _ts(a.end_at),
                "batch_id": a.batch_id,
            }
            for a in item.assignments
        ],
        "solve": {
            "status": item.solve.status.value,
            "wall_time_ms": item.solve.wall_time_ms,
        },
        "predicted_objectives": [
            {
                "metric": o.metric,
                "unit": o.unit,
                "status": o.status.value,
                "value": o.value,
            }
            for o in item.predicted_objectives
        ],
        "stability": {
            "status": item.stability.status.value,
            "moved_assignment_count": item.stability.moved_assignment_count,
        },
        "counterfactual": {
            "status": item.counterfactual.status.value,
            "result_ref": item.counterfactual.result_ref,
            "counterfactual_world_id": item.counterfactual.counterfactual_world_id,
        },
        "validation_result": {
            "status": result.status.value,
            "validator": None
            if result.validator is None
            else {
                "validator_id": result.validator.validator_id,
                "validator_version": result.validator.validator_version,
            },
            "result_ref": result.result_ref,
            "violation_refs": list(result.violation_refs),
            "bound_to": None
            if result.bound_to is None
            else {
                "world_id": result.bound_to.world_id,
                "snapshot_revision": result.bound_to.snapshot_revision,
                "candidate_id": result.bound_to.candidate_id,
            },
        },
    }


def _wire(plan: RecoveryPlan) -> dict[str, Any]:
    profile = plan.objective_profile
    return {
        "contract_version": PLAN_CONTRACT,
        "recovery_plan_id": plan.recovery_plan_id,
        "incident_id": plan.incident_id,
        "world_id": plan.world_id,
        "source_snapshot": {
            "snapshot_revision": plan.source_snapshot.snapshot_revision,
            "generated_at": _ts(plan.source_snapshot.generated_at),
        },
        "base_schedule_version": plan.base_schedule_version,
        "generated_at": _ts(plan.generated_at),
        "valid_until": _ts(plan.valid_until),
        "generation": {
            "kind": plan.generation.kind.value,
            "generator_id": plan.generation.generator_id,
            "generator_version": plan.generation.generator_version,
        },
        "affected_material": [
            {
                "lot_id": m.lot_id,
                "lot_revision": m.lot_revision,
                "route_id": m.route_id,
                "visit_id": m.visit_id,
                "position": m.position,
            }
            for m in plan.affected_material
        ],
        "affected_equipment": [
            {
                "equipment_id": e.equipment_id,
                "equipment_revision": e.equipment_revision,
            }
            for e in plan.affected_equipment
        ],
        "assumptions": [
            {"assumption_id": a.assumption_id, "statement": a.statement}
            for a in plan.assumptions
        ],
        "objective_profile": {
            "profile_id": profile.profile_id,
            "profile_version": profile.profile_version,
            "method": profile.method,
            "terms": [
                {
                    "metric": t.metric,
                    "unit": t.unit,
                    "direction": t.direction.value,
                    "weight": t.weight,
                }
                for t in profile.terms
            ],
        },
        "candidate_schedules": [_wire_candidate(c) for c in plan.candidate_schedules],
        "recommended_candidate_id": plan.recommended_candidate_id,
        "comparison": {
            "status": plan.comparison.status.value,
            "ranking": list(plan.comparison.ranking),
        },
        "rationale": {
            "status": plan.rationale.status.value,
            "summary": plan.rationale.summary,
            "trace_refs": list(plan.rationale.trace_refs),
        },
    }


# --- decoding --------------------------------------------------------------------

_R = Reader(PlanError)

_PLAN_KEYS = (
    "contract_version",
    "recovery_plan_id",
    "incident_id",
    "world_id",
    "source_snapshot",
    "base_schedule_version",
    "generated_at",
    "valid_until",
    "generation",
    "affected_material",
    "affected_equipment",
    "assumptions",
    "objective_profile",
    "candidate_schedules",
    "recommended_candidate_id",
    "comparison",
    "rationale",
    "content_digest",
)


def _nullable_ident(value: Any, path: str) -> str | None:
    return None if value is None else _R.ident(value, path)


def _nullable_number(value: Any, path: str, *, minimum: float | None) -> float | None:
    return None if value is None else _R.number(value, path, minimum=minimum)


def _decode_assignment(raw: Any, path: str) -> Assignment:
    keys = (
        "assignment_id",
        "lot_id",
        "lot_revision",
        "route_id",
        "visit_id",
        "equipment_id",
        "equipment_revision",
        "start_at",
        "end_at",
        "batch_id",
    )
    o = _R.obj(raw, path, keys)
    return Assignment(
        _R.ident(o["assignment_id"], f"{path}/assignment_id"),
        _R.ident(o["lot_id"], f"{path}/lot_id"),
        _R.ident(o["lot_revision"], f"{path}/lot_revision"),
        _R.ident(o["route_id"], f"{path}/route_id"),
        _R.ident(o["visit_id"], f"{path}/visit_id"),
        _R.ident(o["equipment_id"], f"{path}/equipment_id"),
        _R.ident(o["equipment_revision"], f"{path}/equipment_revision"),
        _R.timestamp(o["start_at"], f"{path}/start_at", canonical=True),
        _R.timestamp(o["end_at"], f"{path}/end_at", canonical=True),
        _nullable_ident(o["batch_id"], f"{path}/batch_id"),
    )


def _decode_validation(raw: Any, path: str) -> ValidationResult:
    keys = ("status", "validator", "result_ref", "violation_refs", "bound_to")
    o = _R.obj(raw, path, keys)
    status = ValidationStatus(_R.enum(o["status"], f"{path}/status", _VALIDATION))
    validator = None
    if o["validator"] is not None:
        v = _R.obj(
            o["validator"], f"{path}/validator", ("validator_id", "validator_version")
        )
        validator = Validator(
            _R.ident(v["validator_id"], f"{path}/validator/validator_id"),
            _R.ident(v["validator_version"], f"{path}/validator/validator_version"),
        )
    bound = None
    if o["bound_to"] is not None:
        b = _R.obj(
            o["bound_to"],
            f"{path}/bound_to",
            ("world_id", "snapshot_revision", "candidate_id"),
        )
        bound = ValidationBinding(
            _R.ident(b["world_id"], f"{path}/bound_to/world_id"),
            _R.ident(b["snapshot_revision"], f"{path}/bound_to/snapshot_revision"),
            _R.ident(b["candidate_id"], f"{path}/bound_to/candidate_id"),
        )
    refs = tuple(
        _R.ident(item, f"{path}/violation_refs/{i}")
        for i, item in enumerate(
            _R.array(o["violation_refs"], f"{path}/violation_refs")
        )
    )
    return ValidationResult(
        status,
        validator,
        _nullable_ident(o["result_ref"], f"{path}/result_ref"),
        refs,
        bound,
    )


_SOLVE = _values(SolveStatus)
_COMPUTED = _values(Computed)
_COUNTERFACTUAL = _values(CounterfactualStatus)
_VALIDATION = _values(ValidationStatus)
_RATIONALE = _values(RationaleStatus)
_DIRECTIONS = _values(Direction)
_KINDS = _values(GenerationKind)


def _decode_candidate(raw: Any, path: str) -> Candidate:
    keys = (
        "candidate_id",
        "algorithm",
        "horizon",
        "assignments",
        "solve",
        "predicted_objectives",
        "stability",
        "counterfactual",
        "validation_result",
    )
    o = _R.obj(raw, path, keys)
    algorithm = _R.obj(
        o["algorithm"], f"{path}/algorithm", ("algorithm_id", "algorithm_version")
    )
    horizon = _R.obj(o["horizon"], f"{path}/horizon", ("start_at", "end_at"))
    solve = _R.obj(o["solve"], f"{path}/solve", ("status", "wall_time_ms"))
    stability = _R.obj(
        o["stability"], f"{path}/stability", ("status", "moved_assignment_count")
    )
    cf = _R.obj(
        o["counterfactual"],
        f"{path}/counterfactual",
        ("status", "result_ref", "counterfactual_world_id"),
    )
    objectives: list[PredictedObjective] = []
    for i, item in enumerate(
        _R.array(o["predicted_objectives"], f"{path}/predicted_objectives")
    ):
        where = f"{path}/predicted_objectives/{i}"
        p = _R.obj(item, where, ("metric", "unit", "status", "value"))
        objectives.append(
            PredictedObjective(
                _R.ident(p["metric"], f"{where}/metric"),
                _R.ident(p["unit"], f"{where}/unit"),
                Computed(_R.enum(p["status"], f"{where}/status", _COMPUTED)),
                _nullable_number(p["value"], f"{where}/value", minimum=None),
            )
        )
    moved = stability["moved_assignment_count"]
    return Candidate(
        candidate_id=_R.ident(o["candidate_id"], f"{path}/candidate_id"),
        algorithm_id=_R.ident(
            algorithm["algorithm_id"], f"{path}/algorithm/algorithm_id"
        ),
        algorithm_version=_R.ident(
            algorithm["algorithm_version"], f"{path}/algorithm/algorithm_version"
        ),
        horizon=Horizon(
            _R.timestamp(
                horizon["start_at"], f"{path}/horizon/start_at", canonical=True
            ),
            _R.timestamp(horizon["end_at"], f"{path}/horizon/end_at", canonical=True),
        ),
        assignments=tuple(
            _decode_assignment(item, f"{path}/assignments/{i}")
            for i, item in enumerate(_R.array(o["assignments"], f"{path}/assignments"))
        ),
        predicted_objectives=tuple(objectives),
        solve=Solve(
            SolveStatus(_R.enum(solve["status"], f"{path}/solve/status", _SOLVE)),
            _nullable_number(
                solve["wall_time_ms"], f"{path}/solve/wall_time_ms", minimum=0
            ),
        ),
        stability=Stability(
            Computed(
                _R.enum(stability["status"], f"{path}/stability/status", _COMPUTED)
            ),
            None
            if moved is None
            else _R.integer(moved, f"{path}/stability/moved_assignment_count"),
        ),
        counterfactual=Counterfactual(
            CounterfactualStatus(
                _R.enum(cf["status"], f"{path}/counterfactual/status", _COUNTERFACTUAL)
            ),
            _nullable_ident(cf["result_ref"], f"{path}/counterfactual/result_ref"),
            _nullable_ident(
                cf["counterfactual_world_id"],
                f"{path}/counterfactual/counterfactual_world_id",
            ),
        ),
        validation_result=_decode_validation(
            o["validation_result"], f"{path}/validation_result"
        ),
    )


def _decode(payload: Mapping[str, Any]) -> RecoveryPlan:
    reject_oracle_fields(payload, PlanError)
    top = _R.obj(payload, "", _PLAN_KEYS)
    _R.const(top["contract_version"], "/contract_version", PLAN_CONTRACT)
    snap = _R.obj(
        top["source_snapshot"],
        "/source_snapshot",
        ("snapshot_revision", "generated_at"),
    )
    gen = _R.obj(
        top["generation"],
        "/generation",
        ("kind", "generator_id", "generator_version"),
    )
    profile = _R.obj(
        top["objective_profile"],
        "/objective_profile",
        ("profile_id", "profile_version", "method", "terms"),
    )
    terms: list[ObjectiveTerm] = []
    for i, item in enumerate(
        _R.array(profile["terms"], "/objective_profile/terms", min_items=1)
    ):
        where = f"/objective_profile/terms/{i}"
        t = _R.obj(item, where, ("metric", "unit", "direction", "weight"))
        terms.append(
            ObjectiveTerm(
                _R.ident(t["metric"], f"{where}/metric"),
                _R.ident(t["unit"], f"{where}/unit"),
                Direction(_R.enum(t["direction"], f"{where}/direction", _DIRECTIONS)),
                _R.number(t["weight"], f"{where}/weight", minimum=0),
            )
        )
    material: list[AffectedMaterial] = []
    for i, item in enumerate(_R.array(top["affected_material"], "/affected_material")):
        where = f"/affected_material/{i}"
        m = _R.obj(
            item, where, ("lot_id", "lot_revision", "route_id", "visit_id", "position")
        )
        material.append(
            AffectedMaterial(
                _R.ident(m["lot_id"], f"{where}/lot_id"),
                _R.ident(m["lot_revision"], f"{where}/lot_revision"),
                _R.ident(m["route_id"], f"{where}/route_id"),
                _R.ident(m["visit_id"], f"{where}/visit_id"),
                _R.integer(m["position"], f"{where}/position"),
            )
        )
    equipment: list[AffectedEquipment] = []
    for i, item in enumerate(
        _R.array(top["affected_equipment"], "/affected_equipment")
    ):
        where = f"/affected_equipment/{i}"
        e = _R.obj(item, where, ("equipment_id", "equipment_revision"))
        equipment.append(
            AffectedEquipment(
                _R.ident(e["equipment_id"], f"{where}/equipment_id"),
                _R.ident(e["equipment_revision"], f"{where}/equipment_revision"),
            )
        )
    assumptions: list[Assumption] = []
    for i, item in enumerate(_R.array(top["assumptions"], "/assumptions")):
        where = f"/assumptions/{i}"
        a = _R.obj(item, where, ("assumption_id", "statement"))
        assumptions.append(
            Assumption(
                _R.ident(a["assumption_id"], f"{where}/assumption_id"),
                _R.text(a["statement"], f"{where}/statement"),
            )
        )
    comparison = _R.obj(top["comparison"], "/comparison", ("status", "ranking"))
    rationale = _R.obj(
        top["rationale"], "/rationale", ("status", "summary", "trace_refs")
    )
    summary = rationale["summary"]
    base = top["base_schedule_version"]
    plan = RecoveryPlan(
        recovery_plan_id=_R.ident(top["recovery_plan_id"], "/recovery_plan_id"),
        incident_id=_R.ident(top["incident_id"], "/incident_id"),
        world_id=_R.ident(top["world_id"], "/world_id"),
        source_snapshot=SourceSnapshot(
            _R.ident(snap["snapshot_revision"], "/source_snapshot/snapshot_revision"),
            _R.timestamp(
                snap["generated_at"], "/source_snapshot/generated_at", canonical=True
            ),
        ),
        base_schedule_version=_nullable_ident(base, "/base_schedule_version"),
        generated_at=_R.timestamp(top["generated_at"], "/generated_at", canonical=True),
        valid_until=_R.timestamp(top["valid_until"], "/valid_until", canonical=True),
        generation=Generation(
            GenerationKind(_R.enum(gen["kind"], "/generation/kind", _KINDS)),
            _R.ident(gen["generator_id"], "/generation/generator_id"),
            _R.ident(gen["generator_version"], "/generation/generator_version"),
        ),
        affected_material=tuple(material),
        affected_equipment=tuple(equipment),
        assumptions=tuple(assumptions),
        objective_profile=ObjectiveProfile(
            _R.ident(profile["profile_id"], "/objective_profile/profile_id"),
            _R.ident(profile["profile_version"], "/objective_profile/profile_version"),
            _R.ident(profile["method"], "/objective_profile/method"),
            tuple(terms),
        ),
        candidate_schedules=tuple(
            _decode_candidate(item, f"/candidate_schedules/{i}")
            for i, item in enumerate(
                _R.array(
                    top["candidate_schedules"], "/candidate_schedules", min_items=1
                )
            )
        ),
        recommended_candidate_id=_R.ident(
            top["recommended_candidate_id"], "/recommended_candidate_id"
        ),
        comparison=Comparison(
            Computed(_R.enum(comparison["status"], "/comparison/status", _COMPUTED)),
            tuple(
                _R.ident(item, f"/comparison/ranking/{i}")
                for i, item in enumerate(
                    _R.array(comparison["ranking"], "/comparison/ranking")
                )
            ),
        ),
        rationale=Rationale(
            RationaleStatus(
                _R.enum(rationale["status"], "/rationale/status", _RATIONALE)
            ),
            None if summary is None else _R.text(summary, "/rationale/summary"),
            tuple(
                _R.ident(item, f"/rationale/trace_refs/{i}")
                for i, item in enumerate(
                    _R.array(rationale["trace_refs"], "/rationale/trace_refs")
                )
            ),
        ),
    )
    _check_semantics(plan)
    claimed = top["content_digest"]
    if not isinstance(claimed, str) or claimed != plan.content_digest:
        _R.fail("DIGEST_MISMATCH", "/content_digest")
    return plan


# --- cross-field semantics -------------------------------------------------------


def _unique(values: Sequence[str], path: str) -> None:
    if len(set(values)) != len(values):
        _R.fail("DUPLICATE_ID", path)


def _check_candidate(plan: RecoveryPlan, item: Candidate, path: str) -> None:
    if item.horizon.start_at >= item.horizon.end_at:
        _R.fail("INTERVAL_INVALID", f"{path}/horizon")
    _unique([a.assignment_id for a in item.assignments], f"{path}/assignments")
    _unique(
        [f"{a.lot_id}\n{a.visit_id}" for a in item.assignments],
        f"{path}/assignments",
    )
    batches: dict[str, Assignment] = {}
    for i, a in enumerate(item.assignments):
        where = f"{path}/assignments/{i}"
        if a.start_at >= a.end_at:
            _R.fail("INTERVAL_INVALID", where)
        if a.start_at < item.horizon.start_at or a.end_at > item.horizon.end_at:
            _R.fail("OUTSIDE_HORIZON", where)
        if a.batch_id is not None:
            first = batches.setdefault(a.batch_id, a)
            if (first.equipment_id, first.start_at, first.end_at) != (
                a.equipment_id,
                a.start_at,
                a.end_at,
            ):
                _R.fail("BATCH_INCONSISTENT", where)
    terms = plan.objective_profile.terms
    if len(item.predicted_objectives) != len(terms):
        _R.fail("OBJECTIVE_MISMATCH", f"{path}/predicted_objectives")
    for i, (obj, term) in enumerate(zip(item.predicted_objectives, terms, strict=True)):
        where = f"{path}/predicted_objectives/{i}"
        if (obj.metric, obj.unit) != (term.metric, term.unit):
            _R.fail("OBJECTIVE_MISMATCH", where)
        if (obj.status is Computed.COMPUTED) != (obj.value is not None):
            _R.fail("STATE_INCONSISTENT", where)
    solve = item.solve
    if (solve.status is SolveStatus.NOT_RUN) != (solve.wall_time_ms is None):
        _R.fail("STATE_INCONSISTENT", f"{path}/solve")
    stab = item.stability
    if (stab.status is Computed.COMPUTED) != (stab.moved_assignment_count is not None):
        _R.fail("STATE_INCONSISTENT", f"{path}/stability")
    cf = item.counterfactual
    available = cf.status is CounterfactualStatus.AVAILABLE
    if available != (cf.result_ref is not None) or available != (
        cf.counterfactual_world_id is not None
    ):
        _R.fail("STATE_INCONSISTENT", f"{path}/counterfactual")
    val = item.validation_result
    where = f"{path}/validation_result"
    if val.status is ValidationStatus.NOT_RUN:
        if val.validator or val.result_ref or val.violation_refs or val.bound_to:
            _R.fail("STATE_INCONSISTENT", where)
        return
    if val.validator is None or val.result_ref is None or val.bound_to is None:
        _R.fail("STATE_INCONSISTENT", where)
    if (val.status is ValidationStatus.REPORTED_INVALID) != bool(val.violation_refs):
        _R.fail("STATE_INCONSISTENT", where)
    expected = (
        plan.world_id,
        plan.source_snapshot.snapshot_revision,
        item.candidate_id,
    )
    bound = val.bound_to
    if (bound.world_id, bound.snapshot_revision, bound.candidate_id) != expected:
        _R.fail("BINDING_MISMATCH", f"{where}/bound_to")


def _check_semantics(plan: RecoveryPlan) -> None:
    if plan.generated_at >= plan.valid_until:
        _R.fail("INTERVAL_INVALID", "/valid_until")
    if plan.source_snapshot.generated_at > plan.generated_at:
        _R.fail("INTERVAL_INVALID", "/source_snapshot/generated_at")
    _unique([m.lot_id for m in plan.affected_material], "/affected_material")
    _unique([e.equipment_id for e in plan.affected_equipment], "/affected_equipment")
    _unique([a.assumption_id for a in plan.assumptions], "/assumptions")
    _unique(
        [t.metric for t in plan.objective_profile.terms], "/objective_profile/terms"
    )
    ids = [c.candidate_id for c in plan.candidate_schedules]
    _unique(ids, "/candidate_schedules")
    if plan.recommended_candidate_id not in ids:
        _R.fail("UNKNOWN_CANDIDATE", "/recommended_candidate_id")
    for i, item in enumerate(plan.candidate_schedules):
        _check_candidate(plan, item, f"/candidate_schedules/{i}")
    cmp = plan.comparison
    if cmp.status is Computed.NOT_COMPUTED:
        if cmp.ranking:
            _R.fail("STATE_INCONSISTENT", "/comparison/ranking")
    else:
        if not cmp.ranking:
            _R.fail("STATE_INCONSISTENT", "/comparison/ranking")
        if sorted(cmp.ranking) != sorted(ids):
            _R.fail("UNKNOWN_CANDIDATE", "/comparison/ranking")
        if any(
            o.status is not Computed.COMPUTED
            for c in plan.candidate_schedules
            for o in c.predicted_objectives
        ):
            _R.fail("STATE_INCONSISTENT", "/comparison/status")
    rat = plan.rationale
    derived = rat.status is RationaleStatus.TRACE_DERIVED
    if derived != (rat.summary is not None) or derived != bool(rat.trace_refs):
        _R.fail("STATE_INCONSISTENT", "/rationale")
    _unique(rat.trace_refs, "/rationale/trace_refs")


# --- binding and producer path ---------------------------------------------------


def check_snapshot_binding(
    plan: RecoveryPlan, snapshot: PlanningSnapshot
) -> BindingResult:
    """Require the plan to cite exactly the snapshot it claims to be computed from.

    World, snapshot revision and instant, base schedule version, and every cited lot,
    route visit and equipment (with its exact revision) must match. Eligibility,
    overlaps, maintenance and every other feasibility rule are NOT assessed here.
    """

    if plan.world_id != snapshot.world_id:
        _R.fail("BINDING_MISMATCH", "/world_id")
    cited = plan.source_snapshot
    if (cited.snapshot_revision, cited.generated_at) != (
        snapshot.snapshot_revision,
        snapshot.generated_at,
    ):
        _R.fail("BINDING_MISMATCH", "/source_snapshot")
    if plan.base_schedule_version != snapshot.current_schedule_version:
        _R.fail("BINDING_MISMATCH", "/base_schedule_version")
    lots = {lot.lot_id: lot for lot in snapshot.lots}
    equipment = {item.equipment_id: item for item in snapshot.equipment}

    def check_lot(
        lot_id: str, revision: str | None, visit_id: str, route_id: str, path: str
    ) -> None:
        lot = lots.get(lot_id)
        if lot is None:
            _R.fail("UNKNOWN_REFERENCE", path)
        if (revision is not None and revision != lot.revision) or (
            visit_id,
            route_id,
        ) != (lot.visit.visit_id, lot.visit.route_id):
            _R.fail("BINDING_MISMATCH", path)

    def check_equipment(equipment_id: str, revision: str, path: str) -> None:
        item = equipment.get(equipment_id)
        if item is None:
            _R.fail("UNKNOWN_REFERENCE", path)
        if item.revision != revision:
            _R.fail("BINDING_MISMATCH", path)

    for i, m in enumerate(plan.affected_material):
        path = f"/affected_material/{i}"
        check_lot(m.lot_id, m.lot_revision, m.visit_id, m.route_id, path)
        if m.position != lots[m.lot_id].visit.position:
            _R.fail("BINDING_MISMATCH", path)
    for i, e in enumerate(plan.affected_equipment):
        check_equipment(
            e.equipment_id, e.equipment_revision, f"/affected_equipment/{i}"
        )
    for ci, candidate in enumerate(plan.candidate_schedules):
        for ai, a in enumerate(candidate.assignments):
            path = f"/candidate_schedules/{ci}/assignments/{ai}"
            check_lot(a.lot_id, a.lot_revision, a.visit_id, a.route_id, path)
            check_equipment(a.equipment_id, a.equipment_revision, path)
    return BindingResult(
        plan.content_digest, snapshot.world_id, snapshot.snapshot_revision
    )


def propose_recovery_plan(
    planning_input: PlanningInput,
    header: PlanHeader,
    candidates: Sequence[Candidate],
    *,
    now: datetime,
) -> RecoveryPlan:
    """Assemble a bound, validated-for-shape proposal from a typed producer port.

    The candidates come from the caller (the future DEP-083 generator); nothing is
    computed here. A candidate that already carries a validity report is refused: this
    path cannot manufacture independent validity, approval or execution eligibility.

    Construction is a *current* act, so freshness is rechecked at the caller-supplied
    aware-UTC ``now`` (no hidden clock): the retained ``NORMAL`` label proves nothing
    about the present. The snapshot must be FRESH, already generated and unexpired
    (``now < valid_until``; the end is exclusive), and the plan may not be generated at
    or after the source's expiry. Decoding a historical plan does not do this check.
    """

    if (
        not isinstance(now, datetime)
        or now.tzinfo is None
        or now.utcoffset() != UTC.utcoffset(None)
    ):
        _R.fail("NOW_NOT_AWARE_UTC", "/now")
    snapshot = planning_input.snapshot
    if (
        snapshot.usability is not Usability.NORMAL
        or snapshot.freshness_status is not FreshnessStatus.FRESH
    ):
        _R.fail("SNAPSHOT_NOT_USABLE", "/source_snapshot")
    if now < snapshot.generated_at:
        _R.fail("SNAPSHOT_FROM_FUTURE", "/source_snapshot")
    if now >= snapshot.valid_until:
        _R.fail("SNAPSHOT_EXPIRED", "/source_snapshot")
    if header.generated_at >= snapshot.valid_until:
        _R.fail("PLAN_AFTER_SOURCE_EXPIRY", "/generated_at")
    for i, item in enumerate(candidates):
        if item.validation_result != ValidationResult():
            _R.fail("VALIDITY_CLAIM_REJECTED", f"/candidate_schedules/{i}")
    draft = RecoveryPlan(
        recovery_plan_id=header.recovery_plan_id,
        incident_id=header.incident_id,
        world_id=snapshot.world_id,
        source_snapshot=SourceSnapshot(
            snapshot.snapshot_revision, snapshot.generated_at
        ),
        base_schedule_version=snapshot.current_schedule_version,
        generated_at=header.generated_at,
        valid_until=header.valid_until,
        generation=header.generation,
        affected_material=header.affected_material,
        affected_equipment=header.affected_equipment,
        assumptions=header.assumptions,
        objective_profile=header.objective_profile,
        candidate_schedules=tuple(candidates),
        recommended_candidate_id=header.recommended_candidate_id,
        comparison=header.comparison,
        rationale=header.rationale,
    )
    plan = RecoveryPlan.from_wire(draft.to_wire())
    check_snapshot_binding(plan, snapshot)
    return plan
