"""Failure, repair, degradation and maintenance (FR-SIM-004, FR-SIM-005; TEST-SIM-KERNEL)."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from manufacturing_simulator import fifo
from manufacturing_simulator.operations import (
    EquipmentSpec,
    FacilityConfig,
    FailureSpec,
    MaintenanceSpec,
    OperationalFacility,
)
from ops_fixtures import config, kinds, run


def equipment(facility: OperationalFacility, name: str) -> tuple[str, str]:
    item = next(e for e in facility.equipment_reports() if e.equipment_id == name)
    return item.state, item.health


def spans(facility: OperationalFacility, machine: str) -> list[tuple[int, int, str]]:
    return sorted(
        (e.started_at, e.ended_at or -1, r.lot_id)
        for r in facility.lot_reports()
        for e in r.executions
        if e.equipment_id == machine
    )


def with_equipment(**m1: Any) -> tuple[EquipmentSpec, ...]:
    return (
        EquipmentSpec("M1", ("MILL",), **m1),
        EquipmentSpec("M2", ("MILL",)),
        EquipmentSpec("INS1", ("INSPECT",)),
    )


def test_a_failure_during_processing_pauses_the_lot_on_the_same_machine() -> None:
    cfg = config(lots=2, failures=(FailureSpec("M1", 5),))
    _, facility, publisher = run(cfg)
    first = next(
        r for r in facility.lot_reports() if r.executions[0].equipment_id == "M1"
    )
    paused = first.executions[0]
    assert paused.equipment_id == "M1" and paused.started_at == 0
    assert paused.interruptions == 1
    assert (
        paused.ended_at is not None and paused.ended_at > 5 + 7
    )  # repair time had to pass
    assert first.lifecycle == "COMPLETED"
    assert kinds(publisher).count("EQUIPMENT_FAILED") == 1
    assert kinds(publisher).count("EQUIPMENT_REPAIRED") == 1


def test_a_failed_machine_takes_no_new_work_and_material_is_never_moved() -> None:
    cfg = config(lots=4, failures=(FailureSpec("M1", 5),))
    _, facility, publisher = run(cfg)
    repaired = next(e.time for e in publisher.events if e.kind == "EQUIPMENT_REPAIRED")
    for started, _, _ in spans(facility, "M1")[1:]:
        assert started >= repaired  # nothing starts on M1 while it is down
    for (
        report
    ) in facility.lot_reports():  # one execution per visit, never re-run elsewhere
        assert [e.visit_id for e in report.executions] == ["V1", "V2", "V3"]


def test_the_repair_path_goes_through_maintenance_and_qualification() -> None:
    cfg = config(
        lots=1,
        equipment=with_equipment(qualification=40),
        failures=(FailureSpec("M1", 5),),
    )
    seen: list[tuple[int, str]] = []
    for moment in (4, 6, 40, 200):
        _, facility, _ = run(cfg, until=moment)
        seen.append((moment, equipment(facility, "M1")[0]))
    states = dict(seen)
    assert states[4] == "BUSY"
    assert states[6] == "MAINTENANCE"
    assert states[200] in {"AVAILABLE", "BUSY"}
    assert "QUALIFICATION" in {
        equipment(run(cfg, until=t)[1], "M1")[0] for t in range(10, 120, 3)
    }


def test_health_degrades_with_use_and_a_repair_restores_it() -> None:
    cfg = config(lots=4, equipment=with_equipment(degrade_after=1, critical_after=3))
    _, facility, publisher = run(cfg, until=2000)
    steps = [
        dict(e.attributes) for e in publisher.events if e.kind == "EQUIPMENT_DEGRADED"
    ]
    assert {
        "from_state": "HEALTHY",
        "machine_id": "M1",
        "to_state": "DEGRADED",
    } in steps
    assert equipment(facility, "M1")[1] in {"DEGRADED", "CRITICAL"}
    failing = replace(cfg, failures=(FailureSpec("M1", 2000),))
    _, again, _ = run(failing, until=4000)
    assert equipment(again, "M1")[1] == "HEALTHY"


def mean_busy(cfg: FacilityConfig) -> float:
    total = count = 0
    for seed in range(1, 7):
        _, facility, _ = run(cfg, seed=seed)
        for r in facility.lot_reports():
            for e in r.executions:
                if e.equipment_id == "M1" and e.ended_at is not None:
                    total += e.ended_at - e.started_at
                    count += 1
    return total / count


def test_a_degraded_machine_is_slower() -> None:
    healthy = config(lots=4)
    worn = replace(healthy, equipment=with_equipment(degrade_after=1, critical_after=2))
    assert mean_busy(worn) > mean_busy(healthy)


def test_stochastic_failures_are_seeded_and_never_lose_a_lot() -> None:
    cfg = config(lots=6, equipment=with_equipment(mtbf=30))
    counts = []
    for seed in (1, 2, 3):
        _, facility, publisher = run(cfg, seed=seed, horizon=3000)
        failed = kinds(publisher).count("EQUIPMENT_FAILED")
        repaired = kinds(publisher).count("EQUIPMENT_REPAIRED")
        counts.append(failed)
        assert all(r.lifecycle == "COMPLETED" for r in facility.lot_reports())
        assert (
            0 <= failed - repaired <= 1
        )  # at most one repair still running at the horizon
    assert any(count > 0 for count in counts)
    first = [(e.kind, e.time) for e in run(cfg, seed=1, horizon=3000)[2].events]
    assert first == [(e.kind, e.time) for e in run(cfg, seed=1, horizon=3000)[2].events]


def test_a_planned_window_on_an_idle_machine_blocks_dispatch_and_restores_health() -> (
    None
):
    cfg = config(
        lots=4,
        equipment=with_equipment(degrade_after=1),
        maintenance=(MaintenanceSpec("M1", 0, 150),),
    )
    _, facility, publisher = run(cfg)
    assert all(started >= 150 for started, _, _ in spans(facility, "M1"))
    assert kinds(publisher).count("MAINTENANCE_STARTED") == 1
    assert kinds(publisher).count("MAINTENANCE_COMPLETED") == 1


def test_a_window_on_a_busy_machine_waits_until_it_is_idle() -> None:
    cfg = config(lots=1, maintenance=(MaintenanceSpec("M1", 3, 100),))
    _, facility, publisher = run(cfg)
    first_end = spans(facility, "M1")[0][1]
    started = next(e.time for e in publisher.events if e.kind == "MAINTENANCE_STARTED")
    assert started == first_end >= 15
    assert all(s >= started + 100 or e <= started for s, e, _ in spans(facility, "M1"))


def test_a_window_on_a_machine_that_is_down_is_skipped_not_invented() -> None:
    cfg = config(
        lots=1,
        failures=(FailureSpec("M1", 2),),
        maintenance=(MaintenanceSpec("M1", 4, 50),),
    )
    _, _, publisher = run(cfg)
    assert "MAINTENANCE_SKIPPED" in kinds(publisher)


def test_a_paused_lot_resumes_with_exactly_the_remaining_time() -> None:
    base = config(lots=1)
    _, plain, _ = run(base, seed=5)
    full = plain.lot_reports()[0].executions[0]
    duration = (full.ended_at or 0) - full.started_at
    assert full.equipment_id == "M1" and duration > 5
    _, facility, publisher = run(
        replace(base, failures=(FailureSpec("M1", 5),)), seed=5
    )
    paused = facility.lot_reports()[0].executions[0]
    repaired = next(e.time for e in publisher.events if e.kind == "EQUIPMENT_REPAIRED")
    assert paused.ended_at == repaired + (duration - 5)


def test_the_first_stochastic_failure_time_depends_on_the_seed() -> None:
    cfg = config(lots=1, equipment=with_equipment(mtbf=200))
    first = {
        seed: next(
            (
                e.time
                for e in run(cfg, seed=seed, horizon=3000)[2].events
                if e.kind == "EQUIPMENT_FAILED"
            ),
            None,
        )
        for seed in range(1, 8)
    }
    assert len({t for t in first.values() if t is not None}) > 1


def test_an_external_decision_cannot_start_work_on_a_machine_in_maintenance() -> None:
    from dispatch_fixtures import intake_document
    from manufacturing_simulator import ExecutionContext, OutcomeStatus, RejectReason

    cfg = config(lots=2, maintenance=(MaintenanceSpec("M1", 0, 100),))
    kernel, facility, _ = run(cfg, provider=fifo(), until=5)
    assert equipment(facility, "M1")[0] == "MAINTENANCE"
    document = intake_document(
        world_id=cfg.world_id,
        lot_id="L2",
        lot_revision=facility.lots()[0].revision,
        route_step="V1",
        machine_id="M1",
        base_state_revision=facility.state_revision,
        decision_time={"value": kernel.world.clock.now, "unit": "us"},
    )
    outcome = facility.gate.submit(document, ExecutionContext(kernel))
    assert outcome.status is OutcomeStatus.REJECTED
    assert outcome.reason_code is RejectReason.MACHINE_UNAVAILABLE
