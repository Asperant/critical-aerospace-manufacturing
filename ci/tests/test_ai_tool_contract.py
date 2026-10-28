"""Bounded typed AI tool contract slice for WP-AI-002 / DEP-064."""

import json
from pathlib import Path

import pytest
from cap_contracts.boundary import BoundaryValidator, ContractViolation
from cap_contracts.registry import Registry

ROOT = Path(__file__).parents[2]
REGISTRY = Registry.load(ROOT / "packages/contracts/registry")
DECLARATION = REGISTRY.get("ai.tool-interface.v1")
FIXTURE_DIR = ROOT / "services/ai-intelligence/contracts/v1"


def fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    "name",
    [
        "ai-tool.core-order-read.json",
        "ai-tool.twin-snapshot-read.json",
        "ai-tool.simulate-recovery.json",
        "ai-tool.propose-recovery.json",
    ],
)
def test_allowlisted_tools_validate_as_producer_and_consumer(name: str) -> None:
    validator = BoundaryValidator(DECLARATION, ROOT)
    payload = fixture(name)
    validator.validate(payload, role="producer")
    validator.validate(payload, role="consumer")


def test_tool_contract_rejects_unknown_surface_and_authority_escalation() -> None:
    validator = BoundaryValidator(DECLARATION, ROOT)
    payload = fixture("ai-tool.propose-recovery.json")
    payload["authority"] = "EXECUTE"
    with pytest.raises(ContractViolation):
        validator.validate(payload, role="consumer")

    payload = fixture("ai-tool.core-order-read.json")
    payload["tool_id"] = "shell.exec"
    with pytest.raises(ContractViolation):
        validator.validate(payload, role="producer")


def test_allowlist_has_no_mutation_or_arbitrary_query_surface() -> None:
    allowlist = DECLARATION.semantics["allowlist"]
    assert {item.rsplit(":", 1)[1] for item in allowlist.split(", ")} == {
        "READ",
        "SIMULATE",
        "PROPOSE",
    }
    assert all(
        "shell" not in item and "sql" not in item for item in allowlist.split(", ")
    )


def test_schema_declares_all_four_authority_surfaces() -> None:
    schema = json.loads(
        (
            ROOT
            / "services/ai-intelligence/contracts/v1/ai-tool-interface.v1.schema.json"
        ).read_text()
    )
    assert set(schema["$defs"]) == {
        "CoreOrderRead",
        "TwinSnapshotRead",
        "SimulateRecovery",
        "ProposeRecovery",
    }
