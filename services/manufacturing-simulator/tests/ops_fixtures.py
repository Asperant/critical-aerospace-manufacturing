"""A small but re-entrant facility for the operational-model tests.

Two mills (``M1``, ``M2``) and one inspection station (``INS1``). Route ``R1`` visits
the MILL class twice, so a lot re-enters the same operation class with a distinct visit.
Passing tests prove the operational mechanics on this facility, not realism.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from manufacturing_simulator import (
    DecisionProvider,
    Kernel,
    ListPublisher,
    ScenarioEngine,
    fifo,
)
from manufacturing_simulator.operations import (
    KINDS,
    EquipmentSpec,
    FacilityConfig,
    LotSpec,
    OperationalFacility,
    RouteSpec,
    VisitSpec,
    scenario_config,
)

WORLD = "world-ops"


def routes(*, defect: int = 0, inspect: bool = True) -> tuple[RouteSpec, ...]:
    return (
        RouteSpec(
            "R1",
            "R1-rev1",
            (
                VisitSpec("V1", "MILL", ("M1", "M2"), 20),
                VisitSpec("V2", "INSPECT", ("INS1",), 10, inspect, defect),
                VisitSpec("V3", "MILL", ("M1", "M2"), 20),
            ),
        ),
    )


REWORK_ROUTE = RouteSpec("RW", "RW-rev1", (VisitSpec("W1", "MILL", ("M1", "M2"), 15),))


def config(lots: int = 4, **changes: Any) -> FacilityConfig:
    base = FacilityConfig(
        world_id=WORLD,
        equipment=(
            EquipmentSpec("M1", ("MILL",)),
            EquipmentSpec("M2", ("MILL",)),
            EquipmentSpec("INS1", ("INSPECT",)),
        ),
        routes=routes(),
        lots=tuple(
            LotSpec(f"L{n}", f"O{n}", "R1", release_at=0, priority=n, due_at=500 - n)
            for n in range(1, lots + 1)
        ),
        rework_routes=(REWORK_ROUTE,),
    )
    return replace(base, **changes)


def run(
    cfg: FacilityConfig,
    *,
    seed: int = 7,
    provider: DecisionProvider | None = None,
    horizon: int = 3000,
    until: int | None = None,
) -> tuple[Kernel, OperationalFacility, ListPublisher]:
    publisher = ListPublisher()
    facility = OperationalFacility(
        cfg, provider=provider or fifo(), publisher=publisher
    )
    world = ScenarioEngine(KINDS).initialize(
        scenario_config(cfg, seed=seed, horizon=horizon)
    )
    kernel = Kernel(world, facility.handlers())
    if until is None:
        kernel.run_to_horizon(100_000)
    else:
        kernel.run(until, 100_000)
    return kernel, facility, publisher


def kinds(publisher: ListPublisher) -> list[str]:
    return [event.kind for event in publisher.events]
