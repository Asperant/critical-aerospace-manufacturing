"""Capture one WP-SIM-003 verification run with its execution identity.

Usage (repository root, locked CI environment, PYTHONPATH=ci:ci/scripts):
    python evidence/WP-SIM-003/capture_run.py <out-dir>
Runs the commands in ``default_commands`` once, in order, and writes into ``out-dir``:

* ``<id>.stdout`` and ``<id>.stderr``: the exact bytes the command wrote, never
  normalized (they may hold trailing whitespace; ``runs/.gitattributes`` marks them
  binary so ``git diff --check`` ignores them);
* ``results.json``: per command the argv, UTC times, exit code (``null`` with an
  ``error`` if it could not start), byte count and SHA-256 of both streams, and a
  ``display_result_line`` that is derived from stdout for reading only;
* ``identity.json``: source, tool, lock, host and workload identity.

A failing or missing command is recorded and the run continues; the exit status is
non-zero if any command failed. The tree may be dirty: ``identity.json`` then lists
every changed or untracked file with its SHA-256, except the generated run outputs
and the README that cites them (``manifest_excludes``), so the capture
scripts are bound. Identity fields come from this host at run time; one that cannot
be read stays null. They are local labels, not a governed Release, Environment or
Hardware ID.
"""

from __future__ import annotations

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
PKG = "services/manufacturing-simulator"
EVIDENCE = "evidence/WP-SIM-003"
LINTED = (
    PKG,
    f"{EVIDENCE}/capture_run.py",
    f"{EVIDENCE}/tests/test_capture_run.py",
)
MANIFEST_EXCLUDES = (f"{EVIDENCE}/runs/", f"{EVIDENCE}/README.md")
PACKAGES = (
    "numpy",
    "hypothesis",
    "pytest",
    "ruff",
    "pyright",
    "manufacturing-simulator",
)
OPS_TESTS = (
    f"{PKG}/tests/test_ops_states.py",
    f"{PKG}/tests/test_ops_config.py",
    f"{PKG}/tests/test_ops_routing.py",
    f"{PKG}/tests/test_ops_failures.py",
    f"{PKG}/tests/test_ops_rework.py",
    f"{PKG}/tests/test_ops_replay.py",
    f"{PKG}/tests/test_ops_contract.py",
    f"{PKG}/tests/test_ops_properties.py",
)
NOT_DISPLAY = ("WARNING", "Please install")


def default_commands(py: str) -> list[tuple[str, list[str]]]:
    pytest = [py, "-m", "pytest"]
    quiet = ["-q", "-p", "pytest_quarantine"]
    config = ["-c", f"{PKG}/pyproject.toml"]
    return [
        (
            "operational-model-tests",
            [*pytest, *config, *OPS_TESTS, *quiet],
        ),
        ("simulator-suite", [*pytest, *config, f"{PKG}/tests", *quiet]),
        ("collector-tests", [*pytest, f"{EVIDENCE}/tests", *quiet]),
        ("ruff-check", [py, "-m", "ruff", "check", *LINTED]),
        ("ruff-format", [py, "-m", "ruff", "format", "--check", *LINTED]),
        (
            "pyright",
            [py, "-m", "pyright", "--project", f"{PKG}/pyrightconfig.json"],
        ),
        ("architecture", [py, "ci/scripts/check_architecture_boundaries.py"]),
    ]


def now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    ).stdout.strip()


def display_line(stdout: bytes) -> str:
    """Last meaningful stdout line, for reading only (not evidence)."""
    lines = [ln.rstrip() for ln in stdout.decode("utf-8", "replace").splitlines()]
    lines = [ln for ln in lines if ln and not ln.startswith(NOT_DISPLAY)]
    return lines[-1] if lines else ""


def run_command(repo: Path, out: Path, name: str, cmd: list[str]) -> dict:
    entry: dict = {"id": name, "argv": cmd, "started_utc": now()}
    try:
        done = subprocess.run(cmd, cwd=repo, capture_output=True)
        code, stdout, stderr, error = done.returncode, done.stdout, done.stderr, None
    except OSError as exc:  # the command could not start
        code, stdout, stderr, error = None, b"", b"", f"{type(exc).__name__}: {exc}"
    entry["finished_utc"] = now()
    entry["exit_code"] = code
    if error:
        entry["error"] = error
    for stream, data in (("stdout", stdout), ("stderr", stderr)):
        (out / f"{name}.{stream}").write_bytes(data)
        entry[f"{stream}_file"] = f"{name}.{stream}"
        entry[f"{stream}_bytes"] = len(data)
        entry[f"{stream}_sha256"] = sha_bytes(data)
    entry["display_result_line"] = display_line(stdout)
    return entry


def host_now() -> dict:
    return {"recorded_utc": now(), "loadavg": os.getloadavg()}


def host_static() -> dict:
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
    return {
        "cpu_model": model,
        "logical_cpus": os.cpu_count(),
        "mem_total_mib": mem,
        "gpu": None,
    }


def uv_version() -> str | None:
    try:
        done = subprocess.run(["uv", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return done.stdout.strip() or None


def package_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def own_dir(repo: Path, out: Path) -> list[str]:
    """Pathspec that leaves this run's own (just created) directory out of status."""
    try:
        return ["--", ".", f":(exclude){out.resolve().relative_to(repo.resolve())}"]
    except ValueError:  # the run directory is outside the repository
        return []


def input_manifest(repo: Path, excludes: tuple[str, ...]) -> dict[str, str]:
    """SHA-256 of every modified or untracked file except generated outputs."""
    names = git(repo, "ls-files", "-m", "-o", "--exclude-standard").splitlines()
    return {
        n: sha_bytes((repo / n).read_bytes())
        for n in sorted(names)
        if not n.startswith(excludes) and (repo / n).is_file()
    }


def capture(
    repo: Path,
    out: Path,
    commands: list[tuple[str, list[str]]],
    excludes: tuple[str, ...] = MANIFEST_EXCLUDES,
) -> int:
    out.mkdir(parents=True, exist_ok=False)
    host_start = host_now()
    lock = repo / "ci/uv.lock"
    source = {
        "head_commit": git(repo, "rev-parse", "HEAD"),
        "head_tree": git(repo, "rev-parse", "HEAD^{tree}"),
        "branch": git(repo, "branch", "--show-current"),
        "tree_clean": not git(
            repo, "status", "--porcelain", "--untracked-files=all", *own_dir(repo, out)
        ),
        "manifest_excludes": list(excludes),
        "changed_or_untracked_files_sha256": input_manifest(repo, excludes),
        "lock_sha256": sha_bytes(lock.read_bytes()) if lock.is_file() else None,
    }
    results = [run_command(repo, out, name, cmd) for name, cmd in commands]
    identity = {
        "kind": "NEW local verification run; not CI, INTEGRATION or EVALUATION evidence",
        "source": source,
        "runtime": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "uv": uv_version(),
            "pythonpath": os.environ.get("PYTHONPATH"),
            "packages": {n: package_version(n) for n in PACKAGES},
        },
        "hardware": host_static(),
        "host_at_start": host_start,
        "host_at_finish": host_now(),
        "workload": {
            "scenario": "operational-facility test configurations (2 mills, 1 inspection "
            "station, re-entrant route); not a ScenarioDefinition or realism claim",
            "matrix": "policies fifo, edd, static priority; seeds 1-4; random facilities",
            "shared_host": True,
            "containers_started": False,
            "commands_sequential": True,
        },
        "unavailable": [
            "governed Release identity (ReleaseManifest)",
            "governed Environment ID and image digest",
            "governed Hardware ID (HardwareProfile)",
        ],
    }
    (out / "identity.json").write_text(json.dumps(identity, indent=2) + "\n")
    (out / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    return 0 if all(r["exit_code"] == 0 for r in results) else 1


if __name__ == "__main__":
    sys.exit(
        capture(REPO, Path(sys.argv[1]).resolve(), default_commands(sys.executable))
    )
