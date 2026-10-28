"""Compare the dispatch replay trace across fresh processes and hash seeds.

Usage (repository root, locked CI environment):
    python evidence/WP-SCH-001/replay_comparison.py
Prints one JSON document. For each seed the in-process canonical trace (the
generated instance plus every rule's ranking at fixed epochs) is compared with the
trace printed by fresh processes started with different PYTHONHASHSEED values.
"""

import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TESTS = REPO / "services/scheduler-service/tests"
MASTER_SEED = 20261027
SEEDS = [MASTER_SEED + offset for offset in range(6)]
HASH_SEEDS = ["0", "1", "4242", "random"]


def load_fixtures():
    sys.path.insert(0, str(TESTS))
    import sch_fixtures

    return sch_fixtures


def fresh(seed: int, hash_seed: str) -> str:
    env = {**os.environ, "PYTHONHASHSEED": hash_seed, "PYTHONPATH": str(TESTS)}
    return subprocess.run(
        [sys.executable, str(TESTS / "replay_worker.py"), str(seed)],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    ).stdout


def main() -> int:
    fixtures = load_fixtures()
    rows = []
    for seed in SEEDS:
        local = fixtures.canonical_replay(seed)
        equal = {hs: fresh(seed, hs) == local for hs in HASH_SEEDS}
        rows.append(
            {
                "seed": seed,
                "trace_sha256": hashlib.sha256(local.encode()).hexdigest(),
                "equal_to_fresh_process": equal,
            }
        )
    result = {
        "kind": "synthetic offline fixture replay; not BENCH-SCH-001 evidence",
        "numpy": metadata.version("numpy"),
        "config": asdict(fixtures.REPLAY_CONFIG),
        "epochs": list(fixtures.REPLAY_EPOCHS),
        "hash_seeds": HASH_SEEDS,
        "policies": 5,
        "seeds": rows,
        "all_equal": all(all(r["equal_to_fresh_process"].values()) for r in rows),
    }
    print(json.dumps(result, indent=2))
    return 0 if result["all_equal"] else 1


if __name__ == "__main__":
    sys.exit(main())
