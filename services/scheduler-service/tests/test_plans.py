"""RecoveryPlan decoding, cross-field semantics, snapshot binding and producer path."""

from __future__ import annotations

import copy
import dataclasses
import json
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from manufacturing_scheduler.errors import PlanError
from manufacturing_scheduler.plans import (
    AffectedEquipment,
    AffectedMaterial,
    Assignment,
    Candidate,
    Computed,
    PlanHeader,
    RecoveryPlan,
    ValidationBinding,
    ValidationResult,
    ValidationStatus,
    Validator,
    check_snapshot_binding,
    propose_recovery_plan,
)
from manufacturing_scheduler.snapshot import (
    FreshnessMode,
    FreshnessStatus,
    parse_snapshot,
    to_planning_input,
)
from manufacturing_scheduler.wire import canonical_json
from plan_helpers import (
    NOW,
    Doc,
    mutated,
    parsed_snapshot,
    plan_doc,
    policy,
    redigest,
    snapshot_doc,
)

Change = Callable[[Doc], None]
CAND = "candidate_schedules"
VALID = "recovery-plan.self-reported-valid.json"


def _set(path: str, value: Any) -> Change:
    def apply(doc: Doc) -> None:
        node: Any = doc
        keys = path.split("/")
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        if isinstance(node, list):
            node[int(keys[-1])] = value
        else:
            node[keys[-1]] = value

    return apply


def _both(path: str, **fields: Any) -> Change:
    def apply(doc: Doc) -> None:
        node: Any = doc
        for key in path.split("/"):
            node = node[int(key)] if isinstance(node, list) else node[key]
        node.update(fields)

    return apply


def _drop(path: str) -> Change:
    def apply(doc: Doc) -> None:
        node: Any = doc
        keys = path.split("/")
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        del node[keys[-1]]

    return apply


@pytest.mark.parametrize("name", ["recovery-plan.v1.json", VALID])
def test_published_fixtures_decode_and_roundtrip_exactly(name: str) -> None:
    doc = plan_doc(name)
    plan = RecoveryPlan.from_wire(doc)
    assert plan.to_wire() == doc
    assert RecoveryPlan.from_wire(plan.to_wire()) == plan
    assert plan.content_digest == doc["content_digest"]
    text = json.dumps(doc, indent=2)
    assert RecoveryPlan.from_json(text) == plan
    assert canonical_json(plan.to_wire()) == canonical_json(doc)


def test_pending_fixture_computes_nothing_and_claims_no_validity() -> None:
    plan = RecoveryPlan.from_wire(plan_doc())
    assert plan.generation.kind.value == "DEVELOPMENT_FIXTURE"
    assert (
        plan.comparison.status is Computed.NOT_COMPUTED
        and plan.comparison.ranking == ()
    )
    assert plan.rationale.summary is None
    for item in plan.candidate_schedules:
        assert item.validation_result == ValidationResult()
        assert item.solve.wall_time_ms is None
        assert all(o.value is None for o in item.predicted_objectives)
        assert item.counterfactual.result_ref is None
    assert plan.recommended.candidate_id == plan.recommended_candidate_id


def _first_candidate(change: Callable[[Doc], None]) -> Change:
    return lambda doc: change(doc[CAND][0])


def _swap_ids(doc: Doc) -> None:
    doc[CAND][1]["candidate_id"] = doc[CAND][0]["candidate_id"]


def _duplicate_trace_refs(doc: Doc) -> None:
    doc["rationale"].update(
        status="TRACE_DERIVED", summary="A claim.", trace_refs=["T1", "T1"]
    )


def _batch_split(doc: Doc) -> None:
    for item in doc[CAND][0]["assignments"]:
        item["batch_id"] = "B1"  # two lots on different intervals share one batch


STRUCTURAL: list[tuple[str, Change, str]] = [
    (
        "version",
        _set("contract_version", "scheduler.recovery-plan.v2"),
        "VERSION_UNSUPPORTED",
    ),
    ("unknown-top", _set("execution_eligible", True), "FIELD_UNKNOWN"),
    ("unknown-nested", _set(f"{CAND}/0/solve/extra", 1), "FIELD_UNKNOWN"),
    ("missing-top", _drop("rationale"), "FIELD_MISSING"),
    ("oracle", _set(f"{CAND}/0/oracle_label", "x"), "ORACLE_FIELD_REJECTED"),
    ("padded-id", _set("incident_id", " INC"), "IDENTIFIER_INVALID"),
    ("bool-weight", _set("objective_profile/terms/0/weight", True), "NUMBER_INVALID"),
    ("negative-weight", _set("objective_profile/terms/0/weight", -1), "NUMBER_INVALID"),
    (
        "huge-number",
        _set(f"{CAND}/0/predicted_objectives/0/value", 1e300),
        "NUMBER_INVALID",
    ),
    ("string-number", _set(f"{CAND}/0/solve/wall_time_ms", "5"), "NUMBER_INVALID"),
    (
        "float-count",
        _set(f"{CAND}/0/stability/moved_assignment_count", 1.0),
        "INTEGER_INVALID",
    ),
    ("bool-position", _set("affected_material/0/position", True), "INTEGER_INVALID"),
    ("naive-time", _set("generated_at", "2026-10-27T08:01:00"), "TIMESTAMP_INVALID"),
    (
        "offset-time",
        _set("generated_at", "2026-10-27T08:01:00+00:00"),
        "TIMESTAMP_NOT_CANONICAL",
    ),
    (
        "trailing-zero",
        _set("generated_at", "2026-10-27T08:01:00.50Z"),
        "TIMESTAMP_NOT_CANONICAL",
    ),
    ("enum", _set(f"{CAND}/0/solve/status", "DONE"), "ENUM_INVALID"),
    ("empty-candidates", _set(CAND, []), "ARRAY_TOO_SHORT"),
    ("empty-terms", _set("objective_profile/terms", []), "ARRAY_TOO_SHORT"),
    ("assignments-not-array", _set(f"{CAND}/0/assignments", "none"), "ARRAY_REQUIRED"),
]

SEMANTIC: list[tuple[str, Change, str]] = [
    ("duplicate-candidate", _swap_ids, "DUPLICATE_ID"),
    (
        "duplicate-assignment-id",
        _set(f"{CAND}/0/assignments/1/assignment_id", "A-1"),
        "DUPLICATE_ID",
    ),
    (
        "duplicate-visit",
        _both(f"{CAND}/0/assignments/1", lot_id="LOT-001", visit_id="VISIT-A-03"),
        "DUPLICATE_ID",
    ),
    (
        "duplicate-affected-lot",
        _set("affected_material/1/lot_id", "LOT-001"),
        "DUPLICATE_ID",
    ),
    (
        "duplicate-metric",
        _set("objective_profile/terms/1/metric", "total_tardiness"),
        "DUPLICATE_ID",
    ),
    (
        "recommended-missing",
        _set("recommended_candidate_id", "FIXTURE-CAND-Z"),
        "UNKNOWN_CANDIDATE",
    ),
    (
        "assignment-reversed",
        _set(f"{CAND}/0/assignments/0/end_at", "2026-10-27T08:05:00Z"),
        "INTERVAL_INVALID",
    ),
    (
        "assignment-empty",
        _set(f"{CAND}/0/assignments/0/end_at", "2026-10-27T08:05:00Z"),
        "INTERVAL_INVALID",
    ),
    (
        "outside-horizon",
        _set(f"{CAND}/0/assignments/1/end_at", "2026-10-27T20:05:01Z"),
        "OUTSIDE_HORIZON",
    ),
    (
        "before-horizon",
        _set(f"{CAND}/0/assignments/0/start_at", "2026-10-27T08:04:59Z"),
        "OUTSIDE_HORIZON",
    ),
    (
        "horizon-reversed",
        _set(f"{CAND}/0/horizon/end_at", "2026-10-27T08:05:00Z"),
        "INTERVAL_INVALID",
    ),
    (
        "validity-reversed",
        _set("valid_until", "2026-10-27T08:01:00Z"),
        "INTERVAL_INVALID",
    ),
    (
        "snapshot-after-plan",
        _set("source_snapshot/generated_at", "2026-10-27T08:02:00Z"),
        "INTERVAL_INVALID",
    ),
    (
        "metric-mismatch",
        _set(f"{CAND}/0/predicted_objectives/0/metric", "other"),
        "OBJECTIVE_MISMATCH",
    ),
    (
        "unit-mismatch",
        _set(f"{CAND}/0/predicted_objectives/1/unit", "hour"),
        "OBJECTIVE_MISMATCH",
    ),
    (
        "objective-count",
        _set(f"{CAND}/0/predicted_objectives", []),
        "OBJECTIVE_MISMATCH",
    ),
    (
        "computed-without-value",
        _set(f"{CAND}/0/predicted_objectives/0/status", "COMPUTED"),
        "STATE_INCONSISTENT",
    ),
    (
        "value-without-compute",
        _set(f"{CAND}/0/predicted_objectives/0/value", 0),
        "STATE_INCONSISTENT",
    ),
    (
        "not-run-with-time",
        _set(f"{CAND}/0/solve/wall_time_ms", 3),
        "STATE_INCONSISTENT",
    ),
    (
        "solved-without-time",
        _set(f"{CAND}/0/solve/status", "OPTIMAL"),
        "STATE_INCONSISTENT",
    ),
    (
        "stability-count-only",
        _set(f"{CAND}/0/stability/moved_assignment_count", 2),
        "STATE_INCONSISTENT",
    ),
    (
        "counterfactual-ref-only",
        _set(f"{CAND}/0/counterfactual/result_ref", "REF"),
        "STATE_INCONSISTENT",
    ),
    (
        "validation-not-run-with-validator",
        _set(
            f"{CAND}/0/validation_result/validator",
            {"validator_id": "V", "validator_version": "1"},
        ),
        "STATE_INCONSISTENT",
    ),
    (
        "comparison-ranking-uncomputed",
        _set("comparison/ranking", ["FIXTURE-CAND-A", "FIXTURE-CAND-B"]),
        "STATE_INCONSISTENT",
    ),
    (
        "comparison-before-objectives",
        _set("comparison/status", "COMPUTED"),
        "STATE_INCONSISTENT",
    ),
    (
        "rationale-summary-only",
        _set("rationale/summary", "A claim."),
        "STATE_INCONSISTENT",
    ),
    ("rationale-refs-only", _set("rationale/trace_refs", ["T1"]), "STATE_INCONSISTENT"),
    (
        "batch-split",
        _batch_split,
        "BATCH_INCONSISTENT",
    ),
    ("duplicate-trace-ref", _duplicate_trace_refs, "DUPLICATE_ID"),
]

VALIDITY: list[tuple[str, Change, str]] = [
    (
        "valid-without-validator",
        _set(f"{CAND}/0/validation_result/validator", None),
        "STATE_INCONSISTENT",
    ),
    (
        "valid-without-ref",
        _set(f"{CAND}/0/validation_result/result_ref", None),
        "STATE_INCONSISTENT",
    ),
    (
        "valid-with-violations",
        _set(f"{CAND}/0/validation_result/violation_refs", ["V1"]),
        "STATE_INCONSISTENT",
    ),
    (
        "invalid-without-violations",
        _set(f"{CAND}/0/validation_result/status", "REPORTED_INVALID"),
        "STATE_INCONSISTENT",
    ),
    (
        "bound-other-world",
        _set(f"{CAND}/0/validation_result/bound_to/world_id", "COUNTERFACTUAL"),
        "BINDING_MISMATCH",
    ),
    (
        "bound-other-revision",
        _set(f"{CAND}/0/validation_result/bound_to/snapshot_revision", "twin-rev-1"),
        "BINDING_MISMATCH",
    ),
    (
        "bound-other-candidate",
        _set(f"{CAND}/0/validation_result/bound_to/candidate_id", "FIXTURE-CAND-B"),
        "BINDING_MISMATCH",
    ),
    (
        "comparison-unknown-rank",
        _set("comparison/ranking", ["FIXTURE-CAND-A", "FIXTURE-CAND-Z"]),
        "UNKNOWN_CANDIDATE",
    ),
]


def _reject(doc: Doc, code: str) -> None:
    with pytest.raises(PlanError) as caught:
        RecoveryPlan.from_wire(doc)
    assert caught.value.code == code


@pytest.mark.parametrize(
    ("change", "code"),
    [(c, k) for _, c, k in STRUCTURAL],
    ids=[n for n, _, _ in STRUCTURAL],
)
def test_structural_defects_are_rejected(change: Change, code: str) -> None:
    _reject(redigest(mutated(plan_doc(), change)), code)


@pytest.mark.parametrize(
    ("change", "code"),
    [(c, k) for _, c, k in SEMANTIC],
    ids=[n for n, _, _ in SEMANTIC],
)
def test_cross_field_defects_are_rejected_even_with_a_matching_digest(
    change: Change, code: str
) -> None:
    _reject(redigest(mutated(plan_doc(), change)), code)


@pytest.mark.parametrize(
    ("change", "code"),
    [(c, k) for _, c, k in VALIDITY],
    ids=[n for n, _, _ in VALIDITY],
)
def test_validity_report_defects_are_rejected(change: Change, code: str) -> None:
    _reject(redigest(mutated(plan_doc(VALID), change)), code)


@pytest.mark.parametrize(
    "text",
    [
        '{"a":1,"a":2}',
        '{"weight": NaN}',
        '{"weight": Infinity}',
        '{"weight": 1e999}',
        "",
        "[]",
    ],
)
def test_strict_json_for_plans(text: str) -> None:
    with pytest.raises(PlanError):
        RecoveryPlan.from_json(text)


def _leaves(node: Any, path: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
    if isinstance(node, dict):
        return [p for k, v in node.items() for p in _leaves(v, (*path, k))]
    if isinstance(node, list):
        return [p for i, v in enumerate(node) for p in _leaves(v, (*path, i))]
    return [path]


def _tweak(value: Any) -> Any:
    if isinstance(value, bool) or value is None:
        return "x"
    if isinstance(value, int):
        return value + 1
    if isinstance(value, float):
        return value + 0.5
    return value + "x"


@pytest.mark.parametrize("name", ["recovery-plan.v1.json", VALID])
def test_every_single_leaf_mutation_is_rejected_or_changes_the_digest(
    name: str,
) -> None:
    original = plan_doc(name)
    digest = RecoveryPlan.from_wire(original).content_digest
    paths = _leaves(original)
    assert len(paths) > 100
    for path in paths:
        doc = copy.deepcopy(original)
        node: Any = doc
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = _tweak(node[path[-1]])
        # 1. a tampered document keeps its old digest: always refused
        with pytest.raises(PlanError):
            RecoveryPlan.from_wire(doc)
        # 2. a re-digested one is either refused or a different proposal
        if path == ("content_digest",):
            continue  # the digest field is what a re-digest rewrites
        try:
            decoded = RecoveryPlan.from_wire(redigest(doc))
        except PlanError:
            continue
        assert decoded.content_digest != digest, path


def test_decoded_plan_is_immutable_and_detached_from_the_caller_document() -> None:
    doc = plan_doc()
    plan = RecoveryPlan.from_wire(doc)
    doc[CAND][0]["assignments"][0]["lot_id"] = "tampered"
    assert plan.candidate_schedules[0].assignments[0].lot_id == "LOT-001"
    with pytest.raises(dataclasses.FrozenInstanceError):
        plan.world_id = "OTHER"  # type: ignore[misc]
    assert isinstance(plan.candidate_schedules, tuple)
    assert isinstance(plan.candidate_schedules[0].assignments, tuple)
    wire = plan.to_wire()
    wire[CAND].clear()
    assert len(plan.to_wire()[CAND]) == 2  # serialization hands out fresh copies


def test_digest_changes_with_material_content_only() -> None:
    plan = RecoveryPlan.from_wire(plan_doc())
    moved = replace(plan, incident_id="FIXTURE-INCIDENT-002")
    assert moved.content_digest != plan.content_digest
    assert replace(plan).content_digest == plan.content_digest


def test_integer_and_float_spellings_are_distinct_content() -> None:
    doc = plan_doc(VALID)
    other = mutated(doc, _set(f"{CAND}/0/predicted_objectives/1/value", 0.0))
    assert redigest(other)["content_digest"] != doc["content_digest"]


# --- binding to the consumed snapshot ---------------------------------------------


def test_fixture_binds_to_the_published_snapshot_without_assessing_feasibility() -> (
    None
):
    plan = RecoveryPlan.from_wire(plan_doc())
    result = check_snapshot_binding(plan, parsed_snapshot())
    assert result.plan_digest == plan.content_digest
    assert (result.world_id, result.snapshot_revision) == ("PRIMARY", "twin-rev-184202")
    assert result.feasibility_assessed is False


def _rename_equipment(doc: Doc) -> None:
    doc["equipment"][0]["id"] = "CNC-5AX-09"
    for lot in doc["lots"]:
        lot["eligible_equipment_ids"] = [
            "CNC-5AX-09" if item == "CNC-5AX-07" else item
            for item in lot["eligible_equipment_ids"]
        ]


SNAPSHOT_CHANGES: list[tuple[str, Change, str]] = [
    ("revision", _set("snapshot_revision", "twin-rev-184203"), "BINDING_MISMATCH"),
    ("generated", _set("generated_at", "2026-10-27T08:00:01Z"), "BINDING_MISMATCH"),
    ("schedule", _set("current_schedule_version", "schedule-v20"), "BINDING_MISMATCH"),
    ("no-schedule", _set("current_schedule_version", None), "BINDING_MISMATCH"),
    ("lot-revision", _set("lots/0/revision", "lot-rev-12"), "BINDING_MISMATCH"),
    (
        "lot-visit",
        _set("lots/0/route_position/visit_id", "VISIT-A-04"),
        "BINDING_MISMATCH",
    ),
    (
        "lot-route",
        _set("lots/1/route_position/route_id", "ROUTE-C"),
        "BINDING_MISMATCH",
    ),
    ("lot-position", _set("lots/1/route_position/position", 1), "BINDING_MISMATCH"),
    (
        "equipment-revision",
        _set("equipment/0/revision", "equipment-rev-8"),
        "BINDING_MISMATCH",
    ),
    ("lot-gone", _set("lots/1/id", "LOT-009"), "UNKNOWN_REFERENCE"),
    ("equipment-gone", _rename_equipment, "UNKNOWN_REFERENCE"),
]


def test_plan_refuses_a_snapshot_of_another_world() -> None:
    other = parsed_snapshot()
    other = replace(other, world_id="COUNTERFACTUAL-1")
    with pytest.raises(PlanError) as caught:
        check_snapshot_binding(RecoveryPlan.from_wire(plan_doc()), other)
    assert (caught.value.code, caught.value.path) == ("BINDING_MISMATCH", "/world_id")


@pytest.mark.parametrize(
    ("change", "code"),
    [(c, k) for _, c, k in SNAPSHOT_CHANGES],
    ids=[n for n, _, _ in SNAPSHOT_CHANGES],
)
def test_any_drift_of_a_cited_snapshot_fact_breaks_the_binding(
    change: Change, code: str
) -> None:
    drifted = parsed_snapshot(mutated(snapshot_doc(), change))
    with pytest.raises(PlanError) as caught:
        check_snapshot_binding(RecoveryPlan.from_wire(plan_doc()), drifted)
    assert caught.value.code == code


def test_reentrant_visit_identity_is_part_of_the_binding() -> None:
    def second_visit(doc: Doc) -> None:
        extra = copy.deepcopy(doc["lots"][0])
        extra.update(id="LOT-003")
        extra["route_position"].update(visit_id="VISIT-A-01", position=0)
        doc["lots"].append(extra)

    snap = parsed_snapshot(mutated(snapshot_doc(), second_visit))
    plan = RecoveryPlan.from_wire(plan_doc())
    check_snapshot_binding(plan, snap)  # LOT-001 is still cited at VISIT-A-03

    def flattened(doc: Doc) -> None:
        for item in doc[CAND][0]["assignments"][:1]:
            item["visit_id"] = (
                "VISIT-A-01"  # same route and operation class, other visit
            )

    wrong = RecoveryPlan.from_wire(redigest(mutated(plan_doc(), flattened)))
    with pytest.raises(PlanError) as caught:
        check_snapshot_binding(wrong, snap)
    assert caught.value.code == "BINDING_MISMATCH"


@settings(max_examples=60, derandomize=True, deadline=None)
@given(
    revisions=st.lists(
        st.text(alphabet="abcdef0123456789-", min_size=1, max_size=12),
        min_size=4,
        max_size=4,
        unique=True,
    ),
    victim=st.integers(min_value=0, max_value=3),
)
def test_binding_holds_for_exact_revisions_and_breaks_for_any_other(
    revisions: list[str], victim: int
) -> None:
    lot_a, lot_b, eq_a, eq_b = revisions

    def with_revisions(doc: Doc) -> None:
        doc["lots"][0]["revision"], doc["lots"][1]["revision"] = lot_a, lot_b
        doc["equipment"][0]["revision"], doc["equipment"][1]["revision"] = eq_a, eq_b

    def plan_with(doc: Doc) -> RecoveryPlan:
        out = copy.deepcopy(plan_doc())
        out["affected_material"][0]["lot_revision"] = lot_a
        out["affected_material"][1]["lot_revision"] = lot_b
        out["affected_equipment"][0]["equipment_revision"] = eq_a
        for item in out[CAND][0]["assignments"] + out[CAND][1]["assignments"]:
            if item["lot_id"] == "LOT-001":
                item["lot_revision"] = lot_a
            else:
                item["lot_revision"] = lot_b
            item["equipment_revision"] = (
                eq_a if item["equipment_id"] == "CNC-5AX-07" else eq_b
            )
        return RecoveryPlan.from_wire(redigest(out))

    base = mutated(snapshot_doc(), with_revisions)
    plan = plan_with(base)
    check_snapshot_binding(plan, parsed_snapshot(base))
    drift = mutated(
        base,
        lambda d: (d["lots"] + d["equipment"])[victim].update(
            revision="drifted-revision"
        ),
    )
    with pytest.raises(PlanError):
        check_snapshot_binding(plan, parsed_snapshot(drift))


# --- producer path -----------------------------------------------------------------


def _inputs() -> tuple[Any, PlanHeader, tuple[Candidate, ...]]:
    plan = RecoveryPlan.from_wire(plan_doc())
    header = PlanHeader(
        plan.recovery_plan_id,
        plan.incident_id,
        plan.generated_at,
        plan.valid_until,
        plan.generation,
        plan.affected_material,
        plan.affected_equipment,
        plan.assumptions,
        plan.objective_profile,
        plan.recommended_candidate_id,
    )
    return to_planning_input(parsed_snapshot()), header, plan.candidate_schedules


def test_producer_path_rebuilds_the_fixture_exactly_and_marks_nothing_validated() -> (
    None
):
    planning_input, header, candidates = _inputs()
    built = propose_recovery_plan(planning_input, header, candidates, now=NOW)
    assert built.to_wire() == plan_doc()
    assert all(
        c.validation_result.status is ValidationStatus.NOT_RUN
        for c in built.candidate_schedules
    )


def test_producer_path_refuses_to_manufacture_validity() -> None:
    planning_input, header, candidates = _inputs()
    claim = ValidationResult(
        ValidationStatus.REPORTED_VALID,
        Validator("V", "1"),
        "REF",
        (),
        ValidationBinding("PRIMARY", "twin-rev-184202", candidates[0].candidate_id),
    )
    claimed = (replace(candidates[0], validation_result=claim), candidates[1])
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(planning_input, header, claimed, now=NOW)
    assert caught.value.code == "VALIDITY_CLAIM_REJECTED"


def test_producer_path_requires_a_normal_snapshot() -> None:
    _, header, candidates = _inputs()
    doc = mutated(snapshot_doc(), _set("freshness/status", "STALE"))
    diagnostic = parse_snapshot(
        doc,
        expected_world_id="PRIMARY",
        policy=policy(NOW, FreshnessMode.DIAGNOSTIC),
    )
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(
            to_planning_input(diagnostic), header, candidates, now=NOW
        )
    assert caught.value.code == "SNAPSHOT_NOT_USABLE"


def test_producer_path_rejects_candidates_for_unknown_or_drifted_material() -> None:
    planning_input, header, candidates = _inputs()
    ghost = replace(candidates[0].assignments[0], lot_id="LOT-009")
    bad = replace(candidates[0], assignments=(ghost, *candidates[0].assignments[1:]))
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(planning_input, header, (bad, candidates[1]), now=NOW)
    assert caught.value.code == "UNKNOWN_REFERENCE"
    stale_header = replace(
        header,
        affected_equipment=(AffectedEquipment("CNC-5AX-07", "equipment-rev-6"),),
    )
    with pytest.raises(PlanError) as drift:
        propose_recovery_plan(planning_input, stale_header, candidates, now=NOW)
    assert drift.value.code == "BINDING_MISMATCH"
    moved = replace(
        header,
        affected_material=(
            AffectedMaterial("LOT-001", "lot-rev-11", "ROUTE-A", "VISIT-A-03", 1),
        ),
    )
    with pytest.raises(PlanError):
        propose_recovery_plan(planning_input, moved, candidates, now=NOW)


def test_producer_output_is_detached_from_the_callers_candidate_list() -> None:
    planning_input, header, candidates = _inputs()
    mutable = list(candidates)
    built = propose_recovery_plan(planning_input, header, mutable, now=NOW)
    mutable.clear()
    assert len(built.candidate_schedules) == 2
    assert isinstance(built.candidate_schedules, tuple)
    assert isinstance(built.candidate_schedules[0].assignments[0], Assignment)


# --- R1: current freshness at the construction boundary ------------------------------


def _at(delta: timedelta) -> datetime:
    return datetime(2026, 10, 27, 8, 5, tzinfo=UTC) + delta  # snapshot valid_until


def test_construction_accepts_fresh_input_up_to_but_excluding_expiry() -> None:
    planning_input, header, candidates = _inputs()
    propose_recovery_plan(planning_input, header, candidates, now=NOW)
    propose_recovery_plan(
        planning_input, header, candidates, now=_at(-timedelta(microseconds=1))
    )
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(planning_input, header, candidates, now=_at(timedelta(0)))
    assert (caught.value.code, caught.value.path) == (
        "SNAPSHOT_EXPIRED",
        "/source_snapshot",
    )


def test_a_retained_normal_snapshot_does_not_prove_current_freshness() -> None:
    planning_input, header, candidates = _inputs()
    assert planning_input.snapshot.usability.value == "NORMAL"  # parsed at NOW
    late = replace(
        header,
        generated_at=_at(timedelta(seconds=1)),
        valid_until=_at(timedelta(hours=1)),
    )
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(
            planning_input, late, candidates, now=_at(timedelta(seconds=1))
        )
    assert caught.value.code == "SNAPSHOT_EXPIRED"


@pytest.mark.parametrize("offset", [timedelta(0), timedelta(seconds=1)])
def test_plan_may_not_be_generated_at_or_after_source_expiry(offset: timedelta) -> None:
    planning_input, header, candidates = _inputs()
    late = replace(
        header, generated_at=_at(offset), valid_until=_at(offset + timedelta(hours=1))
    )
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(planning_input, late, candidates, now=NOW)
    assert (caught.value.code, caught.value.path) == (
        "PLAN_AFTER_SOURCE_EXPIRY",
        "/generated_at",
    )


def test_construction_rejects_a_clock_before_the_snapshot_existed() -> None:
    planning_input, header, candidates = _inputs()
    early = datetime(2026, 10, 27, 7, 59, tzinfo=UTC)
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(planning_input, header, candidates, now=early)
    assert caught.value.code == "SNAPSHOT_FROM_FUTURE"


@pytest.mark.parametrize(
    "now",
    [
        datetime(2026, 10, 27, 8, 1),
        datetime(2026, 10, 27, 11, 1, tzinfo=timezone(timedelta(hours=3))),
        "2026-10-27T08:01:00Z",
        None,
    ],
)
def test_construction_clock_must_be_explicit_aware_utc(now: Any) -> None:
    planning_input, header, candidates = _inputs()
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(planning_input, header, candidates, now=now)
    assert caught.value.code == "NOW_NOT_AWARE_UTC"


def test_historical_plans_still_decode_without_any_clock() -> None:
    RecoveryPlan.from_wire(plan_doc())  # decoding is not a current act


# --- R2: oversized integers stay inside the declared failure interface ---------------

NUMBER_FIELDS = [
    "objective_profile/terms/0/weight",
    f"{CAND}/0/solve/wall_time_ms",
    f"{CAND}/0/predicted_objectives/0/value",
]


@pytest.mark.parametrize("path", NUMBER_FIELDS)
@pytest.mark.parametrize(
    "value", [10**400, -(10**400), 2**53, -(2**53), True, False, "1"]
)
def test_unsafe_numbers_are_plan_errors_on_the_public_paths(
    path: str, value: Any
) -> None:
    doc = redigest(mutated(plan_doc(VALID), _set(path, value)))
    with pytest.raises(PlanError) as wired:
        RecoveryPlan.from_wire(doc)
    assert wired.value.code == "NUMBER_INVALID"
    with pytest.raises(PlanError) as text:
        RecoveryPlan.from_json(json.dumps(doc))
    assert text.value.code == "NUMBER_INVALID"


@pytest.mark.parametrize("path", NUMBER_FIELDS)
@pytest.mark.parametrize("value", [0, 1, 2**53 - 1, 2.5, 0.0])
def test_ordinary_numbers_still_decode(path: str, value: Any) -> None:
    doc = redigest(mutated(plan_doc(VALID), _set(path, value)))
    plan = RecoveryPlan.from_wire(doc)
    assert RecoveryPlan.from_json(json.dumps(doc)) == plan


def test_a_float_that_overflows_is_rejected_at_the_json_boundary() -> None:
    text = json.dumps(plan_doc(VALID)).replace('"weight": 1.0', '"weight": 1e400', 1)
    assert "1e400" in text
    with pytest.raises(PlanError) as caught:
        RecoveryPlan.from_json(text)
    assert caught.value.code == "JSON_INVALID"


def test_construction_does_not_trust_an_inconsistent_normal_label() -> None:
    planning_input, header, candidates = _inputs()
    forged = replace(
        planning_input.snapshot, freshness_status=FreshnessStatus.STALE
    )  # label says NORMAL, status says STALE
    with pytest.raises(PlanError) as caught:
        propose_recovery_plan(
            replace(planning_input, snapshot=forged), header, candidates, now=NOW
        )
    assert caught.value.code == "SNAPSHOT_NOT_USABLE"
