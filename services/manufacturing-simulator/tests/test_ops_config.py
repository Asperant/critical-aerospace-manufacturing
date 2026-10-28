"""Strict facility configuration and its replay digest (TEST-SIM-KERNEL)."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest
from manufacturing_simulator import InvalidConfigurationError
from manufacturing_simulator.operations import (
    EquipmentSpec,
    FailureSpec,
    HoldSpec,
    LotSpec,
    MaintenanceSpec,
    RouteSpec,
    VisitSpec,
)
from ops_fixtures import REWORK_ROUTE, config, routes


def build_visit(**changes: Any) -> VisitSpec:
    fields: dict[str, Any] = {
        "visit_id": "V1",
        "operation_class": "MILL",
        "eligible_equipment": ("M1",),
        "mean_duration": 10,
    }
    return VisitSpec(**{**fields, **changes})


BAD_VISITS: list[dict[str, Any]] = [
    {"visit_id": ""},
    {"visit_id": "has space"},
    {"operation_class": 5},
    {"eligible_equipment": ()},
    {"eligible_equipment": ("M1", "M1")},
    {"mean_duration": 0},
    {"mean_duration": True},
    {"mean_duration": 1.5},
    {"defect_per_mille": 1001},
    {"defect_per_mille": -1},
]


@pytest.mark.parametrize("change", BAD_VISITS)
def test_a_malformed_visit_is_refused(change: dict[str, Any]) -> None:
    with pytest.raises(InvalidConfigurationError):
        build_visit(**change)


def test_other_specs_refuse_malformed_values() -> None:
    bad: list[Any] = [
        lambda: RouteSpec("R", "rev", ()),
        lambda: RouteSpec("R", "rev", (build_visit(), build_visit())),
        lambda: EquipmentSpec("M", ()),
        lambda: EquipmentSpec("M", ("MILL",), mttr=0),
        lambda: EquipmentSpec("M", ("MILL",), degrade_after=3, critical_after=3),
        lambda: LotSpec("L", "O", "R", release_at=-1),
        lambda: FailureSpec("M", True),
        lambda: MaintenanceSpec("M", 0, 0),
        lambda: HoldSpec("L", 5, 5),
    ]
    for make in bad:
        with pytest.raises(InvalidConfigurationError):
            make()


def test_references_must_resolve() -> None:
    good = config()
    cases: list[dict[str, Any]] = [
        {"lots": (LotSpec("L1", "O1", "NOPE"),)},
        {"lots": good.lots + (good.lots[0],)},
        {"failures": (FailureSpec("MX", 1),)},
        {"maintenance": (MaintenanceSpec("MX", 1, 5),)},
        {"holds": (HoldSpec("LX", 1),)},
        {"equipment": good.equipment[:1]},
        {
            "routes": (
                replace(good.routes[0], route_id="R1"),
                replace(REWORK_ROUTE, route_id="R1"),
            )
        },
    ]
    for change in cases:
        with pytest.raises(InvalidConfigurationError):
            replace(good, **change)
    wrong_class = (
        RouteSpec(
            "R1",
            "rev",
            (build_visit(operation_class="INSPECT", eligible_equipment=("M1",)),),
        ),
    )
    with pytest.raises(InvalidConfigurationError):
        replace(good, routes=wrong_class)


def test_the_digest_is_stable_canonical_and_sensitive_to_every_part() -> None:
    base = config()
    assert base.digest() == config().digest() and base.digest().startswith("sha256:")
    json.dumps(base.to_document())  # JSON-ready, no objects
    variants = [
        replace(base, max_rework=3),
        replace(base, failures=(FailureSpec("M1", 5),)),
        replace(base, routes=routes(defect=10)),
        replace(
            base,
            equipment=(EquipmentSpec("M1", ("MILL",), mtbf=50), *base.equipment[1:]),
        ),
        replace(base, lots=base.lots[:-1]),
    ]
    digests = {base.digest(), *(v.digest() for v in variants)}
    assert len(digests) == len(variants) + 1
