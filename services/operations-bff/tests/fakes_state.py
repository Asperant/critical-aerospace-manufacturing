"""Deterministic Twin facility-state reader built from the service fixture."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any

from operations_bff.facility_state import (
    EquipmentState,
    FacilityStateQuery,
    FacilityStateSnapshot,
    LotState,
    RoutePosition,
)
from operations_bff.overview import SourceUnavailable
from test_contract_v1 import load_json


class FakeStateReader:
    name = "digital-twin-service"

    def __init__(self, snapshot: FacilityStateSnapshot) -> None:
        self.snapshot = snapshot
        self.queries: list[FacilityStateQuery] = []
        self.down = False

    def read(self, query: FacilityStateQuery) -> FacilityStateSnapshot:
        self.queries.append(query)
        if self.down:
            raise SourceUnavailable
        return self.snapshot


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


def from_fixture() -> tuple[FakeStateReader, dict[str, Any]]:
    fixture = load_json("facility-state.normal.json")
    source = fixture["meta"]["sources"][0]
    equipment = tuple(
        EquipmentState(
            equipment_id=item["equipment_id"],
            revision=item["revision"],
            equipment_state=item["equipment_state"],
            maintenance_state=item["maintenance_state"],
            epistemic_class=item["epistemic_class"],
            freshness=item["freshness"],
        )
        for item in fixture["facility"]["equipment"]
    )
    lots = tuple(
        LotState(
            lot_id=item["lot_id"],
            revision=item["revision"],
            lifecycle_state=item["lifecycle_state"],
            execution_state=item["execution_state"],
            hold_state=item["hold_state"],
            route_position=RoutePosition(**item["route_position"]),
            epistemic_class=item["epistemic_class"],
            freshness=item["freshness"],
        )
        for item in fixture["facility"]["lots"]
    )
    return (
        FakeStateReader(
            FacilityStateSnapshot(
                source=source["source"],
                revision=source["revision"],
                as_of=parse(source["as_of"]),
                freshness=source["freshness"],
                equipment=equipment,
                lots=lots,
            )
        ),
        fixture,
    )


def with_freshness(reader: FakeStateReader, freshness: str) -> None:
    reader.snapshot = replace(reader.snapshot, freshness=freshness)
