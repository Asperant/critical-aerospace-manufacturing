"""Offline instance generator: bounds, determinism and the five-rule integration."""

from __future__ import annotations

import dataclasses

from hypothesis import given
from hypothesis import strategies as st
from manufacturing_scheduler import (
    MAX_SEED,
    POLICIES,
    DecisionStatus,
    OfflineInstanceConfig,
    generate,
)
from sch_fixtures import ranked_ids

CONFIG = OfflineInstanceConfig(
    job_count=60,
    horizon_ticks=400,
    min_operation_ticks=3,
    max_operation_ticks=9,
    max_extra_route_ticks=15,
    min_due_offset_ticks=10,
    max_due_offset_ticks=90,
)


@given(st.integers(0, MAX_SEED))
def test_generated_jobs_respect_every_configured_bound(seed: int) -> None:
    instance = generate(CONFIG, seed)
    ids = [j.job_id for j in instance.jobs]
    assert len(ids) == len(set(ids)) == CONFIG.job_count
    for j in instance.jobs:
        assert 0 <= j.queue_entry_tick <= CONFIG.horizon_ticks
        assert 3 <= j.operation_ticks <= 9
        assert 0 <= j.remaining_route_ticks - j.operation_ticks <= 15
        assert 10 <= j.due_tick - j.queue_entry_tick <= 90
        assert j.tick_unit == CONFIG.tick_unit


@given(st.integers(0, MAX_SEED))
def test_same_seed_and_config_give_an_equal_instance(seed: int) -> None:
    assert generate(CONFIG, seed) == generate(CONFIG, seed)


def test_recorded_stream_output_for_the_pinned_numpy() -> None:
    # A recorded regression value, not a hand calculation: it pins the seed
    # derivation (PCG64, SeedSequence spawn key 1) for the locked NumPy (2.4.6).
    # A failure after a NumPy bump means previously recorded instances no longer
    # replay and must be regenerated and re-recorded.
    instance = generate(OfflineInstanceConfig(3, 100), 20261027)
    assert instance.instance_id == "SYN-1.0.0-20261027-c53f945d38b7"
    assert [
        (j.job_id, j.queue_entry_tick, j.due_tick, j.operation_ticks)
        for j in instance.jobs
    ] == [("J0000", 34, 120, 17), ("J0001", 6, 95, 17), ("J0002", 79, 220, 11)]
    assert [j.remaining_route_ticks for j in instance.jobs] == [48, 41, 33]


def test_instances_vary_with_seed_and_configuration() -> None:
    # A claim about these fixture values only, not about every pair of seeds.
    base = generate(CONFIG, 1)
    assert generate(CONFIG, 2).jobs != base.jobs
    other = dataclasses.replace(CONFIG, job_count=61)
    assert generate(other, 1).instance_id != base.instance_id


def test_metadata_records_provenance_and_the_replay_recipe() -> None:
    meta = generate(CONFIG, 20261027).metadata
    assert meta.provenance.startswith("SYNTHETIC_OFFLINE_FIXTURE")
    assert (meta.rng_algorithm, meta.stream_name, meta.seed) == (
        "numpy.random.PCG64",
        "instance-generator",
        20261027,
    )
    assert meta.config == CONFIG
    assert len(meta.config_sha256) == 64


@given(st.integers(0, MAX_SEED), st.sampled_from([0, 100, 250, 400, 800]))
def test_one_instance_feeds_all_five_rules_in_any_call_order(
    seed: int, now: int
) -> None:
    instance = generate(CONFIG, seed)
    before = instance.jobs
    forward = {pid: p.select(instance.context_at(now)) for pid, p in POLICIES.items()}
    backward = {
        pid: p.select(instance.context_at(now)) for pid, p in reversed(POLICIES.items())
    }
    assert forward == backward
    assert instance.jobs is before
    released = {j.job_id for j in instance.jobs if j.queue_entry_tick <= now}
    for decision in forward.values():
        assert set(ranked_ids(decision)) == released
        assert (decision.status is DecisionStatus.SELECTED) == bool(released)


def test_a_decision_before_the_first_release_has_no_candidate() -> None:
    instance = generate(OfflineInstanceConfig(5, 1_000), 3)
    first = min(j.queue_entry_tick for j in instance.jobs)
    assert first > 0  # a fact of this fixture seed
    for policy in POLICIES.values():
        before = policy.select(instance.context_at(first - 1))
        assert before.status is DecisionStatus.NO_CANDIDATES
        at = policy.select(instance.context_at(first))
        assert at.status is DecisionStatus.SELECTED
