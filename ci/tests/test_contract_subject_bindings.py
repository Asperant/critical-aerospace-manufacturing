"""TEST-EVT-001-009: static subject ownership; all async examples are synthetic."""

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
    StreamDefinition,
    StreamDefinitions,
    SubjectBinding,
)

REPO = Path(__file__).resolve().parents[2]


def context() -> tuple[Registry, ProducerAuthorities]:
    """Synthetic declarations, not hash-verified artifacts or production bindings."""
    exemplar = ContractDeclaration.from_mapping(
        json.loads(
            (REPO / "packages/contracts/registry/core.order-query.v1.json").read_text()
        )
    )
    declarations: dict[str, ContractDeclaration] = {}
    producers: list[dict[str, Any]] = []
    for suffix in ("observation", "other"):
        family = f"test.{suffix}"
        producer = f"test-{suffix}"
        root = f"services/{producer}/contracts/"
        declaration = replace(
            exemplar,
            contract_id=f"{family}.v1",
            version=1,
            name="Synthetic test event",
            contract_type="EVENT",
            sync_semantics="ASYNC",
            semantic_owner="Test owner",
            canonical_producer=producer,
            declared_consumers=("Test consumer",),
            authority_level="Synthetic observation only",
            input_schema=None,
            output_schema=replace(exemplar.output_schema, path=root + "schema.json"),
            fixtures=(),
        )
        declarations[declaration.contract_id] = declaration
        producers.append(
            {
                "producer": producer,
                "semantic_owner": "Test owner",
                "source_roots": [root],
                "contracts": [
                    {
                        "family": family,
                        "contract_type": "EVENT",
                        "authority_level": "Synthetic observation only",
                    }
                ],
            }
        )
    return Registry(declarations), ProducerAuthorities(
        {"schema_version": "cap-producer-authorities-v1", "producers": producers}
    )


def stream(suffix: str = "observation") -> dict[str, Any]:
    return {
        "stream_id": f"test.{suffix}-stream.v1",
        "version": 1,
        "stream_class": "DOMAIN_EVENT",
        "semantic_owner": "Test owner",
        "allowed_publishers": [f"test-{suffix}"],
        "known_consumers": ["Test consumer"],
        "schema_family": f"test.{suffix}",
        "partition_key_policy": "test-entity-id",
        "ordering_scope": "per-test-entity",
        "retention_class": "DOMAIN_STANDARD",
        "replay_policy": "projection-only",
        "data_classification": "INTERNAL",
        "message_size_class": "test-small",
        "dlq_policy": "per-test-consumer",
        "bindings": [
            {
                "binding_id": f"test.{suffix}.v1",
                "version": 1,
                "contract_id": f"test.{suffix}.v1",
                "schema_family": f"test.{suffix}",
                "subject": f"test.{suffix}.v1",
                "canonical_producer": f"test-{suffix}",
            }
        ],
    }


def catalog(*streams: dict[str, Any]) -> dict[str, Any]:
    return {"schema_version": "cap-stream-definitions-v1", "streams": list(streams)}


def test_valid_binding_is_deterministic_and_detached_from_caller() -> None:
    registry, authorities = context()
    first, second = stream(), stream("other")
    value = catalog(first, second)
    model = StreamDefinitions(value, registry, authorities)
    assert (
        model.to_json()
        == StreamDefinitions(catalog(second, first), registry, authorities).to_json()
    )
    assert (
        StreamDefinitions(json.loads(model.to_json()), registry, authorities).to_json()
        == model.to_json()
    )
    first["bindings"][0]["canonical_producer"] = "spoofed"
    assert model.definitions[0].bindings[0].canonical_producer == "test-observation"
    assert model.definitions[0].bindings[0].version == 1


def test_duplicate_subject_within_stream_is_rejected() -> None:
    value = stream()
    value["bindings"].append(copy.deepcopy(value["bindings"][0]))
    with pytest.raises(ContractError, match="SUBJECT_OWNERSHIP_CONFLICT"):
        StreamDefinition.from_mapping(value, *context())


def test_conflicting_registered_producers_cannot_share_subject_across_streams() -> None:
    first, second = stream(), stream("other")
    second["bindings"][0]["subject"] = first["bindings"][0]["subject"]
    with pytest.raises(ContractError, match="SUBJECT_OWNERSHIP_CONFLICT"):
        StreamDefinitions(catalog(first, second), *context())


def test_same_binding_identity_cannot_own_multiple_subjects() -> None:
    value = stream()
    other = copy.deepcopy(value["bindings"][0])
    other["subject"] = "test.another-subject"
    value["bindings"].append(other)
    with pytest.raises(ContractError, match="SUBJECT_BINDING_DUPLICATE"):
        StreamDefinitions(catalog(value), *context())


@pytest.mark.parametrize("producer", ["test-other", "unknown-producer"])
def test_binding_cannot_claim_another_producer(producer: str) -> None:
    value = stream()
    value["bindings"][0]["canonical_producer"] = producer
    value["allowed_publishers"] = [producer]
    with pytest.raises(ContractError, match="SUBJECT_PRODUCER_MISMATCH"):
        StreamDefinitions(catalog(value), *context())


def test_unknown_registered_producer_fails_closed() -> None:
    registry, authorities = context()
    declaration = replace(
        registry.get("test.observation.v1"), canonical_producer="unknown-producer"
    )
    value = stream()
    value["bindings"][0]["canonical_producer"] = "unknown-producer"
    value["allowed_publishers"] = ["unknown-producer"]
    with pytest.raises(ContractError, match="PRODUCER_UNKNOWN"):
        StreamDefinitions(
            catalog(value),
            Registry({declaration.contract_id: declaration}),
            authorities,
        )


@pytest.mark.parametrize(
    "subject",
    [
        "test.*",
        "test.>",
        "test..v1",
        "Test.event",
        " test.event",
        "test.event ",
        "nats://test.event",
        "test.event_name",
        "single",
        "",
        "test.événement",
        None,
    ],
)
def test_invalid_or_ambiguous_subject_is_rejected(subject: object) -> None:
    value = stream()
    value["bindings"][0]["subject"] = subject
    with pytest.raises(ContractError):
        StreamDefinitions(catalog(value), *context())


@pytest.mark.parametrize(
    "field,value",
    [
        ("binding_id", "test.other.v1"),
        ("binding_id", "test.observation.v2"),
        ("contract_id", "test.other.v1"),
        ("contract_id", "test.observation.v2"),
        ("schema_family", "test.other"),
        ("version", 2),
        ("version", True),
    ],
)
def test_binding_version_and_family_must_match(field: str, value: object) -> None:
    data = stream()
    data["bindings"][0][field] = value
    with pytest.raises(ContractError, match="SUBJECT_(VERSION|FAMILY)_MISMATCH"):
        StreamDefinitions(catalog(data), *context())


@pytest.mark.parametrize(
    "field,value",
    [
        ("version", 2),
        ("version", True),
        ("schema_family", "test.other"),
        ("semantic_owner", "Other owner"),
        ("allowed_publishers", ["test-other"]),
        ("allowed_publishers", ["test-observation", "test-other"]),
        ("known_consumers", ["Unknown consumer"]),
        ("stream_class", "TELEMETRY"),
        ("retention_class", "UNKNOWN"),
        ("partition_key_policy", "TBD"),
        ("bindings", []),
        ("dlq_policy", None),
    ],
)
def test_incomplete_or_inconsistent_stream_fails_closed(
    field: str, value: object
) -> None:
    data = stream()
    data[field] = value
    with pytest.raises(ContractError):
        StreamDefinitions(catalog(data), *context())


def test_missing_field_and_inline_wildcard_override_are_rejected() -> None:
    missing = stream()
    del missing["dlq_policy"]
    override = stream()
    override["bindings"][0]["allow_wildcard"] = True
    for value in (missing, override):
        with pytest.raises(ContractError, match="STREAM_DEFINITION_INVALID"):
            StreamDefinitions(catalog(value), *context())


def test_unknown_contract_and_catalog_version_fail_closed() -> None:
    value = stream("absent")
    with pytest.raises(ContractError):
        StreamDefinitions(catalog(value), *context())
    value = catalog(stream())
    value["schema_version"] = "cap-stream-definitions-v2"
    with pytest.raises(ContractError, match="STREAM_DEFINITION_UNVERIFIABLE"):
        StreamDefinitions(value, *context())


def test_duplicate_stream_identity_fails_closed() -> None:
    with pytest.raises(ContractError, match="STREAM_DEFINITION_DUPLICATE"):
        StreamDefinitions(catalog(stream(), stream()), *context())


def test_core_query_is_not_promoted_to_a_publishable_event() -> None:
    registry = Registry.load(REPO / "packages/contracts/registry")
    authorities = ProducerAuthorities.load(
        REPO / "packages/contracts/producer-authorities.json"
    )
    value = stream()["bindings"][0]
    value.update(
        binding_id="core.order-query.v1",
        contract_id="core.order-query.v1",
        schema_family="core.order-query",
        canonical_producer="manufacturing-core",
    )
    with pytest.raises(ContractError, match="STREAM_CONTRACT_UNSUPPORTED"):
        SubjectBinding.from_mapping(value, registry, authorities)
