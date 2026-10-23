"""Fixture compatibility, structural schema and semantic contract checks."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from manufacturing_core.query_v1 import OrderQueryRequestV1, OrderQueryResultV1
from pydantic import ValidationError

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts" / "v1"


@pytest.mark.parametrize(
    "filename,model",
    [
        ("order-query.schema.json", OrderQueryResultV1),
        ("order-query-request.schema.json", OrderQueryRequestV1),
    ],
)
def test_published_schema_matches_reused_models(
    filename: str, model: type[OrderQueryResultV1] | type[OrderQueryRequestV1]
) -> None:
    published = json.loads((CONTRACTS / filename).read_text())
    Draft202012Validator.check_schema(published)
    assert published == model.model_json_schema()


@pytest.mark.parametrize("scenario", ["normal", "reentrant"])
def test_fixture_schema_and_identity_round_trip(scenario: str) -> None:
    data = json.loads((CONTRACTS / f"order-query.{scenario}.json").read_text())
    schema = json.loads((CONTRACTS / "order-query.schema.json").read_text())
    Draft202012Validator(schema).validate(data)
    result = OrderQueryResultV1.model_validate(data)
    assert json.loads(result.model_dump_json()) == data
    assert set(data) == {
        "contract_version",
        "order",
        "route",
        "lots",
        "components",
        "equipment",
    }
    assert set(data["order"]) == {"id", "revision", "route_id"}
    assert set(data["route"]) == {"id", "revision", "visits"}
    assert set(data["route"]["visits"][0]) == {
        "id",
        "revision",
        "route_id",
        "operation_class_id",
        "equipment_id",
    }
    assert set(data["lots"][0]) == {"id", "revision", "order_id"}
    assert set(data["components"][0]) == {"id", "revision", "lot_id"}
    assert set(data["equipment"][0]) == {"id", "revision"}


def reentrant_data() -> dict:
    return json.loads((CONTRACTS / "order-query.reentrant.json").read_text())


def test_visit_order_is_not_identity_order() -> None:
    result = OrderQueryResultV1.model_validate(reentrant_data())
    assert [visit.id for visit in result.route.visits] == ["V-30", "V-10", "V-20"]
    assert [visit.operation_class_id for visit in result.route.visits] == [
        "CNC",
        "METROLOGY",
        "CNC",
    ]
    assert len({visit.id for visit in result.route.visits}) == 3


@pytest.mark.parametrize(
    "collection,field",
    [("lots", "order_id"), ("components", "lot_id"), ("equipment", "id")],
)
def test_dangling_references_rejected(collection: str, field: str) -> None:
    data = reentrant_data()
    data[collection][0][field] = "missing"
    with pytest.raises(ValidationError):
        OrderQueryResultV1.model_validate(data)


@pytest.mark.parametrize("collection", ["lots", "components", "equipment"])
def test_duplicate_entity_identity_rejected(collection: str) -> None:
    data = reentrant_data()
    data[collection].append(data[collection][0])
    with pytest.raises(ValidationError, match="duplicate"):
        OrderQueryResultV1.model_validate(data)


@pytest.mark.parametrize("collection", ["lots", "components", "equipment"])
def test_collection_order_is_explicit(collection: str) -> None:
    data = reentrant_data()
    data[collection].reverse()
    with pytest.raises(ValidationError, match="ordered"):
        OrderQueryResultV1.model_validate(data)


@pytest.mark.parametrize(
    "field", ["contract_version", "order", "route", "lots", "components", "equipment"]
)
def test_required_contract_fields(field: str) -> None:
    data = reentrant_data()
    del data[field]
    with pytest.raises(ValidationError):
        OrderQueryResultV1.model_validate(data)


@pytest.mark.parametrize(
    "corruption",
    [
        "version",
        "extra",
        "unknown_route",
        "missing_equipment",
        "duplicate_visit",
        "visit_parent",
        "revision",
        "identity",
    ],
)
def test_invalid_response_rejected(corruption: str) -> None:
    data = reentrant_data()
    if corruption == "version":
        data["contract_version"] = "core.order-query.v2"
    elif corruption == "extra":
        data["oracle_state"] = "failed"
    elif corruption == "unknown_route":
        data["order"]["route_id"] = "missing"
    elif corruption == "missing_equipment":
        data["equipment"] = []
    elif corruption == "duplicate_visit":
        data["route"]["visits"][2]["id"] = "V-30"
    elif corruption == "visit_parent":
        data["route"]["visits"][0]["route_id"] = "other"
    elif corruption == "revision":
        data["order"]["revision"] = ""
    else:
        data["order"]["id"] = ""
    with pytest.raises(ValidationError):
        OrderQueryResultV1.model_validate(data)


@pytest.mark.parametrize("identity", [None, "", " \t", 1, True])
def test_invalid_request_identity(identity: object) -> None:
    with pytest.raises(ValidationError):
        OrderQueryRequestV1.model_validate(
            {"contract_version": "core.order-query.v1", "order_id": identity}
        )


def test_request_schema_and_required_version() -> None:
    request = {"contract_version": "core.order-query.v1", "order_id": "O-NORMAL"}
    Draft202012Validator(
        json.loads((CONTRACTS / "order-query-request.schema.json").read_text())
    ).validate(request)
    assert OrderQueryRequestV1.model_validate(request).model_dump() == request
    with pytest.raises(ValidationError):
        OrderQueryRequestV1.model_validate({"order_id": "O-NORMAL"})
