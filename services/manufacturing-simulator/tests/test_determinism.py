"""TEST-SIM-DETERMINISM: replay equality, stream isolation and process independence.

These run the opaque toy scenario from ``sim_fixtures``. They establish kernel
mechanics only; they are not AV-SCEN-01, E2E-01 or BENCH-SIMVAL-001 evidence.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st
from manufacturing_simulator import MAX_SEED
from sim_fixtures import build_kernel, canonical_trace, dumps, run_toy

TESTS_DIR = Path(__file__).resolve().parent
SRC_DIR = TESTS_DIR.parent / "src"
SEED = 20261024


def test_toy_scenario_exercises_the_kernel() -> None:
    trace = run_toy(SEED)
    kinds = {record[2] for record in trace["records"]}
    assert kinds == {"arrive", "start", "finish"}
    assert trace["queue_depth"] == 0
    state = dict(trace["state"])
    assert state["finished"] == state["arrivals"] >= 20
    # Every arrival produces exactly one arrive, one start and one finish record.
    assert len(trace["records"]) == 3 * state["arrivals"]


@given(st.integers(min_value=0, max_value=MAX_SEED))
def test_same_seed_replays_to_an_equal_trace_and_state(seed: int) -> None:
    assert run_toy(seed) == run_toy(seed)


def test_replay_in_fresh_worlds_matches_after_other_worlds_ran() -> None:
    first = run_toy(SEED)
    run_toy(SEED + 1)
    run_toy(SEED + 2)
    assert run_toy(SEED) == first


def test_recorded_seed_fixtures_yield_different_traces() -> None:
    # A claim about these two fixture seeds only, not about every pair of seeds.
    assert dumps(run_toy(1)) != dumps(run_toy(2))


def test_stepwise_execution_matches_a_single_run() -> None:
    whole = build_kernel(SEED)
    whole.run_to_horizon(10_000)
    stepped = build_kernel(SEED)
    while stepped.step().record is not None:
        pass
    assert canonical_trace(stepped) == canonical_trace(whole)


def test_a_resumed_run_matches_an_uninterrupted_run() -> None:
    whole = build_kernel(SEED)
    whole.run_to_horizon(10_000)
    resumed = build_kernel(SEED)
    resumed.run(300, 10_000)
    resumed.run(1_000, 10_000)
    resumed.run_to_horizon(10_000)
    assert canonical_trace(resumed) == canonical_trace(whole)


def timing(trace: dict[str, object]) -> list[tuple[object, object, object]]:
    records = trace["records"]
    assert isinstance(records, list)
    return [(r[1], r[2], tuple(map(tuple, r[4]))) for r in records]


def test_extra_draws_on_one_stream_do_not_perturb_the_others() -> None:
    base = run_toy(SEED)
    noisy = run_toy(SEED, extra_draws=7)
    # Arrival, processing and finish timing depend only on the arrival and
    # processing streams, so sampling more from the quality stream cannot move them.
    assert timing(noisy) == timing(base)


def test_quality_stream_draws_are_what_changed() -> None:
    outcomes = {
        dict(run_toy(SEED, extra_draws=n)["state"]).get("defects", 0) for n in range(12)
    }
    # Only the quality stream moved, and it did change the quality outcome.
    assert len(outcomes) > 1


def test_stream_lookup_order_in_handlers_does_not_change_the_trace() -> None:
    assert run_toy(SEED, reverse=False) == run_toy(SEED, reverse=True)


def run_in_fresh_process(seed: int, hash_seed: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
    env["PYTHONHASHSEED"] = hash_seed
    env["PYTHONPATH"] = os.pathsep.join([str(SRC_DIR), str(TESTS_DIR)])
    completed = subprocess.run(
        [sys.executable, str(TESTS_DIR / "replay_worker.py"), str(seed)],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )
    assert completed.returncode == 0, completed.stderr
    return completed.stdout


@pytest.mark.parametrize("hash_seed", ["0", "1", "424242", "random"])
def test_fresh_processes_with_any_hash_seed_replay_identically(hash_seed: str) -> None:
    assert run_in_fresh_process(SEED, hash_seed) == dumps(run_toy(SEED))


def test_a_different_seed_in_a_fresh_process_matches_its_own_replay() -> None:
    assert run_in_fresh_process(7, "3") == dumps(run_toy(7))
    assert run_in_fresh_process(7, "3") != run_in_fresh_process(SEED, "3")
