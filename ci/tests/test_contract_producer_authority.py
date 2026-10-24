"""TEST-EVT-001-007: registered producer authority, including the real Core exemplar."""

import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from cap_contracts import (
    ContractDeclaration,
    ContractError,
    FileRef,
    ProducerAuthorities,
    Registry,
)
from cap_contracts.ci_gate import check_versions

REPO = Path(__file__).resolve().parents[2]
MODEL = "packages/contracts/producer-authorities.json"
DECLARATION = "packages/contracts/registry/core.order-query.v1.json"


def model() -> dict[str, Any]:
    return json.loads((REPO / MODEL).read_text())


def record() -> dict[str, Any]:
    return json.loads((REPO / DECLARATION).read_text())


def declaration() -> ContractDeclaration:
    return ContractDeclaration.from_mapping(record())


def test_valid_registered_core_producer_passes_with_all_existing_hash_checks() -> None:
    registry = Registry.load(REPO / "packages/contracts/registry")
    registry.verify_authorities(ProducerAuthorities.load(REPO / MODEL), repo_root=REPO)
    registry.verify(REPO)


def test_unknown_producer_is_rejected_even_with_matching_authority_text() -> None:
    with pytest.raises(ContractError, match="PRODUCER_UNKNOWN"):
        ProducerAuthorities(model()).validate(
            replace(declaration(), canonical_producer="unregistered-service")
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("semantic_owner", "Other owner"),
        ("authority_level", "Execute protected manufacturing actions"),
        ("contract_type", "COMMAND"),
    ],
)
def test_producer_authority_metadata_mismatch_is_rejected(
    field: str, value: str
) -> None:
    with pytest.raises(ContractError, match="PRODUCER_AUTHORITY_MISMATCH"):
        ProducerAuthorities(model()).validate(replace(declaration(), **{field: value}))


@pytest.mark.parametrize("consumer", ["Simulator", "Digital Twin", "Scheduler"])
def test_consumer_cannot_claim_producer_authority(consumer: str) -> None:
    with pytest.raises(ContractError, match="CONSUMER_AUTHORITY_CLAIM"):
        ProducerAuthorities(model()).validate(
            replace(declaration(), canonical_producer=consumer)
        )


def test_consumer_cannot_evade_validation_by_removing_its_consumer_label() -> None:
    with pytest.raises(ContractError, match="PRODUCER_UNKNOWN"):
        ProducerAuthorities(model()).validate(
            replace(
                declaration(), canonical_producer="Scheduler", declared_consumers=()
            )
        )


def test_another_registered_producer_cannot_claim_core_family() -> None:
    value = model()
    other = copy.deepcopy(value["producers"][0])
    other.update(producer="test-other", source_roots=["services/test-other/contracts/"])
    other["contracts"][0]["family"] = "test.other"
    value["producers"].append(other)
    with pytest.raises(ContractError, match="PRODUCER_AUTHORITY_MISMATCH"):
        ProducerAuthorities(value).validate(
            replace(declaration(), canonical_producer="test-other")
        )


@pytest.mark.parametrize("field", ["input_schema", "output_schema", "fixtures"])
def test_foreign_package_files_cannot_masquerade_as_core_sources(field: str) -> None:
    foreign = FileRef("services/foreign/contracts/observation.json", "0" * 64)
    changed = replace(
        declaration(), **{field: (foreign,) if field == "fixtures" else foreign}
    )
    with pytest.raises(ContractError, match="PRODUCER_SOURCE_MISMATCH"):
        ProducerAuthorities(model()).validate(changed)


def test_producer_source_symlink_escape_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "services/manufacturing-core"
    root.mkdir(parents=True)
    foreign = tmp_path / "services/foreign/contracts"
    foreign.mkdir(parents=True)
    (root / "contracts").symlink_to(foreign, target_is_directory=True)
    with pytest.raises(ContractError, match="PRODUCER_SOURCE_MISMATCH"):
        ProducerAuthorities(model()).validate(declaration(), repo_root=tmp_path)


@pytest.mark.parametrize(
    "conflict",
    [
        "duplicate_producer",
        "conflicting_producer",
        "duplicate_family",
        "overlapping_roots",
    ],
)
def test_duplicate_or_conflicting_authority_is_rejected(conflict: str) -> None:
    value = model()
    other = copy.deepcopy(value["producers"][0])
    if conflict == "conflicting_producer":
        other["semantic_owner"] = "Other owner"
    elif conflict in {"duplicate_family", "overlapping_roots"}:
        other["producer"] = "test-other"
        if conflict == "duplicate_family":
            other["source_roots"] = ["services/test-other/contracts/"]
        else:
            other["source_roots"] = ["services/manufacturing-core/contracts/nested/"]
            other["contracts"][0]["family"] = "test.other"
    value["producers"].append(other)
    with pytest.raises(ContractError, match="PRODUCER_AUTHORITY_CONFLICT"):
        ProducerAuthorities(value)


@pytest.mark.parametrize(
    "invalid",
    [None, {}, {"schema_version": "cap-producer-authorities-v1", "producers": []}],
)
def test_missing_ownership_model_is_unverifiable(invalid: object) -> None:
    with pytest.raises(ContractError, match="AUTHORITY_MODEL_INVALID"):
        ProducerAuthorities(invalid)


@pytest.mark.parametrize("unknown", ["", "UNKNOWN", "TBD", None])
def test_unknown_registered_authority_fails_closed(unknown: object) -> None:
    value = model()
    value["producers"][0]["contracts"][0]["authority_level"] = unknown
    with pytest.raises(ContractError, match="AUTHORITY_MODEL_INVALID"):
        ProducerAuthorities(value)


def test_unregistered_family_has_no_inferred_authority() -> None:
    with pytest.raises(ContractError, match="AUTHORITY_UNVERIFIABLE"):
        ProducerAuthorities(model()).validate(
            replace(declaration(), contract_id="core.unregistered.v1")
        )


@pytest.mark.parametrize("value", [None, "", []])
def test_canonical_producer_must_be_explicit(value: object) -> None:
    data = record()
    data["canonical_producer"] = value
    with pytest.raises(ContractError):
        ContractDeclaration.from_mapping(data)


def test_missing_canonical_producer_is_rejected() -> None:
    data = record()
    data.pop("canonical_producer")
    with pytest.raises(ContractError, match="FIELD_MISSING"):
        ContractDeclaration.from_mapping(data)


def test_registration_is_not_mutated_by_later_caller_edits() -> None:
    value = model()
    authorities = ProducerAuthorities(value)
    value["producers"][0]["contracts"][0]["authority_level"] = "UNKNOWN"
    authorities.validate(declaration())


def test_duplicate_json_keys_in_model_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "authorities.json"
    path.write_text(
        '{"schema_version":"cap-producer-authorities-v1","producers":[],"producers":[]}'
    )
    with pytest.raises(ContractError):
        ProducerAuthorities.load(path)


def test_ci_checks_real_core_and_pre_model_history(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    baseline.mkdir()
    decl = declaration()
    paths = [DECLARATION, decl.output_schema.path, *(ref.path for ref in decl.fixtures)]
    assert decl.input_schema is not None
    paths.append(decl.input_schema.path)
    for name in paths:
        target = baseline / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((REPO / name).read_bytes())
    report = check_versions(baseline, REPO)
    assert report["status"] == "PASS"
    assert report["unchanged"] == 1


def test_ci_never_skips_authority_checks_for_unchanged_declarations(
    tmp_path: Path,
) -> None:
    roots = (tmp_path / "old", tmp_path / "new")
    for root in roots:
        (root / DECLARATION).parent.mkdir(parents=True)
        value = record()
        value["canonical_producer"] = "unregistered-service"
        (root / DECLARATION).write_text(json.dumps(value))
        (root / MODEL).write_text(json.dumps(model()))
    report = check_versions(*roots)
    assert report["status"] == "FAIL"
    assert {item["code"] for item in report["failures"]} == {"PRODUCER_UNKNOWN"}


def test_ci_missing_candidate_model_fails_closed(tmp_path: Path) -> None:
    report = check_versions(REPO, tmp_path)
    assert report["failures"] == [
        {"stage": "candidate", "code": "AUTHORITY_UNVERIFIABLE"}
    ]
