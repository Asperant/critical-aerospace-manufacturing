"""TEST-EVT-001-011: pure publisher allowlist; no runtime identity or broker."""

import json
from dataclasses import replace
from typing import Any

import pytest
from cap_contracts import ContractError, Registry, StreamDefinitions
from cap_contracts.permissions import PublisherPermissions
from test_contract_subject_bindings import catalog, context, stream


def permissions(*values: dict[str, Any]) -> PublisherPermissions:
    registry, authorities = context()
    return PublisherPermissions(
        StreamDefinitions(catalog(*values), registry, authorities),
        registry,
        authorities,
    )


def test_only_owned_exact_subjects_are_allowed() -> None:
    policy = permissions(stream(), stream("other"))
    assert policy.allows_publish("test-observation", "test.observation.v1")
    assert policy.allows_publish("test-other", "test.other.v1")
    assert not policy.allows_publish("test-other", "test.observation.v1")
    assert not policy.allows_publish("test-observation", "test.other.v1")


@pytest.mark.parametrize(
    "producer,subject",
    [
        ("Test consumer", "test.observation.v1"),
        ("test-consumer", "test.observation.v1"),
        ("unknown", "test.observation.v1"),
        ("test-observation", "test.unknown.v1"),
        ("test-observation", "test.*"),
        ("test-observation", ">"),
        ("*", "test.observation.v1"),
        ("TEST-OBSERVATION", "test.observation.v1"),
        (None, "test.observation.v1"),
        ("test-observation", []),
    ],
)
def test_unknown_consumer_broadened_and_invalid_claims_deny(
    producer: object, subject: object
) -> None:
    assert not permissions(stream()).allows_publish(producer, subject)


def test_output_order_is_deterministic_and_contains_no_subscribe_grants() -> None:
    first = permissions(stream(), stream("other")).to_json()
    assert permissions(stream("other"), stream()).to_json() == first
    assert json.loads(first) == {
        "schema_version": "cap-publisher-permissions-v1",
        "publishers": [
            {"producer": "test-observation", "subjects": ["test.observation.v1"]},
            {"producer": "test-other", "subjects": ["test.other.v1"]},
        ],
    }


def test_one_producer_collects_only_its_versioned_subjects() -> None:
    registry, authorities = context()
    before = registry.get("test.observation.v1")
    after = replace(before, contract_id="test.observation.v2", version=2)
    registry = Registry({item.contract_id: item for item in (before, after)})
    one, two = stream(), stream()
    two.update(stream_id="test.observation-stream.v2", version=2)
    two["bindings"][0].update(
        binding_id=after.contract_id,
        contract_id=after.contract_id,
        version=2,
        subject="test.observation.v2",
    )
    model = StreamDefinitions(catalog(two, one), registry, authorities)
    policy = PublisherPermissions(model, registry, authorities)
    assert policy.entries[0].subjects == ("test.observation.v1", "test.observation.v2")


def test_projection_revalidates_current_registry_and_rejects_unknown_producer() -> None:
    registry, authorities = context()
    model = StreamDefinitions(catalog(stream()), registry, authorities)
    declaration = replace(
        registry.get("test.observation.v1"), canonical_producer="unknown-producer"
    )
    changed = Registry({declaration.contract_id: declaration})
    with pytest.raises(ContractError, match="PRODUCER_UNKNOWN"):
        PublisherPermissions(model, changed, authorities)


@pytest.mark.parametrize("change", ["duplicate", "conflict", "wildcard"])
def test_conflicting_or_ambiguous_bindings_never_produce_permissions(
    change: str,
) -> None:
    first, second = stream(), stream("other")
    if change == "duplicate":
        second = stream()
        second["stream_id"] = "test.alternate-stream.v1"
        second["bindings"][0]["subject"] = "test.alternate.v1"
    elif change == "conflict":
        second["bindings"][0]["subject"] = first["bindings"][0]["subject"]
    else:
        second["bindings"][0]["subject"] = "test.*"
    with pytest.raises(ContractError):
        permissions(first, second)


def test_raw_unvalidated_mapping_is_rejected() -> None:
    # Deliberately exercise runtime misuse beyond the typed API.
    value: Any = catalog(stream())
    with pytest.raises(ContractError, match="PUBLISHER_PERMISSIONS_UNVERIFIABLE"):
        PublisherPermissions(value, *context())
