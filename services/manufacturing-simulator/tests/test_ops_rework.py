"""Rework, scrap and defects (FR-SIM-006; TEST-SIM-KERNEL).

The Simulator executes only a directive that arrives the way Core would issue it; a
defect produces an operational fact, never a directive.
"""

from __future__ import annotations

from dataclasses import replace

import pytest
from manufacturing_simulator import (
    ExecutionContext,
    Kernel,
    ListPublisher,
    ScenarioEngine,
)
from manufacturing_simulator.operations import (
    KINDS,
    EquipmentSpec,
    FacilityConfig,
    FailureSpec,
    OperationalFacility,
    ReworkDirectiveSpec,
    ScrapSpec,
    scenario_config,
)
from ops_fixtures import REWORK_ROUTE, config, kinds, routes, run


def stalled(*extra: ScrapSpec) -> FacilityConfig:
    """One lot, with the inspection station down for long so it waits QUEUED for V2."""
    return replace(
        config(lots=1),
        failures=(FailureSpec("INS1", 1),),
        equipment=(
            EquipmentSpec("M1", ("MILL",)),
            EquipmentSpec("M2", ("MILL",)),
            EquipmentSpec("INS1", ("INSPECT",), mttr=4000),
        ),
        scraps=extra,
    )


def waiting() -> tuple[Kernel, OperationalFacility, ListPublisher]:
    """Run until the lot has finished V1 and waits QUEUED for the inspection station."""
    kernel, facility, publisher = run(stalled(), until=200)
    assert all(
        r.execution_state == "QUEUED" and r.current_visit == "V2"
        for r in facility.lot_reports()
    )
    return kernel, facility, publisher


def directive(
    name: str = "D1",
    *,
    at: int = 0,
    origin: str = "V1",
    back: str = "V2",
    route: str = "RW",
    approval: str = "APPROVED",
) -> ReworkDirectiveSpec:
    return ReworkDirectiveSpec(name, "L1", at, origin, back, route, approval)


def test_an_approved_directive_inserts_the_rework_route_and_returns_to_the_original_route() -> (
    None
):
    kernel, facility, publisher = waiting()
    assert facility.apply_rework(directive(), ExecutionContext(kernel)) is None
    (report,) = facility.lot_reports()
    assert (
        report.current_visit == REWORK_ROUTE.visits[0].visit_id
        and report.rework_count == 1
    )
    assert report.directives == ("D1",) and "REWORK_STARTED" in kinds(publisher)


def test_rework_runs_to_completion_through_the_inserted_visit() -> None:
    cfg = config(
        lots=1,
        reworks=(directive(at=100),),
        failures=(FailureSpec("INS1", 1),),
        equipment=(
            EquipmentSpec("M1", ("MILL",)),
            EquipmentSpec("M2", ("MILL",)),
            EquipmentSpec("INS1", ("INSPECT",), mttr=300),
        ),
    )
    _, facility, publisher = run(cfg)
    (report,) = facility.lot_reports()
    assert [e.visit_id for e in report.executions] == ["V1", "W1", "V2", "V3"]
    assert report.lifecycle == "COMPLETED" and report.rework_count == 1
    assert kinds(publisher).count("REWORK_STARTED") == 1


REFUSALS: list[tuple[str, ReworkDirectiveSpec, str]] = [
    ("not approved", directive(approval="PENDING"), "NOT_APPROVED"),
    ("rejected", directive(approval="REJECTED"), "NOT_APPROVED"),
    ("no origin", directive(origin="V3"), "NO_ORIGIN_EXECUTION"),
    ("bad return", directive(back="NOPE"), "BAD_RETURN_VISIT"),
]


@pytest.mark.parametrize(("name", "refused", "reason"), REFUSALS)
def test_a_directive_that_does_not_satisfy_the_rules_is_refused_without_change(
    name: str, refused: ReworkDirectiveSpec, reason: str
) -> None:
    kernel, facility, publisher = waiting()
    before = (facility.state_revision, facility.lot_reports())
    assert facility.apply_rework(refused, ExecutionContext(kernel)) == reason, name
    assert (facility.state_revision, facility.lot_reports()) == before
    rejected = [
        dict(e.attributes) for e in publisher.events if e.kind == "REWORK_REJECTED"
    ]
    assert rejected[-1]["reason_code"] == reason


def test_rework_is_refused_while_the_lot_is_being_processed() -> None:
    kernel, facility, _ = run(config(lots=1), until=3)
    (report,) = facility.lot_reports()
    assert report.execution_state == "PROCESSING"
    assert (
        facility.apply_rework(directive(), ExecutionContext(kernel))
        == "NOT_BETWEEN_STEPS"
    )


def test_the_rework_count_is_limited() -> None:
    kernel, facility, _ = waiting()
    context = ExecutionContext(kernel)
    results = [facility.apply_rework(directive(f"D{n}"), context) for n in range(1, 4)]
    assert results == [None, None, "REWORK_LIMIT"]
    assert facility.lot_reports()[0].rework_count == 2


def test_completed_and_scrapped_material_cannot_be_reworked() -> None:
    kernel, facility, _ = run(config(lots=1))
    assert (
        facility.apply_rework(directive(), ExecutionContext(kernel)) == "LOT_COMPLETED"
    )
    kernel, facility, _ = run(stalled(ScrapSpec("L1", 150)), until=200)
    assert facility.lot_reports()[0].lifecycle == "SCRAPPED"
    assert (
        facility.apply_rework(directive(), ExecutionContext(kernel)) == "LOT_SCRAPPED"
    )


def test_scrap_is_refused_while_processing_and_a_scrapped_lot_is_never_dispatched() -> (
    None
):
    _, facility, publisher = run(replace(config(lots=1), scraps=(ScrapSpec("L1", 3),)))
    assert "LOT_SCRAP_REJECTED" in kinds(publisher)
    assert facility.lot_reports()[0].lifecycle == "COMPLETED"
    cfg = replace(
        config(lots=2),
        failures=(FailureSpec("INS1", 1),),
        equipment=(
            EquipmentSpec("M1", ("MILL",)),
            EquipmentSpec("M2", ("MILL",)),
            EquipmentSpec("INS1", ("INSPECT",), mttr=100),
        ),
        scraps=(ScrapSpec("L1", 60),),
    )
    _, facility, _ = run(cfg)
    by_lot = {r.lot_id: r for r in facility.lot_reports()}
    assert by_lot["L1"].lifecycle == "SCRAPPED" and len(by_lot["L1"].executions) == 1
    assert by_lot["L2"].lifecycle == "COMPLETED"


def test_a_defect_is_an_operational_fact_and_never_creates_a_rework_directive() -> None:
    cfg = replace(config(lots=3), routes=routes(defect=1000))
    _, facility, publisher = run(cfg)
    assert kinds(publisher).count("INSPECTION_FAILED") == 3
    assert kinds(publisher).count("REWORK_REQUESTED") == 3
    assert "REWORK_STARTED" not in kinds(publisher)
    assert all(
        r.rework_count == 0 and r.lifecycle == "COMPLETED"
        for r in facility.lot_reports()
    )


def test_a_directive_for_an_unknown_scenario_is_a_configuration_error() -> None:
    from manufacturing_simulator import InvalidConfigurationError

    with pytest.raises(InvalidConfigurationError):
        config(reworks=(directive(route="MISSING"),))
    world = ScenarioEngine(KINDS).initialize(
        scenario_config(config(lots=1), seed=1, horizon=10)
    )
    assert world.config.horizon == 10
