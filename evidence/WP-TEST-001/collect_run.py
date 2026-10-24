"""Produce RUN-TEST-001-DEV-001: the WP-TEST-001 run on the shared host.

Run from the repository root on a committed, clean work tree:

    uv run --project ci --locked python evidence/WP-TEST-001/collect_run.py

Every step is a real invocation against the actual repository, CI workflow,
03 and 04 (boundary mode REAL; nothing is stubbed):

* conformance   - the strategy check over the whole repository (expects exit 0);
* repeat        - the same check again; the two outputs must be identical, so the
                  gate is deterministic (no retry-until-green, NFR-DX-006);
* negative      - the negative and positive cases of TEST-TEST-001-001;
* probe         - a test file outside every declared suite is created for the
                  duration of the step; the check must fail and name it
                  (expects exit 1), and the file is removed afterwards.

Exit codes and output are recorded as observed; host paths and the host name are
replaced with placeholders.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RUN_ID = "RUN-TEST-001-DEV-001"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
SUMMARY = re.compile(r"covers (\d+) test files in (\d+) suites; (\d+) violation")
PASSED = re.compile(r"(\d+) passed")
PROBE_DIR = "wp_test_001_probe"
PROBE_FILE = f"{PROBE_DIR}/test_untracked_probe.py"


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, check=True
    ).stdout.strip()


def main() -> int:
    root = Path(git("rev-parse", "--show-toplevel"))
    os.chdir(root)
    if git("status", "--porcelain"):
        print("Refusing to run: commit or stash local changes first.", file=sys.stderr)
        return 2
    out = root / "evidence" / "WP-TEST-001" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    uv = ["uv", "run", "--project", "ci", "--locked", "python"]
    env = {**os.environ, "PYTHONPATH": "ci:ci/scripts"}
    check = [*uv, "ci/scripts/check_test_strategy.py"]

    def clean(text: str) -> str:
        text = ANSI.sub("", text)
        for old, new in [
            (str(root), "<repo>"),
            (str(Path.home()), "<home>"),
            (socket.gethostname(), "<host>"),
        ]:
            text = text.replace(old, new)
        lines = [line.rstrip() for line in text.splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines) + "\n"

    steps: list[tuple[str, list[str], str, int]] = [
        ("conformance", check, "conformance.log.txt", 0),
        ("repeat", check, "repeat.log.txt", 0),
        (
            "negative",
            [
                *uv,
                "-m",
                "pytest",
                "ci/tests/test_test_strategy.py",
                "-v",
                "-p",
                "pytest_quarantine",
            ],
            "negative.log.txt",
            0,
        ),
        ("probe", check, "probe.log.txt", 1),
    ]
    results: list[dict[str, object]] = []
    bodies: dict[str, str] = {}
    for name, argv, filename, expected in steps:
        if name == "probe":
            (root / PROBE_DIR).mkdir(exist_ok=True)
            (root / PROBE_FILE).write_text("def test_probe() -> None:\n    pass\n")
        started = time.monotonic()
        try:
            completed = subprocess.run(
                argv, capture_output=True, text=True, env=env, check=False
            )
        finally:
            if name == "probe":
                shutil.rmtree(root / PROBE_DIR, ignore_errors=True)
        body = clean(completed.stdout + completed.stderr)
        bodies[name] = body
        (out / filename).write_text(body, encoding="utf-8")
        results.append(
            {
                "step": name,
                "exit_code": completed.returncode,
                "expected_exit_code": expected,
                "wall_s": round(time.monotonic() - started, 1),
                "output": filename,
            }
        )
        print(
            f"{name:<12} exit={completed.returncode} (expected {expected}) -> {filename}"
        )

    summary = SUMMARY.search(bodies["conformance"])
    passed = PASSED.search(bodies["negative"])
    probe_named = f"VIOLATION {PROBE_FILE}: test file belongs to no declared suite"
    outcome = {
        "test_files": int(summary[1]) if summary else None,
        "suites": int(summary[2]) if summary else None,
        "violations": int(summary[3]) if summary else None,
        "deterministic_repeat": bodies["conformance"] == bodies["repeat"],
        "negative_and_positive_cases_passed": int(passed[1]) if passed else None,
        "probe_rejected_and_named": probe_named in bodies["probe"],
    }
    unexpected = {
        str(r["step"]): f"exit {r['exit_code']}, expected {r['expected_exit_code']}"
        for r in results
        if r["exit_code"] != r["expected_exit_code"]
    }
    record = {
        "run_id": RUN_ID,
        "work_package": "WP-TEST-001",
        "kind": "DEV run on the shared host against the actual repository, workflow, 03 and 04",
        "boundary_mode": "REAL",
        "test_ids": ["TEST-TEST-001-001"],
        "code_revision": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": {
            "machine": platform.machine(),
            "system": platform.system(),
            "python": platform.python_version(),
        },
        "outcome": outcome,
        "steps": results,
        "unexpected": unexpected,
    }
    (out / "record.json").write_text(
        clean(json.dumps(record, indent=2, ensure_ascii=False)), encoding="utf-8"
    )
    print(f"Recorded {RUN_ID} for {record['code_revision'][:12]}: {outcome}")
    ok = not unexpected and all(
        outcome[k] for k in ("deterministic_repeat", "probe_rejected_and_named")
    )
    return 0 if ok and outcome["violations"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
