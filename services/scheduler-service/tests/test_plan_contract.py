"""Registered contract: producer and consumer roles, schema/decoder parity, authority.

The JSON Schema checks structure only. The decoder additionally enforces cross-field
rules and the content digest, and neither establishes feasibility, validity or
approval: the separation probe below models what a consumer must still require.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import manufacturing_scheduler
import pytest
from cap_contracts.boundary import BoundaryValidator, ContractViolation
from cap_contracts.registry import Registry
from manufacturing_scheduler import plans, snapshot
from manufacturing_scheduler.errors import PlanError
from manufacturing_scheduler.plans import (
    RecoveryPlan,
    ValidationStatus,
    check_snapshot_binding,
)
from plan_helpers import PLAN_DIR, ROOT, Doc, load, mutated, parsed_snapshot, plan_doc

DECLARATION = Registry.load(ROOT / "packages/contracts/registry").get(
    "scheduler.recovery-plan.v1"
)
VALIDATOR = BoundaryValidator(DECLARATION, ROOT)
FIXTURES = ["recovery-plan.v1.json", "recovery-plan.self-reported-valid.json"]
CAND = "candidate_schedules"


def test_declaration_matches_the_registered_producer_and_authority() -> None:
    assert DECLARATION.canonical_producer == "scheduler-service"
    assert DECLARATION.semantic_owner == "Batuhan Kaya"
    assert DECLARATION.contract_type == "ARTIFACT"
    assert set(DECLARATION.declared_consumers) == {
        "Automation",
        "HITL",
        "Command Center",
    }
    assert "approval, activation or execution authority" in DECLARATION.authority_level
    Registry.load(ROOT / "packages/contracts/registry").verify(ROOT)


@pytest.mark.parametrize("name", FIXTURES)
def test_fixtures_validate_as_producer_and_consumer_and_decode(name: str) -> None:
    doc = load(PLAN_DIR / name)
    VALIDATOR.validate(doc, role="producer")
    VALIDATOR.validate(doc, role="consumer")
    assert RecoveryPlan.from_wire(doc).generation.kind.value == "DEVELOPMENT_FIXTURE"


def _set(path: str, value: Any) -> Callable[[Doc], None]:
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


def _drop(path: str) -> Callable[[Doc], None]:
    def apply(doc: Doc) -> None:
        node: Any = doc
        keys = path.split("/")
        for key in keys[:-1]:
            node = node[int(key)] if isinstance(node, list) else node[key]
        del node[keys[-1]]

    return apply


#: Defects the schema can express: schema and decoder must both refuse them.
SHARED = [
    _set("contract_version", "scheduler.recovery-plan.v2"),
    _set("execution_eligible", True),
    _set("approved", True),
    _set(f"{CAND}/0/validation_result/certified", True),
    _drop("rationale"),
    _drop(f"{CAND}/0/solve/wall_time_ms"),
    _set("world_id", ""),
    _set("incident_id", "has space"),
    _set("generated_at", "2026-10-27T08:01:00"),
    _set("generated_at", "2026-10-27T08:01:00+00:00"),
    _set("generated_at", "2026-10-27T08:01:00.50Z"),
    _set("generation/kind", "OPERATIONAL"),
    _set("objective_profile/terms", []),
    _set(CAND, []),
    _set("objective_profile/terms/0/weight", -1),
    _set("objective_profile/terms/0/weight", True),
    _set(f"{CAND}/0/solve/status", "OPTIMAL"),
    _set(f"{CAND}/0/predicted_objectives/0/status", "COMPUTED"),
    _set(f"{CAND}/0/predicted_objectives/0/value", 3),
    _set(f"{CAND}/0/stability/moved_assignment_count", 2),
    _set(f"{CAND}/0/counterfactual/status", "AVAILABLE"),
    _set(f"{CAND}/0/validation_result/status", "REPORTED_VALID"),
    _set("comparison/ranking", ["FIXTURE-CAND-A"]),
    _set("rationale/summary", "A claim without a trace."),
    _set("content_digest", "sha256:XYZ"),
    _set("affected_material/0/position", -1),
]

#: Facts only the decoder (cross-field rules, digest) can enforce.
DECODER_ONLY = [
    _set("recommended_candidate_id", "FIXTURE-CAND-Z"),
    _set(f"{CAND}/1/candidate_id", "FIXTURE-CAND-A"),
    _set(f"{CAND}/0/assignments/0/end_at", "2026-10-27T08:00:00Z"),
    _set(f"{CAND}/0/assignments/1/end_at", "2026-10-27T21:00:00Z"),
    _set(f"{CAND}/0/predicted_objectives/0/unit", "hour"),
    _set("valid_until", "2026-10-27T08:00:00Z"),
    _set("incident_id", "FIXTURE-INCIDENT-9"),  # stale digest: tampered content
    _set("world_id", "COUNTERFACTUAL-1"),  # still schema-valid, different proposal
]


@pytest.mark.parametrize("change", SHARED)
def test_schema_and_decoder_both_refuse_structural_defects(
    change: Callable[[Doc], None],
) -> None:
    doc = mutated(plan_doc(), change)
    with pytest.raises(ContractViolation):
        VALIDATOR.validate(doc, role="consumer")
    with pytest.raises(PlanError):
        RecoveryPlan.from_wire(doc)


@pytest.mark.parametrize("change", DECODER_ONLY)
def test_schema_success_is_not_authenticity_or_consistency(
    change: Callable[[Doc], None],
) -> None:
    doc = mutated(plan_doc(), change)
    VALIDATOR.validate(doc, role="consumer")  # structurally fine ...
    with pytest.raises(PlanError):  # ... yet not an acceptable proposal
        RecoveryPlan.from_wire(doc)


def test_fixture_sibling_is_discovered_by_the_contract_tier_function() -> None:
    from check_contracts import check_schema_file

    errors, instance_checked = check_schema_file(
        PLAN_DIR / "recovery-plan.v1.schema.json"
    )
    assert errors == [] and instance_checked is True


def test_schema_has_no_activation_approval_or_execution_field() -> None:
    def names(node: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "properties":
                    found |= set(value)
                found |= names(value)
        elif isinstance(node, list):
            for value in node:
                found |= names(value)
        return found

    schema = json.loads((PLAN_DIR / "recovery-plan.v1.schema.json").read_text("utf-8"))
    forbidden = ("approv", "activ", "execut", "eligib", "authoriz")
    assert not [n for n in names(schema) if any(word in n for word in forbidden)]
    assert not [
        n
        for module in (manufacturing_scheduler, plans, snapshot)
        for n in dir(module)
        if not n.startswith("_") and any(word in n.lower() for word in forbidden[:3])
    ]


# --- planner is not validator: a consumer probe ---------------------------------------


@dataclass(frozen=True)
class IndependentValidation:
    """What a consumer must obtain from the validator, outside the plan document."""

    validator_id: str
    world_id: str
    snapshot_revision: str
    candidate_id: str
    plan_digest: str
    passed: bool


def consumer_admits(
    plan: RecoveryPlan,
    candidate_id: str,
    independent: IndependentValidation | None,
    trusted_validators: frozenset[str],
) -> bool:
    """Development model of the documented Automation/HITL precondition (not product)."""

    if independent is None or independent.validator_id not in trusted_validators:
        return False
    return independent.passed and (
        independent.world_id,
        independent.snapshot_revision,
        independent.candidate_id,
        independent.plan_digest,
    ) == (
        plan.world_id,
        plan.source_snapshot.snapshot_revision,
        candidate_id,
        plan.content_digest,
    )


def test_self_reported_validity_never_authorizes_a_consumer() -> None:
    plan = RecoveryPlan.from_wire(plan_doc("recovery-plan.self-reported-valid.json"))
    candidate = plan.recommended
    assert candidate.validation_result.status is ValidationStatus.REPORTED_VALID
    check_snapshot_binding(
        plan, parsed_snapshot()
    )  # identity binds; feasibility unknown
    trusted = frozenset({"independent-validator"})
    assert not consumer_admits(plan, candidate.candidate_id, None, trusted)
    claimed = IndependentValidation(
        "FIXTURE-NOT-A-VALIDATOR",
        plan.world_id,
        plan.source_snapshot.snapshot_revision,
        candidate.candidate_id,
        plan.content_digest,
        True,
    )
    assert not consumer_admits(plan, candidate.candidate_id, claimed, trusted)


def test_an_independent_validation_must_bind_world_revision_candidate_and_content() -> (
    None
):
    plan = RecoveryPlan.from_wire(plan_doc())
    cid = plan.recommended_candidate_id
    base = IndependentValidation(
        "independent-validator",
        plan.world_id,
        plan.source_snapshot.snapshot_revision,
        cid,
        plan.content_digest,
        True,
    )
    trusted = frozenset({"independent-validator"})
    assert consumer_admits(plan, cid, base, trusted)  # the probe's positive control
    for field, wrong in [
        ("world_id", "COUNTERFACTUAL-1"),
        ("snapshot_revision", "twin-rev-1"),
        ("candidate_id", "FIXTURE-CAND-B"),
        ("plan_digest", "sha256:" + "0" * 64),
        ("passed", False),
    ]:
        assert not consumer_admits(
            plan, cid, IndependentValidation(**{**base.__dict__, field: wrong}), trusted
        )
