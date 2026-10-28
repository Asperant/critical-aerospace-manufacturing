"""Re-entrant routing, queues and dispatch on the operational facility (TEST-SIM-KERNEL)."""

from __future__ import annotations

from manufacturing_simulator import edd, fifo, static_priority
from ops_fixtures import config, kinds, run


def test_every_lot_completes_its_three_visits_in_route_order() -> None:
    _, facility, _ = run(config())
    for report in facility.lot_reports():
        assert report.lifecycle == "COMPLETED"
        assert [e.visit_id for e in report.executions] == ["V1", "V2", "V3"]
        assert all(e.ended_at is not None for e in report.executions)
        times = [(e.started_at, e.ended_at or -1) for e in report.executions]
        assert all(a < b for a, b in times)
        assert all(times[i][1] <= times[i + 1][0] for i in range(2))  # no overlap


def test_a_reentered_operation_class_is_a_distinct_visit() -> None:
    _, facility, _ = run(config(lots=1))
    (report,) = facility.lot_reports()
    classes = {"V1": "MILL", "V2": "INSPECT", "V3": "MILL"}
    assert len({e.visit_id for e in report.executions}) == 3
    assert [classes[e.visit_id] for e in report.executions] == [
        "MILL",
        "INSPECT",
        "MILL",
    ]
    assert len({e.execution_id for e in report.executions}) == 3


def test_a_machine_never_runs_two_lots_at_once() -> None:
    _, facility, _ = run(config(lots=6))
    spans: dict[str, list[tuple[int, int]]] = {}
    for report in facility.lot_reports():
        for e in report.executions:
            assert e.ended_at is not None
            spans.setdefault(e.equipment_id, []).append((e.started_at, e.ended_at))
    for machine, items in spans.items():
        items.sort()
        assert all(
            items[i][1] <= items[i + 1][0] for i in range(len(items) - 1)
        ), machine


def test_work_waits_in_a_queue_until_a_machine_is_free_and_two_mills_share_it() -> None:
    _, facility, publisher = run(config(lots=4))
    used = {
        e.equipment_id
        for r in facility.lot_reports()
        for e in r.executions
        if e.visit_id == "V1"
    }
    assert used == {"M1", "M2"}
    assert kinds(publisher).count("LOT_QUEUED") == 4 * 3
    assert kinds(publisher).count("LOT_COMPLETED") == 4


def test_the_chosen_policy_decides_who_goes_first() -> None:
    first: dict[str, str] = {}
    for name, policy in (("fifo", fifo()), ("edd", edd()), ("prio", static_priority())):
        _, facility, _ = run(config(lots=4), provider=policy)
        starts = sorted(
            (e.started_at, r.lot_id)
            for r in facility.lot_reports()
            for e in r.executions
            if e.visit_id == "V1" and e.equipment_id == "M1"
        )
        first[name] = starts[0][1]
    assert first["fifo"] == "L1"  # equal ready times: lot id order
    assert first["edd"] == "L4"  # earliest due date
    assert first["prio"] == "L4"  # highest priority value


def test_a_held_lot_is_not_dispatched_until_released() -> None:
    from manufacturing_simulator.operations import HoldSpec

    cfg = config(lots=2, holds=(HoldSpec("L1", 0, 200),))
    _, facility, publisher = run(cfg)
    held = next(r for r in facility.lot_reports() if r.lot_id == "L1")
    assert held.executions[0].started_at >= 200
    assert {"HOLD_PLACED", "HOLD_RELEASED"} <= set(kinds(publisher))
    assert held.lifecycle == "COMPLETED"


def test_a_run_without_a_provider_dispatches_nothing_until_a_decision_arrives() -> None:
    from manufacturing_simulator import Kernel, ListPublisher, ScenarioEngine
    from manufacturing_simulator.operations import (
        KINDS,
        OperationalFacility,
        scenario_config,
    )

    cfg = config(lots=1)
    facility = OperationalFacility(cfg, provider=None, publisher=ListPublisher())
    world = ScenarioEngine(KINDS).initialize(scenario_config(cfg, seed=1, horizon=100))
    kernel = Kernel(world, facility.handlers())
    kernel.run_to_horizon(1000)
    (report,) = facility.lot_reports()
    assert report.execution_state == "QUEUED" and report.executions == ()
