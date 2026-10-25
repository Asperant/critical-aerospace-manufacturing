"""Produce RUN-GOV-002-DEV-001: the WP-GOV-002 run on the shared host.

Run from the repository root on a committed, clean work tree:

    uv run --project ci --locked python evidence/WP-GOV-002/collect_run.py

Every step is a real invocation against the actual repository (boundary mode
REAL): the full trace lint with the TL-08 regression base, strict drift against
03 §17, a reproducibility check (seed and generate leave the tree unchanged),
the trace tests, TL-13 probes on sample PR descriptions, a negative probe (one
broken edge written into the registry must fail TL-02 and is restored), and the
orphan summary. Exit codes and output are recorded as observed; host paths and
the host name are replaced with placeholders.
"""

from __future__ import annotations

import json
import os
import platform
import re
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

RUN_ID = "RUN-GOV-002-DEV-001"
REGISTRY = "traceability/trace_edges.yaml"
ANSI = re.compile(r"\x1b\[[0-9;]*m")


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
    out = root / "evidence" / "WP-GOV-002" / RUN_ID
    out.mkdir(parents=True, exist_ok=True)
    py = [sys.executable, "-m", "cap_trace"]
    env = {**os.environ, "PYTHONPATH": "ci:ci/scripts:tools/trace/src"}

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

    results: list[dict[str, object]] = []

    def step(name: str, argv: list[str], filename: str, expected: int = 0) -> str:
        started = time.monotonic()
        done = subprocess.run(
            argv, capture_output=True, text=True, env=env, check=False
        )
        body = clean(done.stdout + done.stderr)
        (out / filename).write_text(body, encoding="utf-8")
        results.append(
            {
                "step": name,
                "exit_code": done.returncode,
                "expected_exit_code": expected,
                "wall_s": round(time.monotonic() - started, 1),
                "output": filename,
            }
        )
        print(f"{name:<22} exit={done.returncode} (expected {expected}) -> {filename}")
        return body

    lint = step(
        "validate",
        [*py, "validate", "--json", "--base", "origin/main"],
        "validate.json",
    )
    step("drift-strict", [*py, "drift", "--strict"], "drift.log.txt")
    step("seed", [*py, "seed"], "seed.log.txt")
    reproducible = git("status", "--porcelain", "traceability") == ""
    step("tests", [sys.executable, "-m", "pytest", "-c", "tools/trace/pyproject.toml",
                   "tools/trace/tests", "-q", "-p", "pytest_quarantine"], "tests.log.txt")  # fmt: skip

    probes = out / "impact-probes"
    probes.mkdir(exist_ok=True)
    code = probes / "files-code.txt"
    code.write_text("tools/trace/src/cap_trace/lint.py\n", encoding="utf-8")
    docs = probes / "files-docs.txt"
    docs.write_text("docs/03_Requirements_Traceability_Matrix.md\n", encoding="utf-8")
    field = "Requirements (stable IDs, or NONE — reason / control-only scope): "
    bodies = {
        "declared": field + "FR-GOV-004, FR-GOV-005, FR-GOV-009, NFR-GOV-009\n",
        "unknown-id": field + "FR-GOV-999\n",
        "empty": field + "\n",
    }
    for name, text in bodies.items():
        (probes / f"{name}.md").write_text(text, encoding="utf-8")
    for name, files, expected in [
        ("declared", code, 0),
        ("unknown-id", code, 1),
        ("empty", code, 1),
        ("empty", docs, 0),
    ]:
        label = f"impact-{name}-{files.stem.removeprefix('files-')}"
        step(label, [*py, "impact", "--body-file", str(probes / f"{name}.md"),
                     "--files-from", str(files)], f"{label}.log.txt", expected)  # fmt: skip

    original = (root / REGISTRY).read_bytes()
    broken = original.replace(b'"to": "ARCH-PLAT-CICD"', b'"to": "ARCH-PLAT-NOPE"', 1)
    try:
        (root / REGISTRY).write_bytes(broken)
        probe = step("negative-probe", [*py, "validate"], "negative-probe.log.txt", 1)
    finally:
        (root / REGISTRY).write_bytes(original)
    restored = git("status", "--porcelain", REGISTRY) == ""
    step("orphans", [*py, "orphans"], "orphans.log.txt")

    summary = json.loads(lint)
    unexpected = {
        str(r["step"]): f"exit {r['exit_code']}, expected {r['expected_exit_code']}"
        for r in results
        if r["exit_code"] != r["expected_exit_code"]
    }
    record = {
        "run_id": RUN_ID,
        "work_package": "WP-GOV-002",
        "kind": "DEV run on the shared host against the actual repository (boundary mode REAL)",
        "boundary_mode": "REAL",
        "test_ids": [f"TEST-GOV-002-00{n}" for n in range(1, 6)],
        "code_revision": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "host": {
            "machine": platform.machine(),
            "system": platform.system(),
            "cpus": os.cpu_count(),
        },
        "outcome": {
            "checks": summary["checks"],
            "lint_result": summary["result"],
            "lint_findings": len(summary["findings"]),
            "edge_coverage": summary["coverage"],
            "seed_and_generate_reproducible": reproducible,
            "negative_probe_rejected": "TL-02" in probe and "ARCH-PLAT-NOPE" in probe,
            "registry_restored_after_probe": restored,
        },
        "steps": results,
        "unexpected": unexpected,
    }
    (out / "record.json").write_text(
        clean(json.dumps(record, indent=2, ensure_ascii=False)), encoding="utf-8"
    )
    print(f"Recorded {RUN_ID} for {record['code_revision'][:12]}: {record['outcome']}")
    outcome = record["outcome"]
    ok = (
        not unexpected
        and outcome["lint_result"] == "PASS"
        and reproducible
        and outcome["negative_probe_rejected"]
        and restored
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
