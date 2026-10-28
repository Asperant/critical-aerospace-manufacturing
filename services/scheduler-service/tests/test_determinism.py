"""Replay equality across fresh processes and hash seeds."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sch_fixtures import canonical_replay

TESTS_DIR = Path(__file__).resolve().parent
SRC_DIR = TESTS_DIR.parent / "src"
SEED = 20261027


def run_in_fresh_process(seed: int, hash_seed: str) -> str:
    env = {
        **os.environ,
        "PYTHONHASHSEED": hash_seed,
        "PYTHONPATH": os.pathsep.join([str(SRC_DIR), str(TESTS_DIR)]),
    }
    done = subprocess.run(
        [sys.executable, str(TESTS_DIR / "replay_worker.py"), str(seed)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return done.stdout


@pytest.mark.parametrize("hash_seed", ["0", "1", "4242", "random"])
def test_a_fresh_process_replays_the_in_process_trace(hash_seed: str) -> None:
    assert run_in_fresh_process(SEED, hash_seed) == canonical_replay(SEED)


def test_the_replay_trace_depends_on_the_seed() -> None:
    # A claim about these two fixture seeds only.
    assert canonical_replay(SEED) != canonical_replay(SEED + 1)
