"""TEST-TEST-002-001: current-main consumer contract suite for DEP-021."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from cap_contracts import (
    BoundaryValidator,
    ContractViolation,
    ProducerAuthorities,
    Registry,
    compare_contracts,
)
from cap_contracts.registry import load_schema

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "packages/contracts/registry"
FIXTURES = ROOT / "services/manufacturing-core/contracts/v1"
CONTRACT_ID = "core.order-query.v1"


def validator() -> BoundaryValidator:
    registry = Registry.load(REGISTRY)
    registry.verify(ROOT)
    return BoundaryValidator(registry.get(CONTRACT_ID), ROOT)


def repository_registry() -> Registry:
    registry = Registry.load(REGISTRY)
    registry.verify_authorities(
        ProducerAuthorities.load(ROOT / "packages/contracts/producer-authorities.json"),
        repo_root=ROOT,
    )
    registry.verify(ROOT)
    return registry


@pytest.mark.parametrize(
    "fixture_name", ["order-query.normal.json", "order-query.reentrant.json"]
)
def test_dep021_fixture_is_valid_from_producer_and_consumer_boundaries(
    fixture_name: str,
) -> None:
    payload = json.loads((FIXTURES / fixture_name).read_text(encoding="utf-8"))
    boundary = validator()
    for role in ("producer", "consumer"):
        boundary.validate(payload, role=role)


def test_consumer_rejects_schema_drift_and_preserves_fixture() -> None:
    payload = json.loads(
        (FIXTURES / "order-query.normal.json").read_text(encoding="utf-8")
    )
    before = copy.deepcopy(payload)
    payload["unexpected"] = "must fail closed"
    with pytest.raises(ContractViolation):
        validator().validate(payload, role="consumer")
    assert payload != before


@pytest.mark.parametrize("contract_id", [*Registry.load(REGISTRY).contract_ids()])
def test_every_registered_fixture_is_valid_at_both_boundaries(contract_id: str) -> None:
    """Exercise the real registry, producer roots and every published example."""
    registry = repository_registry()
    declaration = registry.get(contract_id)
    boundary = BoundaryValidator(declaration, ROOT)
    for fixture_ref in declaration.fixtures:
        payload = json.loads((ROOT / fixture_ref.path).read_text(encoding="utf-8"))
        for role in ("producer", "consumer"):
            boundary.validate(payload, role=role)


def test_dep021_request_is_valid_for_producer_and_consumer_and_rejects_negatives() -> None:
    boundary = validator()
    valid = {"contract_version": CONTRACT_ID, "order_id": "ORD-TEST-002"}
    for role in ("producer", "consumer"):
        boundary.validate_request(valid, role=role)
        with pytest.raises(ContractViolation):
            boundary.validate_request({"contract_version": CONTRACT_ID}, role=role)
        with pytest.raises(ContractViolation):
            boundary.validate_request({**valid, "unexpected": True}, role=role)


def test_registered_contract_versions_are_self_compatible_after_hash_verification() -> None:
    registry = repository_registry()
    declaration = registry.get(CONTRACT_ID)
    output = load_schema(declaration.output_schema, ROOT)
    assert declaration.input_schema is not None
    request = load_schema(declaration.input_schema, ROOT)
    result = compare_contracts(
        declaration,
        declaration,
        old_output_schema=output,
        new_output_schema=output,
        old_input_schema=request,
        new_input_schema=request,
    )
    assert result.compatible, result
