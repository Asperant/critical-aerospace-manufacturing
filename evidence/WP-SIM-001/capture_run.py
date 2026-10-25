"""Capture one small WP-SIM-001 kernel run with its execution identity.

Usage (repository root, clean committed tree, locked CI environment):
    python evidence/WP-SIM-001/capture_run.py <out-dir>
Runs the simulator suite and the replay comparison once, then writes results.json
(command, UTC times, exit code, result line, output SHA-256) and identity.json.
Identity fields come from this host at run time; a field that cannot be read stays
null. These are local labels, not a governed Release, Environment or Hardware ID.
"""

import datetime
import hashlib
import json
import os
import platform
import subprocess
import sys
from importlib import metadata
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = Path(sys.argv[1])
SUITE = [
    sys.executable,
    "-m",
    "pytest",
    "-c",
    "services/manufacturing-simulator/pyproject.toml",
    "services/manufacturing-simulator/tests",
    "-q",
    "-p",
    "pytest_quarantine",
    f"--junitxml={OUT / 'test-results.xml'}",
]
REPLAY = [sys.executable, "evidence/WP-SIM-001/replay_comparison.py"]
MASTER_SEED = 20261024


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.strip()


def run(name: str, cmd: list[str], out_file: Path) -> dict:
    started = now()
    done = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    out_file.write_text(done.stdout)
    tail = (done.stdout.strip().splitlines() or [""])[-1] if name == "suite" else ""
    return {
        "id": name,
        "command": " ".join(cmd[1:]),
        "started_utc": started,
        "finished_utc": now(),
        "exit_code": done.returncode,
        "result_line": tail,
        "output_file": out_file.name,
        "output_sha256": sha_file(out_file),
        "stderr_tail": done.stderr.strip().splitlines()[-3:],
    }


def cpu() -> dict:
    model = None
    for line in Path("/proc/cpuinfo").read_text().splitlines():
        if line.startswith("model name"):
            model = line.split(":", 1)[1].strip()
            break
    mem = next(
        (
            int(ln.split()[1]) // 1024
            for ln in Path("/proc/meminfo").read_text().splitlines()
            if ln.startswith("MemTotal")
        ),
        None,
    )
    return {"cpu_model": model, "logical_cpus": os.cpu_count(), "mem_total_mib": mem}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=False)
    dirty = git("status", "--porcelain", "--", ".", f":!{OUT.relative_to(REPO)}")
    if dirty:
        print("refusing to run: tree is not clean\n" + dirty, file=sys.stderr)
        return 2
    commit = git("rev-parse", "HEAD")
    results = [run("suite", SUITE, OUT / "suite-output.txt")]
    results.append(run("replay-comparison", REPLAY, OUT / "replay-comparison.json"))
    packages = {
        n: metadata.version(n)
        for n in ("numpy", "hypothesis", "pytest", "manufacturing-simulator")
    }
    identity = {
        "kind": "NEW local kernel run; not CI, INTEGRATION or EVALUATION evidence",
        "recorded_utc": now(),
        "source": {
            "commit": commit,
            "branch": git("branch", "--show-current"),
            "tree_clean": True,
            "simulator_tree": git("rev-parse", "HEAD:services/manufacturing-simulator"),
            "lock_sha256": sha_file(REPO / "ci" / "uv.lock"),
            "replay_script_sha256": sha_file(
                REPO / "evidence/WP-SIM-001/replay_comparison.py"
            ),
        },
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "uv": subprocess.run(
                ["uv", "--version"], capture_output=True, text=True
            ).stdout.strip()
            or None,
            "packages": packages,
        },
        "hardware": cpu() | {"gpu": None},
        "workload": {
            "scenario": "toy-kernel v1 (not the canonical ScenarioDefinition)",
            "master_seed": MASTER_SEED,
            "shared_host": True,
            "containers_started": False,
            "commands_sequential": True,
        },
        "unavailable": [
            "governed Release identity",
            "governed Environment ID and image digest",
            "governed Hardware ID",
        ],
    }
    (OUT / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    (OUT / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return 0 if all(r["exit_code"] == 0 for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
