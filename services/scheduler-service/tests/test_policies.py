"""FIFO/EDD/CR/SPT/SRPT decisions: hand-calculated cases, an independent oracle,
filtering, ties and properties. Fixture inputs only; no benchmark evidence."""

from __future__ import annotations

import dataclasses
import itertools
import random
from fractions import Fraction
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from manufacturing_scheduler import (
    POLICIES,
    DecisionStatus,
    DispatchJob,
    JobState,
    UnsupportedPolicyError,
    get_policy,
)
from sch_fixtures import context, job, ranked_ids

# Decision epoch 10. Hand-calculated; every rule picks a different job.
#   id  entry due  op  rem   CR = (due-10)/rem
#   J1   0    100  10  50    90/50 = 9/5
#   J2   1     20   6   8    10/8  = 5/4
#   J3   2     30   7  40    20/40 = 1/2
#   J4   3     90   2  60    80/60 = 4/3
#   J5   4     80   3   5    70/5  = 14
HAND = (
    job("J1", 0, 100, 10, 50),
    job("J2", 1, 20, 6, 8),
    job("J3", 2, 30, 7, 40),
    job("J4", 3, 90, 2, 60),
    job("J5", 4, 80, 3, 5),
)
HAND_RANKING = {
    "SCH-B1": ["J1", "J2", "J3", "J4", "J5"],  # entry 0,1,2,3,4
    "SCH-B2": ["J2", "J3", "J5", "J4", "J1"],  # due 20,30,80,90,100
    "SCH-B3": ["J3", "J2", "J4", "J1", "J5"],  # 1/2, 5/4, 4/3, 9/5, 14
    "SCH-B4": ["J4", "J5", "J2", "J3", "J1"],  # next operation 2,3,6,7,10
    "SCH-B5": ["J5", "J2", "J3", "J1", "J4"],  # remaining route 5,8,40,50,60
}


@pytest.mark.parametrize("policy_id", sorted(HAND_RANKING))
def test_hand_calculated_ranking(policy_id: str) -> None:
    decision = get_policy(policy_id).select(context(10, HAND))
    assert decision.status is DecisionStatus.SELECTED
    assert ranked_ids(decision) == HAND_RANKING[policy_id]
    assert decision.selected_job_id == HAND_RANKING[policy_id][0]
    assert (decision.policy_id, decision.decision_tick) == (policy_id, 10)


def test_the_five_rules_disagree_on_the_hand_case() -> None:
    chosen = {
        p.name: p.select(context(10, HAND)).selected_job_id for p in POLICIES.values()
    }
    assert chosen == {"FIFO": "J1", "EDD": "J2", "CR": "J3", "SPT": "J4", "SRPT": "J5"}


def test_critical_ratio_keys_are_exact_and_keep_overdue_negative() -> None:
    # now=50: ratios -10/10, -20/5, -5/100 and 0/4 (due now).
    jobs = (
        job("X", 0, 40, 5, 10),
        job("Y", 0, 30, 5, 5),
        job("Z", 0, 45, 5, 100),
        job("W", 0, 50, 4, 4),
    )
    decision = get_policy("SCH-B3").select(context(50, jobs))
    assert ranked_ids(decision) == ["Y", "X", "Z", "W"]
    assert [r.key[0] for r in decision.ranking] == [
        Fraction(-4),
        Fraction(-1),
        Fraction(-1, 20),
        Fraction(0),
    ]


def test_critical_ratio_is_exact_where_floats_tie() -> None:
    # At now=1 the ratios are (2**53 + 1) / 2**53 and 1/1. As floats they tie at
    # 1.0; exactly the first is larger, so B is more critical although A entered
    # first.
    big = 2**53
    a = job("A", 0, big + 2, 1, big)
    b = job("B", 1, 2, 1, 1)
    assert (a.due_tick - 1) / a.remaining_route_ticks == (b.due_tick - 1) / 1
    decision = get_policy("SCH-B3").select(context(1, (a, b)))
    assert ranked_ids(decision) == ["B", "A"]


def urgent(policy_id: str, a: DispatchJob, b: DispatchJob, now: int) -> bool:
    """Independent oracle: a is strictly more urgent than b, ignoring ties."""
    if policy_id == "SCH-B1":
        return a.queue_entry_tick < b.queue_entry_tick
    if policy_id == "SCH-B2":
        return a.due_tick < b.due_tick
    if policy_id == "SCH-B3":  # cross-multiplication, remaining > 0
        return (a.due_tick - now) * b.remaining_route_ticks < (
            b.due_tick - now
        ) * a.remaining_route_ticks
    if policy_id == "SCH-B4":
        return a.operation_ticks < b.operation_ticks
    return a.remaining_route_ticks < b.remaining_route_ticks


def equally_urgent(policy_id: str, a: DispatchJob, b: DispatchJob, now: int) -> bool:
    return not urgent(policy_id, a, b, now) and not urgent(policy_id, b, a, now)


@pytest.mark.parametrize("policy_id", sorted(HAND_RANKING))
def test_ties_break_by_queue_entry_then_job_id(policy_id: str) -> None:
    # Same primary key for every rule: due 30, operation 4, remaining 8, now 0.
    tied = (
        job("B", 5, 30, 4, 8),
        job("A", 5, 30, 4, 8),
        job("C", 2, 30, 4, 8),
    )
    expected = ["C", "A", "B"]
    for ordering in itertools.permutations(tied):
        decision = get_policy(policy_id).select(context(5, ordering))
        assert ranked_ids(decision) == expected


@pytest.mark.parametrize(
    ("jobs", "now"),
    [
        ((), 0),
        ((job("F", 11, 20, 2, 2),), 10),  # not released yet
        ((job("I", 0, 20, 2, 2, state=JobState.INELIGIBLE),), 10),
        ((job("C", 0, 20, 2, 0, state=JobState.COMPLETED),), 10),
    ],
)
def test_no_dispatchable_job_is_a_normal_empty_decision(
    jobs: tuple[DispatchJob, ...], now: int
) -> None:
    for policy in POLICIES.values():
        decision = policy.select(context(now, jobs))
        assert decision.status is DecisionStatus.NO_CANDIDATES
        assert decision.selected_job_id is None
        assert decision.ranking == ()


def test_release_is_inclusive_and_other_states_never_win() -> None:
    jobs = (
        job("F", 11, 1, 1, 1),  # future, otherwise best on every rule
        job("I", 0, 1, 1, 1, state=JobState.INELIGIBLE),
        job("C", 0, 1, 1, 0, state=JobState.COMPLETED),
        job("R", 10, 99, 9, 9),  # released exactly at now
    )
    for policy in POLICIES.values():
        assert ranked_ids(policy.select(context(10, jobs))) == ["R"]
        # One tick later F is released too, and every rule now ranks both.
        assert sorted(ranked_ids(policy.select(context(11, jobs)))) == ["F", "R"]


def test_decisions_are_pure() -> None:
    ctx = context(10, HAND)
    before = dataclasses.astuple(ctx)
    for policy in POLICIES.values():
        assert policy.select(ctx) == policy.select(ctx)
    assert dataclasses.astuple(ctx) == before
    frozen: Any = ctx
    with pytest.raises(dataclasses.FrozenInstanceError):
        frozen.now = 11


@pytest.mark.parametrize("bad", [None, "SCH-B0", "SCH-B6", "fifo", 1])
def test_unsupported_policy_is_rejected(bad: object) -> None:
    with pytest.raises(UnsupportedPolicyError):
        get_policy(bad)


job_strategy = st.builds(
    lambda i, entry, due, op, extra, state: job(
        f"J{i:03d}",
        entry,
        due,
        op,
        op + extra if state is not JobState.COMPLETED else 0,
        state=state,
    ),
    st.integers(0, 999),
    st.integers(0, 60),
    st.integers(0, 120),
    st.integers(1, 20),
    st.integers(0, 40),
    st.sampled_from(list(JobState)),
)
jobs_strategy = st.lists(job_strategy, max_size=12, unique_by=lambda j: j.job_id)


@given(jobs_strategy, st.integers(0, 150))
def test_selection_is_dispatchable_and_skips_no_better_job(
    jobs: list[DispatchJob], now: int
) -> None:
    dispatchable = [j for j in jobs if j.is_dispatchable(now)]
    by_id = {j.job_id: j for j in dispatchable}
    for policy_id, policy in POLICIES.items():
        decision = policy.select(context(now, jobs))
        assert sorted(ranked_ids(decision)) == sorted(by_id)
        if not dispatchable:
            assert decision.selected_job_id is None
            continue
        assert decision.selected_job_id in by_id
        chosen = by_id[decision.selected_job_id or ""]
        for other in dispatchable:
            assert not urgent(policy_id, other, chosen, now)
            if equally_urgent(policy_id, other, chosen, now):
                assert (chosen.queue_entry_tick, chosen.job_id) <= (
                    other.queue_entry_tick,
                    other.job_id,
                )


@given(jobs_strategy, st.integers(0, 150), st.randoms(use_true_random=False))
def test_input_order_never_changes_the_decision(
    jobs: list[DispatchJob], now: int, rnd: random.Random
) -> None:
    shuffled = list(jobs)
    rnd.shuffle(shuffled)
    for policy in POLICIES.values():
        assert policy.select(context(now, jobs)) == policy.select(
            context(now, shuffled)
        )
