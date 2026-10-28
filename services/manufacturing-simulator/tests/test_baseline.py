"""Standalone baseline policies: total order, determinism, no hidden inputs."""

from __future__ import annotations

import itertools
from typing import Any

from hypothesis import given
from hypothesis import strategies as st
from manufacturing_simulator import (
    BaselinePolicy,
    Candidate,
    DecisionRequest,
    IntakeSource,
    decode_intake,
    edd,
    fifo,
    static_priority,
)


def candidate(
    lot_id: str,
    *,
    ready: int = 0,
    due: int = 100,
    priority: int = 1,
    machines: tuple[str, ...] = ("M1",),
) -> Candidate:
    return Candidate(lot_id, f"{lot_id}-r1", "S1", priority, due, ready, machines)


def request(*candidates: Candidate, machine: str = "M1") -> DecisionRequest:
    return DecisionRequest("world-1", "REQ-9", "rev-3", 40, machine, tuple(candidates))


def chosen(policy: BaselinePolicy, asked: DecisionRequest) -> str:
    decision = policy.decide(asked)
    assert decision is not None
    return decision.lot_id


def test_each_rule_picks_by_its_key_and_breaks_ties_by_lot_id() -> None:
    a = candidate("A", ready=5, due=50, priority=1)
    b = candidate("B", ready=1, due=90, priority=1)
    c = candidate("C", ready=1, due=20, priority=3)
    d = candidate("D", ready=1, due=20, priority=3)
    assert chosen(fifo(), request(a, b, c, d)) == "B"
    assert chosen(edd(), request(a, b, c, d)) == "C"
    assert chosen(static_priority(), request(a, b, c, d)) == "C"


def test_decisions_are_valid_baseline_intakes_with_a_deterministic_id() -> None:
    decision = fifo().decide(request(candidate("A"), candidate("B", ready=3)))
    assert decision is not None
    assert decision.source is IntakeSource.BASELINE
    assert decision.dispatch_id == "DSP-REQ-9" and decision.decision_time == 40
    assert decision.base_state_revision == "rev-3" and decision.machine_id == "M1"
    assert (decision.rule_id, decision.rule_version) == ("SIM-FIFO", "1")
    assert decode_intake(decision.to_document()) == decision


def test_no_eligible_candidate_gives_no_decision() -> None:
    assert fifo().decide(request()) is None
    assert fifo().decide(request(candidate("A", machines=("M2",)))) is None


lots = st.lists(
    st.builds(
        candidate,
        st.text("ABCDEFGH", min_size=1, max_size=3),
        ready=st.integers(0, 5),
        due=st.integers(0, 5),
        priority=st.integers(0, 3),
    ),
    min_size=1,
    max_size=6,
    unique_by=lambda c: c.lot_id,
)


@given(items=lots)
def test_the_choice_does_not_depend_on_candidate_order(items: list[Candidate]) -> None:
    for policy in (fifo(), edd(), static_priority()):
        chosen: set[Any] = set()
        for order in itertools.islice(itertools.permutations(items), 24):
            decision = policy.decide(request(*order))
            assert decision is not None
            chosen.add(decision.lot_id)
        assert len(chosen) == 1


@given(items=lots)
def test_the_choice_is_a_minimum_of_the_documented_key(items: list[Candidate]) -> None:
    pick = fifo().decide(request(*items))
    assert pick is not None
    best = min(items, key=lambda c: (c.ready_at, c.lot_id))
    assert pick.lot_id == best.lot_id
    pick = edd().decide(request(*items))
    assert pick is not None
    assert (
        pick.lot_id == min(items, key=lambda c: (c.due_at, c.ready_at, c.lot_id)).lot_id
    )
    pick = static_priority().decide(request(*items))
    assert pick is not None
    assert (
        pick.lot_id
        == min(items, key=lambda c: (-c.priority, c.ready_at, c.lot_id)).lot_id
    )
