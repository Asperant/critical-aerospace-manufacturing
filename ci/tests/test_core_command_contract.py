import copy
import json
from pathlib import Path

import pytest

from cap_contracts.boundary import BoundaryValidator, ContractViolation
from cap_contracts.compatibility import compare_schemas
from cap_contracts.registry import Registry

ROOT = Path(__file__).parents[2]
REGISTRY = Registry.load(ROOT / "packages/contracts/registry")
DECLARATION = REGISTRY.get("core.operational-command.v1")


def fixture(name: str) -> dict[str, object]:
    return json.loads(
        (ROOT / "services/manufacturing-core/contracts/v1" / name).read_text()
    )


def test_core_command_producer_and_consumer_boundaries_accept_all_v1_fixtures() -> None:
    validator = BoundaryValidator(DECLARATION, ROOT)
    for name in (
        "operational-command.place-hold.json",
        "operational-command.release-hold.json",
        "operational-command.dispatch.json",
        "operational-command.maintenance.json",
    ):
        payload = fixture(name)
        validator.validate(payload, role="producer")
        validator.validate(payload, role="consumer")


def test_core_command_boundary_rejects_unknown_version_and_missing_world() -> None:
    validator = BoundaryValidator(DECLARATION, ROOT)
    payload = fixture("operational-command.place-hold.json")
    payload["command_version"] = 2
    with pytest.raises(ContractViolation):
        validator.validate(payload, role="consumer")
    payload = fixture("operational-command.place-hold.json")
    del payload["world_id"]
    with pytest.raises(ContractViolation):
        validator.validate(payload, role="producer")


def test_core_command_breaking_schema_change_requires_new_major() -> None:
    old = {"type": "object", "properties": {"command_id": {"type": "string"}}}
    new = copy.deepcopy(old)
    new["required"] = ["command_id"]
    result = compare_schemas(old, new)
    assert result.breaking
    assert not result.compatible
