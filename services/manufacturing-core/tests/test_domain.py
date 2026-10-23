"""TEST-CORE-DOMAIN; identity/history foundation of TEST-CORE-GENEALOGY."""

import json

import pytest
from manufacturing_core.domain import (
    Equipment,
    Lot,
    ManufacturingRoute,
    ProductionOrder,
    RouteVisit,
    SerializedComponent,
    validate_references,
)
from pydantic import ValidationError


@pytest.mark.parametrize("identity", ["COMP-1", "component/opaque", "a"])
@pytest.mark.parametrize("revision", ["0", "rev-1", "a1b2"])
def test_identity_revision_round_trip(identity: str, revision: str) -> None:
    component = SerializedComponent(id=identity, revision=revision, lot_id="LOT-1")
    assert (
        SerializedComponent.model_validate_json(component.model_dump_json())
        == component
    )


@pytest.mark.parametrize("field", ["id", "revision", "lot_id"])
@pytest.mark.parametrize("invalid", [None, "", " \t\n", 1, True, [], {}])
def test_invalid_identity_revision_and_reference(field: str, invalid: object) -> None:
    data: dict[str, object] = {"id": "C-1", "revision": "r1", "lot_id": "L-1"}
    data[field] = invalid
    with pytest.raises(ValidationError):
        SerializedComponent.model_validate(data)


@pytest.mark.parametrize("field", ["id", "revision", "lot_id"])
def test_missing_identity_revision_and_reference(field: str) -> None:
    data = {"id": "C-1", "revision": "r1", "lot_id": "L-1"}
    del data[field]
    with pytest.raises(ValidationError):
        SerializedComponent.model_validate(data)


def route() -> ManufacturingRoute:
    return ManufacturingRoute(
        id="R-1",
        revision="r1",
        visits=tuple(
            RouteVisit(
                id=identity,
                revision="r1",
                route_id="R-1",
                operation_class_id=operation,
                equipment_id="MET-1" if operation == "METROLOGY" else "CNC-1",
            )
            for identity, operation in (
                ("V-1", "CNC"),
                ("V-2", "METROLOGY"),
                ("V-3", "CNC"),
            )
        ),
    )


def test_ordered_reentrant_route_round_trip() -> None:
    original = route()
    restored = ManufacturingRoute.model_validate_json(original.model_dump_json())
    assert restored == original
    assert [visit.id for visit in restored.visits] == ["V-1", "V-2", "V-3"]
    assert [visit.operation_class_id for visit in restored.visits] == [
        "CNC",
        "METROLOGY",
        "CNC",
    ]
    assert restored.visits[0].id != restored.visits[2].id


@pytest.mark.parametrize("field,value", [("id", "V-1"), ("route_id", "R-OTHER")])
def test_duplicate_visit_or_wrong_route_rejected(field: str, value: str) -> None:
    data = json.loads(route().model_dump_json())
    data["visits"][2][field] = value
    with pytest.raises(ValidationError):
        ManufacturingRoute.model_validate(data)


@pytest.mark.parametrize("field", ["id", "revision", "visits"])
def test_route_cannot_be_mutated(field: str) -> None:
    with pytest.raises(ValidationError):
        setattr(route(), field, "replacement")


def test_component_identity_cannot_be_mutated() -> None:
    component = SerializedComponent(id="C-1", revision="r1", lot_id="L-1")
    with pytest.raises(ValidationError):
        component.id = "C-2"


@pytest.mark.parametrize("missing", [None, "order", "lot", "route", "equipment"])
def test_reference_consistency(missing: str | None) -> None:
    def check() -> None:
        validate_references(
            orders=[]
            if missing == "order"
            else [ProductionOrder(id="O-1", revision="r1", route_id="R-1")],
            lots=[]
            if missing == "lot"
            else [Lot(id="L-1", revision="r1", order_id="O-1")],
            components=[SerializedComponent(id="C-1", revision="r1", lot_id="L-1")],
            routes=[] if missing == "route" else [route()],
            equipment=[]
            if missing == "equipment"
            else [
                Equipment(id="CNC-1", revision="r1"),
                Equipment(id="MET-1", revision="r1"),
            ],
        )

    if missing is None:
        check()
    else:
        with pytest.raises(ValueError, match="unknown"):
            check()


def test_duplicate_component_identity_rejected() -> None:
    component = SerializedComponent(id="C-1", revision="r1", lot_id="L-1")
    with pytest.raises(ValueError, match="duplicate"):
        validate_references(
            orders=[],
            lots=[],
            components=[component, component],
            routes=[],
            equipment=[],
        )


def test_unknown_fields_do_not_introduce_simulator_truth() -> None:
    with pytest.raises(ValidationError):
        Equipment.model_validate(
            {"id": "E-1", "revision": "r1", "oracle_state": "failed"}
        )
