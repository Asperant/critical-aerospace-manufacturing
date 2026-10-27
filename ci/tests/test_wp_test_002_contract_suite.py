"""TEST-TEST-002-001: current-main consumer contract suite for DEP-021."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from cap_contracts import BoundaryValidator, ContractViolation, Registry

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "packages/contracts/registry"
FIXTURES = ROOT / "services/manufacturing-core/contracts/v1"
CONTRACT_ID = "core.order-query.v1"


def validator() -> BoundaryValidator:
    registry = Registry.load(REGISTRY)
    registry.verify(ROOT)
    return BoundaryValidator(registry.get(CONTRACT_ID), ROOT)


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
