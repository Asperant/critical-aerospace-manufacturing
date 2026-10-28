"""A decision-driven run replays identically (FR-SIM-013 with FR-SIM-008)."""

from __future__ import annotations

from dispatch_fixtures import KINDS, lot, rig, run_config
from manufacturing_simulator import (
    ComparisonOutcome,
    DecisionProvider,
    Kernel,
    ReplayIdentity,
    ReplaySpec,
    ScenarioEngine,
    check_determinism,
    edd,
    fifo,
    static_priority,
)

LOTS = [
    lot("L1", ready=0, due=90, priority=1),
    lot("L2", ready=0, due=10, priority=3),
    lot("L3", ready=2, due=50, priority=2),
    lot("L4", ready=2, due=50, priority=2),
    lot("L5", ready=5, due=5, priority=5),
]
IDENTITY = ReplayIdentity.for_current_runtime("dispatch-test", "dispatch-rig/1")


def spec(seed: int) -> ReplaySpec:
    return ReplaySpec(config=run_config(seed), identity=IDENTITY, max_events=10_000)


def test_every_baseline_replays_to_equal_digests() -> None:
    for policy in (fifo(), edd(), static_priority()):
        result = check_determinism(
            spec(20261028), lambda p=policy: rig(LOTS, p).handlers
        )
        assert result.outcome is ComparisonOutcome.MATCH, policy.rule_id


def run(
    policy: DecisionProvider, seed: int = 7
) -> tuple[list[tuple[int, str, str]], list[str]]:
    rigged = rig(LOTS, policy)
    world = ScenarioEngine(KINDS).initialize(run_config(seed))
    kernel = Kernel(world, rigged.handlers)
    kernel.run_to_horizon(10_000)
    return rigged.facility.started, rigged.facility.finished


def test_all_lots_are_started_once_in_the_order_the_rule_implies() -> None:
    started, finished = run(fifo())
    assert sorted(s[1] for s in started) == ["L1", "L2", "L3", "L4", "L5"]
    assert sorted(finished) == ["L1", "L2", "L3", "L4", "L5"]
    assert [s[1] for s in started[:2]] == ["L1", "L2"]  # ready at 0, lot id order
    edd_started, _ = run(edd())
    assert [s[1] for s in edd_started[:2]] == ["L2", "L1"]  # earliest due first


def test_the_same_seed_gives_the_same_run_and_another_seed_a_different_clock() -> None:
    assert run(fifo(), 7) == run(fifo(), 7)
    assert run(fifo(), 7)[0] != run(fifo(), 8)[0]


def test_two_free_machines_at_one_instant_get_different_lots() -> None:
    started, _ = run(fifo())
    at_zero = [s for s in started if s[0] == 0]
    assert sorted(s[2] for s in at_zero) == ["M1", "M2"]
    assert len({s[1] for s in at_zero}) == 2
