"""Conservation properties over random facilities (TEST-SIM-KERNEL).

Whatever the failures, windows and seeds, material is conserved: every lot finishes its
route in order exactly once, no machine runs two lots at once, and every start has a
matching completion.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from hypothesis import given, settings
from hypothesis import strategies as st
from manufacturing_simulator import BaselinePolicy, edd, fifo, static_priority
from manufacturing_simulator.operations import (
    EquipmentSpec,
    FacilityConfig,
    FailureSpec,
    MaintenanceSpec,
)
from ops_fixtures import config, kinds, run


@st.composite
def facilities(draw: st.DrawFn) -> FacilityConfig:
    lots = draw(st.integers(1, 5))
    mtbf = draw(st.one_of(st.none(), st.integers(15, 200)))
    cfg = config(lots=lots)
    equipment = (
        EquipmentSpec(
            "M1",
            ("MILL",),
            mtbf=mtbf,
            mttr=draw(st.integers(1, 40)),
            qualification=draw(st.integers(0, 20)),
            degrade_after=draw(st.one_of(st.none(), st.integers(1, 3))),
        ),
        *cfg.equipment[1:],
    )
    failures = tuple(
        FailureSpec(
            draw(st.sampled_from(["M1", "M2", "INS1"])), draw(st.integers(0, 150))
        )
        for _ in range(draw(st.integers(0, 3)))
    )
    windows = tuple(
        MaintenanceSpec(
            draw(st.sampled_from(["M1", "M2", "INS1"])),
            draw(st.integers(0, 150)),
            draw(st.integers(1, 60)),
        )
        for _ in range(draw(st.integers(0, 2)))
    )
    return replace(cfg, equipment=equipment, failures=failures, maintenance=windows)


@settings(max_examples=60, deadline=None)
@given(
    cfg=facilities(),
    seed=st.integers(0, 10_000),
    policy=st.sampled_from([fifo, edd, static_priority]),
)
def test_material_is_conserved_in_any_facility(
    cfg: FacilityConfig, seed: int, policy: Callable[[], BaselinePolicy]
) -> None:
    kernel, facility, publisher = run(cfg, seed=seed, provider=policy(), horizon=40_000)
    spans: dict[str, list[tuple[int, int]]] = {}
    total = 0
    for report in facility.lot_reports():
        assert report.lifecycle == "COMPLETED"
        assert [e.visit_id for e in report.executions] == ["V1", "V2", "V3"]
        previous_end = 0
        for execution in report.executions:
            assert execution.ended_at is not None
            assert previous_end <= execution.started_at < execution.ended_at
            previous_end = execution.ended_at
            spans.setdefault(execution.equipment_id, []).append(
                (execution.started_at, execution.ended_at)
            )
            total += 1
    for items in spans.values():
        items.sort()
        assert all(items[i][1] <= items[i + 1][0] for i in range(len(items) - 1))
    assert kinds(publisher).count("PROCESS_COMPLETED") == total == 3 * len(cfg.lots)
    status = kernel.status()
    assert status.processed_events == len(kernel.records())
    times = [record.time for record in kernel.records()]
    assert times == sorted(times)
