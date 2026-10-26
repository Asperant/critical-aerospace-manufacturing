"""TEST-EVT-SCHEMA: Core-owned domain-event payload contracts.

This is a producer/consumer boundary test over the versioned Core event
declarations. Envelope metadata is independently supplied by WP-EVT-002; no
broker, outbox or runtime consumer is exercised here.
"""

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from cap_contracts import BoundaryValidator, ContractViolation, ProducerAuthorities, Registry

REPO = Path(__file__).resolve().parents[2]
REGISTRY = Registry.load(REPO / "packages/contracts/registry")
AUTHORITIES = ProducerAuthorities.load(REPO / "packages/contracts/producer-authorities.json")

EVENTS = (
    "core.lot-held.v1",
    "core.lot-dispatch-authorized.v1",
)


def payload(contract_id: str) -> dict[str, Any]:
    declaration = REGISTRY.get(contract_id)
    fixture = declaration.fixtures[0].read(REPO)
    return json.loads(fixture)


def test_core_event_declarations_are_registered_and_owned() -> None:
    REGISTRY.verify_authorities(AUTHORITIES, repo_root=REPO)
    REGISTRY.verify(REPO)
    assert all(REGISTRY.get(contract_id).contract_type == "EVENT" for contract_id in EVENTS)
    assert all(REGISTRY.get(contract_id).sync_semantics == "ASYNC" for contract_id in EVENTS)
    assert REGISTRY.get("core.lot-held.v1").declared_consumers == (
        "Digital Twin",
        "Simulator",
        "Automation verification",
    )


@pytest.mark.parametrize("contract_id", EVENTS)
def test_producer_and_consumer_validate_the_same_twin_fixture(contract_id: str) -> None:
    declaration = REGISTRY.get(contract_id)
    validator = BoundaryValidator(declaration, REPO)
    fixture = payload(contract_id)
    validator.validate(fixture, role="producer")
    validator.validate(fixture, role="consumer")


@pytest.mark.parametrize("contract_id", EVENTS)
def test_event_payload_rejects_unknown_fields_at_both_boundaries(contract_id: str) -> None:
    declaration = REGISTRY.get(contract_id)
    validator = BoundaryValidator(declaration, REPO)
    invalid = copy.deepcopy(payload(contract_id))
    invalid["unapproved_field"] = "must fail closed"
    with pytest.raises(ContractViolation):
        validator.validate(invalid, role="producer")
    with pytest.raises(ContractViolation):
        validator.validate(invalid, role="consumer")


@pytest.mark.parametrize("contract_id", EVENTS)
def test_event_payload_requires_its_versioned_identity(contract_id: str) -> None:
    declaration = REGISTRY.get(contract_id)
    validator = BoundaryValidator(declaration, REPO)
    invalid = copy.deepcopy(payload(contract_id))
    del invalid["schema_version"]
    with pytest.raises(ContractViolation):
        validator.validate(invalid, role="producer")
