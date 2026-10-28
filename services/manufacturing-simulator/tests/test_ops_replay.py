"""Facility runs replay to equal digests and the configuration binds the input."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace

from manufacturing_simulator import (
    ComparisonOutcome,
    EventHandler,
    ReplayIdentity,
    ReplaySpec,
    check_determinism,
    edd,
    fifo,
    make_payload,
    replay,
    static_priority,
)
from manufacturing_simulator.operations import (
    EquipmentSpec,
    FacilityConfig,
    FailureSpec,
    MaintenanceSpec,
    OperationalFacility,
    ReworkDirectiveSpec,
    scenario_config,
)
from ops_fixtures import config, routes

IDENTITY = ReplayIdentity.for_current_runtime("ops-test", "operational-facility/1")


def rich() -> FacilityConfig:
    """Failures, a stochastic machine, maintenance, a hold-free rework and defects."""
    return replace(
        config(lots=5),
        equipment=(
            EquipmentSpec("M1", ("MILL",), mtbf=60, degrade_after=2, critical_after=4),
            EquipmentSpec("M2", ("MILL",), qualification=5),
            EquipmentSpec("INS1", ("INSPECT",)),
        ),
        routes=routes(defect=300),
        failures=(FailureSpec("M2", 40),),
        maintenance=(MaintenanceSpec("M1", 90, 30),),
        reworks=(ReworkDirectiveSpec("D1", "L1", 30, "V1", "V2", "RW"),),
    )


def spec(cfg: FacilityConfig, seed: int) -> ReplaySpec:
    return ReplaySpec(
        config=scenario_config(cfg, seed=seed, horizon=3000),
        identity=IDENTITY,
        max_events=200_000,
        initial_state=make_payload({"facility_digest": cfg.digest()}),
    )


def test_every_policy_and_seed_replays_to_equal_digests() -> None:
    cfg = rich()
    for policy in (fifo, edd, static_priority):
        for seed in (1, 2, 3, 4):
            result = check_determinism(
                spec(cfg, seed),
                lambda p=policy: OperationalFacility(cfg, provider=p()).handlers(),
            )
            assert result.outcome is ComparisonOutcome.MATCH, (policy.__name__, seed)


def test_a_different_seed_or_configuration_gives_a_different_run() -> None:
    cfg = rich()

    def factory(c: FacilityConfig) -> Callable[[], dict[str, EventHandler]]:
        return lambda: OperationalFacility(c, provider=fifo()).handlers()

    a = replay(spec(cfg, 1), factory(cfg))
    b = replay(spec(cfg, 2), factory(cfg))
    assert a.events != b.events
    other = replace(cfg, failures=(FailureSpec("M2", 41),))
    c = replay(spec(other, 1), factory(other))
    assert a.input_digest != c.input_digest  # the facility digest is part of the input
    assert a.events != c.events
