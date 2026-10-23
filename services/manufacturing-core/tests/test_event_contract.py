"""WP-CORE-005 Slice 1 structural, identity and version compatibility checks."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError as SchemaError
from manufacturing_core.events_v1 import DomainEventV1
from pydantic import ValidationError

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts" / "v1"
EVENTS = [
    ("LotReleased", "production", "Lot", "lot_id"),
    ("MaterialHoldApplied", "production", "MaterialHold", "material_hold_id"),
    (
        "QualityExcursionConfirmed",
        "quality",
        "QualityExcursion",
        "quality_excursion_id",
    ),
    ("ScheduleActivated", "scheduling", "ScheduleVersion", "schedule_id"),
]
SCHEMA = json.loads((CONTRACTS / "domain-event.schema.json").read_text())
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=FormatChecker())


def fixture(name: str) -> dict:
    return json.loads((CONTRACTS / f"domain-event.{name}.json").read_text())


def reject(data: dict) -> None:
    with pytest.raises(ValidationError):
        DomainEventV1.model_validate(data)
    with pytest.raises(SchemaError):
        VALIDATOR.validate(data)


def test_published_schema_matches_model() -> None:
    Draft202012Validator.check_schema(SCHEMA)
    assert DomainEventV1.model_json_schema() == SCHEMA


@pytest.mark.parametrize("name,namespace,aggregate,identity", EVENTS)
def test_fixture_round_trip(
    name: str, namespace: str, aggregate: str, identity: str
) -> None:
    data = fixture(name)
    VALIDATOR.validate(data)
    model = DomainEventV1.model_validate(data)
    assert json.loads(model.model_dump_json()) == data
    assert model.root.event_type == f"{namespace}.{name}"
    assert model.root.aggregate_type == aggregate
    assert model.root.aggregate_id == data["payload"][identity]
    assert model.root.aggregate_version == "opaque-revision-A"


@pytest.mark.parametrize("name,namespace,aggregate,identity", EVENTS)
def test_every_declared_envelope_and_payload_field_is_required(
    name: str, namespace: str, aggregate: str, identity: str
) -> None:
    for field in fixture(name):
        data = fixture(name)
        del data[field]
        reject(data)
    data = fixture(name)
    del data["payload"][identity]
    reject(data)


@pytest.mark.parametrize("name,namespace,aggregate,identity", EVENTS)
@pytest.mark.parametrize("invalid", [None, "", " \t", 12, True])
def test_identity_and_revision_are_required_opaque_strings(
    name: str, namespace: str, aggregate: str, identity: str, invalid: object
) -> None:
    for field in (
        "event_id",
        "aggregate_id",
        "aggregate_version",
        "source",
        "world_id",
        "simulation_run_id",
        "branch_id",
        "correlation_id",
        "causation_id",
        "trace_id",
    ):
        data = fixture(name)
        data[field] = invalid
        reject(data)
    data = fixture(name)
    data["payload"][identity] = invalid
    reject(data)


@pytest.mark.parametrize("name,namespace,aggregate,identity", EVENTS)
@pytest.mark.parametrize(
    "corruption",
    ["namespace", "producer", "aggregate", "payload", "extra", "time", "version"],
)
def test_malformed_or_wrong_namespace_events_rejected(
    name: str, namespace: str, aggregate: str, identity: str, corruption: str
) -> None:
    data = fixture(name)
    if corruption == "namespace":
        data["event_type"] = f"simulation.{name}"
    elif corruption == "producer":
        data["producer"] = "vision-service"
    elif corruption == "aggregate":
        data["aggregate_type"] = "Other"
    elif corruption == "payload":
        data["payload"] = {"display_label": "Not canonical identity"}
    elif corruption == "extra":
        data["payload"]["oracle_state"] = "hidden"
    elif corruption == "time":
        data["occurred_at"] = "2026-10-23T10:00:00"
    else:
        data["schema_version"] = "2"
    reject(data)


@pytest.mark.parametrize("name,namespace,aggregate,identity", EVENTS)
def test_structurally_valid_wrong_aggregate_binding_rejected(
    name: str, namespace: str, aggregate: str, identity: str
) -> None:
    data = fixture(name)
    data["aggregate_id"] = "OTHER-IDENTITY"
    VALIDATOR.validate(data)  # Equality across fields requires semantic validation.
    with pytest.raises(ValidationError, match="payload identity"):
        DomainEventV1.model_validate(data)


@pytest.mark.parametrize("version", ["0", "2", 1, None])
def test_no_silent_version_upgrade_or_downgrade(version: object) -> None:
    data = fixture("LotReleased")
    data["schema_version"] = version
    reject(data)


def test_unknown_future_event_and_envelope_fields_rejected() -> None:
    data = fixture("LotReleased")
    data["event_type"] = "production.FutureEvent"
    reject(data)
    data = fixture("LotReleased")
    data["future_required_field"] = "unknown"
    reject(data)
