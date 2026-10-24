"""TEST-EVT-001-008: exact names, no aliases, no semantic contract rename."""

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from cap_contracts import (
    ContractDeclaration,
    ContractError,
    ProducerAuthorities,
    Registry,
    parse_contract_id,
)
from cap_contracts.versioning import validate_producer_name

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "packages/contracts"


def record() -> dict[str, Any]:
    return json.loads((PACKAGE / "registry/core.order-query.v1.json").read_text())


def model() -> dict[str, Any]:
    return json.loads((PACKAGE / "producer-authorities.json").read_text())


@pytest.mark.parametrize(
    "contract_id", ["core.order-query.v1", "core.order-query.v12", "a.b.v2"]
)
def test_canonical_contract_id_round_trip(contract_id: str) -> None:
    parsed = parse_contract_id(contract_id)
    assert parsed.contract_id == contract_id
    assert contract_id == f"{parsed.family}.v{parsed.major}"


@pytest.mark.parametrize(
    "alias",
    [
        "Core.order-query.v1",
        "core.order_query.v1",
        "core.order-query.V1",
        "core.order-query.v01",
        "core.order-query.v0",
        " core.order-query.v1",
        "core.order-query.v1 ",
        "core.order-query",
    ],
)
def test_contract_id_aliases_are_rejected_without_normalization(alias: str) -> None:
    with pytest.raises(ContractError, match="CONTRACT_ID_INVALID"):
        parse_contract_id(alias)


@pytest.mark.parametrize("version", [2, "1", True])
def test_declaration_version_must_match_id_major(version: object) -> None:
    value = record()
    value["version"] = version
    with pytest.raises(ContractError, match="VERSION_MISMATCH"):
        ContractDeclaration.from_mapping(value)


def test_programmatic_registry_version_must_match_id_major() -> None:
    declaration = replace(ContractDeclaration.from_mapping(record()), version=2)
    with pytest.raises(ContractError, match="VERSION_MISMATCH"):
        Registry({declaration.contract_id: declaration})


@pytest.mark.parametrize("producer", ["manufacturing-core", "test-other", "worker2"])
def test_canonical_producer_name_is_preserved_exactly(producer: str) -> None:
    assert validate_producer_name(producer) == producer


@pytest.mark.parametrize(
    "alias",
    [
        "Manufacturing-Core",
        "MANUFACTURING-CORE",
        "manufacturing_core",
        "manufacturing core",
        " manufacturing-core",
        "manufacturing-core ",
        "manufacturing--core",
        "manufacturing-core-",
        "manufacturing.core",
        "manufacturing-cоre",
    ],
)
def test_producer_aliases_are_rejected_in_declarations_and_ownership_model(
    alias: str,
) -> None:
    value = record()
    value["canonical_producer"] = alias
    with pytest.raises(ContractError):
        ContractDeclaration.from_mapping(value)
    ownership = model()
    ownership["producers"][0]["producer"] = alias
    with pytest.raises(ContractError):
        ProducerAuthorities(ownership)


@pytest.mark.parametrize(
    "key", ["core.order-query", "Core.order-query.v1", "alias", "core.order-query.v2"]
)
def test_programmatic_registry_alias_key_is_rejected(key: str) -> None:
    declaration = ContractDeclaration.from_mapping(record())
    with pytest.raises(ContractError, match="REGISTRY_ID_MISMATCH"):
        Registry({key: declaration})


def test_duplicate_identity_hidden_by_different_mapping_keys_is_rejected() -> None:
    declaration = ContractDeclaration.from_mapping(record())
    with pytest.raises(ContractError, match="REGISTRY_ID_MISMATCH"):
        Registry(
            {
                declaration.contract_id: declaration,
                "alias": replace(declaration, canonical_producer="other"),
            }
        )


@pytest.mark.parametrize("field", ["contract_id", "canonical_producer", "version"])
def test_duplicate_json_identity_fields_are_rejected(
    tmp_path: Path, field: str
) -> None:
    value = record()
    raw = json.dumps(value)
    raw = raw[:-1] + "," + json.dumps(field) + ":" + json.dumps(value[field]) + "}"
    (tmp_path / "core.order-query.v1.json").write_text(raw)
    with pytest.raises(ContractError, match="DECLARATION_INVALID"):
        Registry.load(tmp_path)


def test_registry_filename_alias_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "alias.json").write_text(json.dumps(record()))
    with pytest.raises(ContractError, match="FILE_NAME_MISMATCH"):
        Registry.load(tmp_path)


def test_family_names_are_exact_and_not_inferred_from_producer_display_labels() -> None:
    value = model()
    value["producers"][0]["contracts"][0]["family"] = "manufacturing.core.order-query"
    with pytest.raises(ContractError, match="AUTHORITY_UNVERIFIABLE"):
        ProducerAuthorities(value).validate(ContractDeclaration.from_mapping(record()))


def test_duplicate_family_registration_stays_rejected() -> None:
    value = model()
    bindings = value["producers"][0]["contracts"]
    bindings.append(copy.deepcopy(bindings[0]))
    with pytest.raises(ContractError, match="PRODUCER_AUTHORITY_CONFLICT"):
        ProducerAuthorities(value)


def test_core_exemplar_names_authority_and_existing_hashes_remain_valid() -> None:
    registry = Registry.load(PACKAGE / "registry")
    declaration = registry.get("core.order-query.v1")
    assert declaration.parsed_id.family == "core.order-query"
    assert declaration.version == 1
    assert declaration.canonical_producer == "manufacturing-core"
    registry.verify_authorities(
        ProducerAuthorities.load(PACKAGE / "producer-authorities.json"), repo_root=REPO
    )
    registry.verify(REPO)


def test_programmatic_registry_rejects_noncanonical_producer_name() -> None:
    declaration = replace(
        ContractDeclaration.from_mapping(record()),
        canonical_producer="Manufacturing-Core",
    )
    with pytest.raises(ContractError, match="PRODUCER_NAME_INVALID"):
        Registry({declaration.contract_id: declaration})
