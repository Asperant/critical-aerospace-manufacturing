"""Produce RUN-PLAT-002-DEV-001: the WP-PLAT-002 development run on the shared host.

Run from the repository root on a committed, clean work tree:

    uv run --project ci --locked python evidence/WP-PLAT-002/collect_run.py

Every step is a real mfgctl invocation; its exit code and output are recorded
as observed (a failing step is recorded, never hidden). A fresh timing store is
used so the run's timings are only this run's. Host-specific values (repository
path, home directory, host name, temporary paths) are replaced with placeholders
and the diagnose bundle itself is not kept, only the list of its contents.
"""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import sys
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

RUN_ID = "RUN-PLAT-002-DEV-001"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
EXPLANATIONS = {
    "doctor": "a doctor check failed; see doctor.json (for example Docker socket access)",
    "up-core": "exit 2 by design: infra/mfgctl/capabilities.json arrives with WP-PLAT-001 (DEP-003)",
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout.strip()


def main() -> int:
    root = Path(git("rev-parse", "--show-toplevel"))
    os.chdir(root)
    if git("status", "--porcelain"):
        print("Refusing to run: commit or stash local changes first.", file=sys.stderr)
        return 2
    out = root / "evidence" / "WP-PLAT-002" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    state = Path(tempfile.mkdtemp(prefix="mfgctl-evidence-"))
    bundles = state / "bundles"
    env = {**os.environ, "MFGCTL_STATE_DIR": str(state), "PYTHONPATH": "ci:ci/scripts"}
    replacements = [
        (str(state), "<state>"),
        (str(root), "<repo>"),
        (str(Path.home()), "<home>"),
        (socket.gethostname(), "<host>"),
    ]

    def clean(text: str) -> str:
        text = ANSI.sub("", text)
        for old, new in replacements:
            text = text.replace(old, new)
        lines = [line.rstrip() for line in text.splitlines()]
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines) + "\n"

    uv = ["uv", "run", "--project", "ci", "--locked"]
    steps = [
        ("bootstrap-1", [*uv, "mfgctl", "bootstrap"], "bootstrap-1.log.txt"),
        ("bootstrap-2", [*uv, "mfgctl", "bootstrap"], "bootstrap-2.log.txt"),
        ("doctor", [*uv, "mfgctl", "doctor", "--json"], "doctor.json"),
        ("check-fast", [*uv, "mfgctl", "check", "--fast"], "check-fast.log.txt"),
        (
            "tests",
            [*uv, "python", "-m", "pytest", "tools/mfgctl/tests", "-q", "-p", "pytest_quarantine"],
            "tests.log.txt",
        ),
        ("up-core", [*uv, "mfgctl", "up", "core"], "up-core.log.txt"),
        ("diagnose", [*uv, "mfgctl", "diagnose", "bundle", "--output", str(bundles)], "diagnose.log.txt"),
        ("timings", [*uv, "mfgctl", "timings", "--json"], "timings.json"),
    ]
    results = []
    for name, argv, filename in steps:
        completed = subprocess.run(argv, capture_output=True, text=True, env=env, check=False)
        body = completed.stdout if filename.endswith(".json") else completed.stdout + completed.stderr
        (out / filename).write_text(clean(body), encoding="utf-8")
        results.append({"step": name, "exit_code": completed.returncode, "output": filename})
        print(f"{name:<12} exit={completed.returncode} -> {filename}")

    archives = sorted(bundles.glob("mfgctl-diagnose-*.tar.gz"))
    contents: list[str] = []
    if archives:
        with tarfile.open(archives[-1]) as archive:
            contents = sorted(m.name.split("/", 1)[1] for m in archive.getmembers())
    record = {
        "run_id": RUN_ID,
        "work_package": "WP-PLAT-002",
        "kind": "DEV run on the shared host (not a documented HardwareProfile)",
        "code_revision": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "steps": results,
        "diagnose_bundle_contents": contents,
        "non_zero_explained": {
            r["step"]: EXPLANATIONS.get(r["step"], "unexpected: investigate before using this run")
            for r in results
            if r["exit_code"] != 0
        },
    }
    (out / "record.json").write_text(clean(json.dumps(record, indent=2, ensure_ascii=False)), encoding="utf-8")
    print(f"Recorded {RUN_ID} for {record['code_revision'][:12]} in {out.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
