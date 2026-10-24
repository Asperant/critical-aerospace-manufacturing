"""Generate replay-comparison.json for WP-SIM-001 (toy scenario, kernel mechanics).

Usage (repository root, locked CI environment):
    python replay_comparison.py > replay-comparison.json
Compares an in-process run with fresh-process runs under several PYTHONHASHSEED
values. Hashes are SHA-256 of the canonical JSON trace (records + final state).
"""

import datetime
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy

REPO = Path(__file__).resolve().parents[2] if "evidence" in __file__ else Path.cwd()
SIM = REPO / "services" / "manufacturing-simulator"
sys.path[:0] = [str(SIM / "src"), str(SIM / "tests")]
from sim_fixtures import dumps, run_toy

SEEDS = [0, 1, 2, 7, 20261024, 2**64 + 5]
HASH_SEEDS = ["0", "1", "424242", "random"]


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def fresh(seed: int, hash_seed: str) -> str:
    env = {k: v for k, v in os.environ.items() if k != "PYTHONHASHSEED"}
    env["PYTHONHASHSEED"] = hash_seed
    env["PYTHONPATH"] = os.pathsep.join([str(SIM / "src"), str(SIM / "tests")])
    done = subprocess.run(
        [sys.executable, str(SIM / "tests" / "replay_worker.py"), str(seed)],
        capture_output=True, text=True, env=env, check=True, timeout=120,
    )
    return done.stdout


report = {
    "generated_utc": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
    "scenario": "toy-kernel v1 (opaque counters; kernel mechanics only)",
    "python": sys.version.split()[0],
    "numpy": numpy.__version__,
    "runs": [],
}
all_equal = True
for seed in SEEDS:
    reference = dumps(run_toy(seed))
    entry = {"seed": seed, "in_process_sha256": sha(reference), "fresh_processes": []}
    for hash_seed in HASH_SEEDS:
        out = fresh(seed, hash_seed)
        equal = out == reference
        all_equal &= equal
        entry["fresh_processes"].append(
            {"pythonhashseed": hash_seed, "sha256": sha(out), "equal_to_in_process": equal}
        )
    report["runs"].append(entry)
distinct = {r["in_process_sha256"] for r in report["runs"]}
report["all_fresh_process_traces_equal_in_process"] = all_equal
report["distinct_trace_hashes_across_seeds"] = len(distinct)
report["note"] = (
    "Equality is asserted per seed between processes. Different seeds producing "
    "different traces here is an observation about these fixture seeds, not a claim "
    "about every scenario."
)
print(json.dumps(report, indent=2))
